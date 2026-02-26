"""
Scheduler Service - APScheduler initialization and management
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore[import-untyped]
from apscheduler.triggers.cron import CronTrigger  # type: ignore[import-untyped]
from dataclasses import dataclass
from typing import Callable
from apscheduler.job import Job  # type: ignore[import-untyped]

from app.services.settings_service import SettingsService
from app.scheduler.jobs import (
    job_auto_send_batches,
    job_drs_follow_up,
    job_auto_expire_processes,
)

logger = logging.getLogger(__name__)

scheduler: BackgroundScheduler | None = None


@dataclass
class JobConfig:
    """Configuration for a scheduler job."""

    id: str
    enabled_key: str
    hour_key: str
    func: Callable[[], None]
    name: str


JOB_CONFIGS = [
    JobConfig(
        id="auto_send_batches",
        enabled_key="batch_send_enabled",
        hour_key="batch_send_hour",
        func=job_auto_send_batches,
        name="Auto Send Batches",
    ),
    JobConfig(
        id="drs_follow_up",
        enabled_key="drs_followup_enabled",
        hour_key="drs_followup_hour",
        func=job_drs_follow_up,
        name="DRS Follow Up",
    ),
    JobConfig(
        id="auto_expire_processes",
        enabled_key="auto_expire_enabled",
        hour_key="auto_expire_hour",
        func=job_auto_expire_processes,
        name="Auto Expire Processes",
    ),
]


def _determine_desired_state(
    enabled: bool, existing: Job | None, new_config: dict, job: JobConfig
) -> str:
    """Determine what state change is needed for a job."""
    if not enabled and existing:
        return "pause"
    if enabled and not existing:
        return "add"
    if enabled and existing and existing.next_run_time is None:
        return "resume"
    if enabled and existing:
        current_hour = existing.trigger.fields["hour"][0]
        new_hour = new_config[job.hour_key]
        if current_hour != new_hour:
            return "reschedule"
    return "none"


def _update_single_job(
    scheduler: BackgroundScheduler, new_config: dict, job: JobConfig
):
    """Update or add a single job based on configuration."""
    existing = scheduler.get_job(job.id)
    enabled = new_config[job.enabled_key]
    hour = new_config[job.hour_key]

    desired_state = _determine_desired_state(enabled, existing, new_config, job)

    if desired_state == "add":
        scheduler.add_job(
            job.func,
            CronTrigger(hour=hour, minute=0),
            id=job.id,
            name=job.name,
            replace_existing=True,
        )
        logger.info(f"Added job {job.id}")
    elif desired_state == "pause":
        scheduler.pause_job(job.id)
        logger.info(f"Paused job {job.id}")
    elif desired_state == "resume":
        scheduler.resume_job(job.id)
        logger.info(f"Resumed job {job.id}")
    elif desired_state == "reschedule":
        scheduler.reschedule_job(job.id, trigger=CronTrigger(hour=hour, minute=0))
        logger.info(f"Rescheduled {job.id} to {hour}:00")


def get_scheduler() -> BackgroundScheduler | None:
    return scheduler


def init_scheduler(config: dict | None = None):
    """
    Initialize scheduler with configuration (from DB or defaults).

    Args:
        config: Optional scheduler config dict. If None, reads from DB.
    """
    from app.database import SessionLocal

    global scheduler

    # Get config from DB if not provided
    if config is None:
        db = SessionLocal()
        try:
            config = SettingsService.get_all_scheduler_config(db)
        finally:
            db.close()

    if not config["scheduler_enabled"]:
        logger.info("Scheduler is disabled via configuration")
        scheduler = None
        return

    scheduler = BackgroundScheduler(timezone=config["scheduler_timezone"])

    # Only add jobs if they're enabled
    if config["batch_send_enabled"]:
        scheduler.add_job(
            job_auto_send_batches,
            CronTrigger(hour=config["batch_send_hour"], minute=0),
            id="auto_send_batches",
            name="Auto Send Batches",
            replace_existing=True,
        )

    if config["drs_followup_enabled"]:
        scheduler.add_job(
            job_drs_follow_up,
            CronTrigger(hour=config["drs_followup_hour"], minute=0),
            id="drs_follow_up",
            name="DRS Follow Up",
            replace_existing=True,
        )

    if config["auto_expire_enabled"]:
        scheduler.add_job(
            job_auto_expire_processes,
            CronTrigger(hour=config["auto_expire_hour"], minute=0),
            id="auto_expire_processes",
            name="Auto Expire Processes",
            replace_existing=True,
        )

    scheduler.start()
    logger.info(
        f"Scheduler started with timezone {config['scheduler_timezone']}. "
        f"Jobs: "
        f"auto_send_batches at {config['batch_send_hour']}:00 (enabled: {config['batch_send_enabled']}), "
        f"drs_follow_up at {config['drs_followup_hour']}:00 (enabled: {config['drs_followup_enabled']}), "
        f"auto_expire_processes at {config['auto_expire_hour']}:00 (enabled: {config['auto_expire_enabled']})"
    )


def shutdown_scheduler():
    global scheduler

    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down")
    scheduler = None


def reload_scheduler_settings():
    """
    Reload scheduler settings from database and update running jobs.

    Uses JobConfig dataclass for cleaner job management.
    """
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        new_config = SettingsService.get_all_scheduler_config(db)

        # Handle master scheduler enabled/disabled
        if not new_config["scheduler_enabled"]:
            if scheduler and scheduler.running:
                logger.info("Disabling scheduler via settings")
                shutdown_scheduler()
            return

        # Master scheduler was disabled - need to start
        if scheduler is None:
            logger.info("Enabling scheduler via settings")
            init_scheduler(new_config)
            return

        # Update each job
        for job_config in JOB_CONFIGS:
            _update_single_job(scheduler, new_config, job_config)

        # Handle timezone change (requires restart)
        if str(scheduler.timezone) != new_config["scheduler_timezone"]:
            logger.info(
                f"Timezone changed from {str(scheduler.timezone)} to {new_config['scheduler_timezone']} - restarting scheduler"
            )
            shutdown_scheduler()
            init_scheduler(new_config)

        logger.info("Scheduler settings reloaded successfully")

    finally:
        db.close()
