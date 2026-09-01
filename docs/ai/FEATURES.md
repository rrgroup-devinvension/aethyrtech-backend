# Existing Backend Features

Before building a new feature from scratch, check if a scalable solution already exists.

## 1. Chunked Celery Data Imports (Excel/CSV)
**Path:** `experience_cloud/market_data/tasks.py` and `views.py`

If you need to process large CSV or Excel files asynchronously:
- We have a `DataImportJob` model that tracks `status` (PENDING, PROCESSING, PAUSED, COMPLETED).
- Files are uploaded in 5MB chunks via `DataImportJobViewSet`.
- The background processing is handled by Celery (`process_data_import` task), which uses Pandas to parse the file in manageable chunk sizes (e.g., 1000 rows at a time).
- It supports pausing and resuming processing dynamically.
- **Do not rebuild standard file uploads.** Reuse or extend `DataImportJob` for any heavy bulk processing tasks.

## 2. JSON Generation Pipeline
**Path:** `experience_cloud/json_generator/`

- Robust pipeline for aggregating market data into structured JSON templates.
- Includes `ExecutionManager` for tracking long-running builds and task statuses.
