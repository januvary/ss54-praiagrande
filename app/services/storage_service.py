"""
Storage Service - NFS/Remote Storage Health Checks and Retry Logic

Provides health monitoring for remote file storage (NFS, SMB, SFTP) with:
- Startup mount verification
- Periodic health checks
- Retry logic for transient failures
- Graceful degradation when storage is unavailable
"""

import functools
import logging
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from contextlib import suppress
from typing import Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class StorageHealth:
    available: bool
    mount_type: Optional[str]
    total_bytes: int
    used_bytes: int
    free_bytes: int
    read_latency_ms: Optional[float]
    write_latency_ms: Optional[float]
    error: Optional[str]

    @property
    def used_percent(self) -> float:
        if self.total_bytes == 0:
            return 0.0
        return (self.used_bytes / self.total_bytes) * 100

    def to_dict(self) -> dict:
        return {
            "available": self.available,
            "mount_type": self.mount_type,
            "total_gb": round(self.total_bytes / (1024**3), 2),
            "used_gb": round(self.used_bytes / (1024**3), 2),
            "free_gb": round(self.free_bytes / (1024**3), 2),
            "used_percent": round(self.used_percent, 1),
            "read_latency_ms": self.read_latency_ms,
            "write_latency_ms": self.write_latency_ms,
            "error": self.error,
        }


class StorageError(Exception):
    pass


class StorageUnavailableError(StorageError):
    pass


class StorageRetryableError(StorageError):
    pass


def detect_mount_type(path: Path) -> Optional[str]:
    """
    Detect the filesystem/mount type for a given path.

    Returns:
        'nfs', 'nfs4', 'cifs', 'smb', 'fuse.sshfs', 'local', or None
    """
    try:
        path_str = str(path.resolve())

        with open("/proc/mounts", "r") as f:
            mounts = f.readlines()

        best_match: Optional[tuple[int, str]] = None

        for line in mounts:
            parts = line.split()
            if len(parts) < 3:
                continue

            mount_point = parts[1]
            fs_type = parts[2]

            if path_str.startswith(mount_point):
                match_len = len(mount_point)
                if best_match is None or match_len > best_match[0]:
                    best_match = (match_len, fs_type)

        if best_match:
            return best_match[1]

        return "local"

    except Exception as e:
        logger.warning(f"Could not detect mount type: {e}")
        return None


def check_mount_available(path: Path) -> tuple[bool, Optional[str]]:
    """
    Check if a mount point is available and accessible.

    Returns:
        (is_available, error_message)
    """
    if not path.exists():
        try:
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created storage directory: {path}")
        except OSError as e:
            return False, f"Cannot create storage directory: {e}"

    if not path.is_dir():
        return False, f"Storage path is not a directory: {path}"

    if not os.access(path, os.R_OK | os.W_OK | os.X_OK):
        return False, f"Insufficient permissions for storage path: {path}"

    return True, None


def measure_io_latency(
    path: Path, test_size_bytes: int = 1024 * 1024
) -> tuple[Optional[float], Optional[float]]:
    """
    Measure read and write latency for the storage.

    Args:
        path: Path to test
        test_size_bytes: Size of test file (default 1MB)

    Returns:
        (write_latency_ms, read_latency_ms) or (None, None) on failure
    """
    test_file = path / f".storage_healthcheck_{os.getpid()}"
    test_data = os.urandom(test_size_bytes)

    write_latency = None
    read_latency = None

    try:
        start = time.perf_counter()
        test_file.write_bytes(test_data)
        write_latency = (time.perf_counter() - start) * 1000

        start = time.perf_counter()
        _ = test_file.read_bytes()
        read_latency = (time.perf_counter() - start) * 1000

    except Exception as e:
        logger.warning(f"IO latency measurement failed: {e}")

    finally:
        with suppress(Exception):
            test_file.unlink(missing_ok=True)

    return read_latency, write_latency


def get_disk_usage(path: Path) -> tuple[int, int, int]:
    """
    Get disk usage for the storage path.

    Returns:
        (total_bytes, used_bytes, free_bytes)
    """
    try:
        usage = shutil.disk_usage(path)
        return usage.total, usage.used, usage.free
    except Exception as e:
        logger.warning(f"Could not get disk usage: {e}")
        return 0, 0, 0


def get_storage_health(storage_path: str) -> StorageHealth:
    """
    Get comprehensive health information for the storage.

    Args:
        storage_path: Path to the storage mount point

    Returns:
        StorageHealth object with all metrics
    """
    path = Path(storage_path)

    available, error = check_mount_available(path)

    if not available:
        return StorageHealth(
            available=False,
            mount_type=None,
            total_bytes=0,
            used_bytes=0,
            free_bytes=0,
            read_latency_ms=None,
            write_latency_ms=None,
            error=error,
        )

    mount_type = detect_mount_type(path)
    total, used, free = get_disk_usage(path)
    read_latency, write_latency = measure_io_latency(path)

    return StorageHealth(
        available=True,
        mount_type=mount_type,
        total_bytes=total,
        used_bytes=used,
        free_bytes=free,
        read_latency_ms=read_latency,
        write_latency_ms=write_latency,
        error=None,
    )


def retry_file_operation(
    max_retries: int = 3,
    retry_delay: float = 0.5,
    exponential_backoff: bool = True,
    retryable_exceptions: tuple = (OSError, IOError, StorageRetryableError),
):
    """
    Decorator to retry file operations with configurable backoff.

    Args:
        max_retries: Maximum number of retry attempts
        retry_delay: Initial delay between retries in seconds
        exponential_backoff: If True, double delay after each retry
        retryable_exceptions: Exception types to retry on

    Usage:
        @retry_file_operation(max_retries=3, retry_delay=0.5)
        def save_document(...):
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception: Optional[Exception] = None
            delay = retry_delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except retryable_exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(
                            f"File operation failed after {max_retries + 1} attempts: {func.__name__}"
                        )
                        raise StorageRetryableError(
                            f"Operation failed after {max_retries + 1} attempts: {e}"
                        ) from e

                    logger.warning(
                        f"File operation failed (attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {delay:.2f}s: {e}"
                    )

                    time.sleep(delay)

                    if exponential_backoff:
                        delay *= 2

            raise StorageRetryableError(
                f"Unexpected error in retry logic: {last_exception}"
            )

        return wrapper

    return decorator


class StorageHealthChecker:
    """
    Periodic storage health checker that caches results and provides
    health status for monitoring endpoints.
    """

    def __init__(self, storage_path: str, check_interval_seconds: int = 60):
        self.storage_path = storage_path
        self.check_interval = check_interval_seconds
        self._last_check: Optional[StorageHealth] = None
        self._last_check_time: float = 0

    def check(self, force: bool = False) -> StorageHealth:
        """
        Get storage health, using cached result if recent.

        Args:
            force: If True, bypass cache and perform fresh check
        """
        now = time.time()

        if not force and self._last_check is not None:
            if now - self._last_check_time < self.check_interval:
                return self._last_check

        self._last_check = get_storage_health(self.storage_path)
        self._last_check_time = now

        if not self._last_check.available:
            logger.warning(f"Storage health check failed: {self._last_check.error}")
        else:
            logger.debug(
                f"Storage healthy: {self._last_check.mount_type}, "
                f"{self._last_check.free_bytes / (1024**3):.1f}GB free"
            )

        return self._last_check

    @property
    def is_healthy(self) -> bool:
        """Quick check if storage is available."""
        health = self.check()
        return health.available


_storage_checker: Optional[StorageHealthChecker] = None


def init_storage_checker(
    storage_path: str, check_interval_seconds: int = 60
) -> StorageHealthChecker:
    """
    Initialize the global storage health checker.

    Should be called once at application startup.
    """
    global _storage_checker
    _storage_checker = StorageHealthChecker(storage_path, check_interval_seconds)
    return _storage_checker


def get_storage_checker() -> Optional[StorageHealthChecker]:
    """Get the global storage health checker instance."""
    return _storage_checker


def verify_storage_on_startup(storage_path: str) -> bool:
    """
    Verify storage is available during application startup.

    Logs appropriate messages and returns True if storage is ready.

    Args:
        storage_path: Path to verify

    Returns:
        True if storage is available, False otherwise
    """
    logger.info(f"[>>] Verifying storage at: {storage_path}")

    health = get_storage_health(storage_path)

    if health.available:
        logger.info(
            f"[OK] Storage verified: {health.mount_type}, "
            f"{health.free_bytes / (1024**3):.1f}GB free, "
            f"read latency: {health.read_latency_ms:.1f}ms, "
            f"write latency: {health.write_latency_ms:.1f}ms"
        )
        return True
    else:
        logger.error(f"[FAIL] Storage unavailable: {health.error}")
        return False
