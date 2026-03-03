"""
DEPRECATED: Admin Routes - This file has been split into focused modules

The admin routes have been refactored into the following modules:
- app.web.admin.auth_routes (login/logout)
- app.web.admin.dashboard_routes (dashboard display)
- app.web.admin.process_routes (process listing, details, status, notes, bulk ops)
- app.web.admin.document_routes (document validation, upload, download)
- app.web.admin.email_routes (email preparation, sending, DRS notifications)
- app.web.admin.pdf_routes (PDF generation, viewing, downloading)
- app.web.admin.settings_routes (settings management)
- app.web.admin.activity_routes (activity log viewing)

All routes have been migrated to these new modules. This file is kept for reference.
"""
