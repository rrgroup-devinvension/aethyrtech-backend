# AethyrTech Backend

Welcome to the AethyrTech Backend project. This is a Domain-Driven Django REST Framework (DRF) backend that powers the AethyrTech Cloud architecture, including Core services, Experience Cloud, Identity Cloud, and Media Cloud.

## Prerequisites

Ensure you have the following installed on your machine:
- Python 3.8+
- MySQL (or a compatible MariaDB instance)
- Redis (Required for Celery and caching)
- Git

## Project Architecture

The project follows a **Domain-Driven Design (DDD)** structure to keep apps modular and scalable:

- `core/` - Core logic, authentication, users, organizations, and LLM integrations.
- `experience_cloud/` - Core domain for E-Commerce analytics, catalog management, JSON generation, and market data integrations (e.g., XBytes, Karmatech).
- `identity_cloud/` - Root logic for identity and access management.
- `media_cloud/` - Root logic for media and asset management.
- `shared/` - Global utilities, exceptions, pagination, and response formatting.

---

## Getting Started

### 1. Clone the repository
```bash
git clone <repo-url>
cd aethyrtech-backend
```

### 2. Set up the virtual environment
It is highly recommended to use a virtual environment:
```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On Mac/Linux:
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
pip install python-dotenv
```

### 4. Configure Environment Variables
Copy the provided `.env.example` file to create your local `.env` file:
```bash
cp .env.example .env
```
Open `.env` and fill in your local MySQL database credentials, Redis URL, and any required email configurations. 

### 5. Database Setup & Migrations
Because the project connects to multiple databases (Default, XBytes, and Karmatech), you must ensure your local MySQL server has these databases created as named in your `.env` file.

Apply migrations to the default database:
```bash
python manage.py makemigrations
python manage.py migrate
```

Apply migrations to the external databases (if required by your routers):
```bash
# Example for XBytes data:
python manage.py migrate market_integrations --database=xbytes_db
```

### 6. Database Seeding (Master Seed Script)
The backend is equipped with a dynamic master seed script that automatically discovers and executes all initial data scaffolding across every app.

To fully seed the database (including Roles, Users, Categories, Platforms, and JSON Templates) in one command, run:
```bash
python manage.py seed
```
*Note: This command will automatically use `ADMIN_EMAIL` and `ADMIN_PASSWORD` from your `.env` file to generate the initial superuser.*

**Running Individual Seeds:**
If you prefer to run or re-run a specific seed script manually, you can execute them individually:
```bash
python manage.py seed_roles            # Seeds User Roles & Permissions
python manage.py seed_users            # Seeds Admin Users
python manage.py seed_categories       # Seeds core product categories
python manage.py seed_platforms        # Seeds E-Commerce platforms (Amazon, Flipkart)
python manage.py seed_json_templates   # Seeds the base templates for JSON builders
```

---

## Running the Application

### 1. Start the Django Server
```bash
python manage.py runserver
```
*For debugging in VSCode using `debugpy`:*
```bash
python -m debugpy --listen 5678 manage.py runserver
```

### 2. Start Celery (Background Tasks)
Celery requires Redis to be running. 

**On Mac/Linux:**
```bash
celery -A config worker --loglevel=info -Q scheduler,celery
```

**On Windows:**
*Windows doesn't support Celery's default prefork pool, so you must use threads:*
```bash
python -m celery -A config worker --pool=threads --concurrency=4 --loglevel=info
```

### 3. Start Celery Beat (Scheduled Tasks)
```bash
celery -A config beat -l info
```

---

## API Documentation

The backend uses `drf-spectacular` to auto-generate beautiful OpenAPI 3.0 documentation. Once your Django server is running, you can access the documentation here:

- **Swagger UI (Interactive API Tester)**: [http://127.0.0.1:8000/api/docs/swagger/](http://127.0.0.1:8000/api/docs/swagger/)
- **Redoc UI (Clean reading format)**: [http://127.0.0.1:8000/api/docs/redoc/](http://127.0.0.1:8000/api/docs/redoc/)

*Note: All API endpoints (except authentication/login) require a JWT Bearer token, which can be passed via the "Authorize" button in Swagger.*

---

## Common Developer Commands

- **Create a new app**:
  ```bash
  python manage.py startapp <app_name>
  ```
- **Collect static files**:
  ```bash
  python manage.py collectstatic
  ```
- **Run tests**:
  ```bash
  python manage.py test
  ```
- **Import/Export MySQL Dumps** (Examples):
  ```bash
  mysql -u root -p atech_new < aethyrtech.sql
  mysqldump -u root -p compx_db > store_backup.sql
  ```

---

## Project Standards & Architecture Details

### 1. Formatting & Linting (Ruff)
This project uses **Ruff** for blazing-fast linting and code formatting (replacing Black and Flake8). 
- **Check for issues**: `ruff check .`
- **Auto-fix issues**: `ruff check --fix .`
- **Format code**: `ruff format .`

### 2. Git Workflow & Pre-Commit Hooks
We strictly enforce code quality before commits using the `pre-commit` framework.
- **Setup hooks (Run once after cloning)**: `pre-commit install`
- **Run manually against all files**: `pre-commit run --all-files`
*The pre-commit hooks will automatically fix trailing whitespace, check YAML formats, and run Ruff formatting.*

### 3. Request/Response Standards
The project strictly enforces a global response wrapper via `shared.response.StandardJSONRenderer`. 
You do not need to manually wrap successful dictionary returns in your views; the renderer handles standardizing the output into a unified JSON format for the frontend.

### 4. Code Commenting
- **Python Docstrings**: Use PEP 257 standard `"""docstrings"""` for all Classes and Service layer functions.
- **Typing**: Use standard Python type hinting (`def process(user_id: int) -> dict:`) especially in domain logic and serializers to aid IDEs and developers.

### 5. API Versioning
APIs should be versioned via the URL routing setup (e.g. `api/v1/...`). Avoid making breaking changes to `v1` routes; create `v2` routes if structural domain changes are required.

### 6. API Idempotency (Safe Retries)
The backend implements a custom `shared.middlewares.IdempotencyMiddleware`. 
For critical actions (like payments or data processing), the frontend can safely retry failed network requests without triggering the same action twice, ensuring robust data integrity.

### 7. Pagination, Filtering & Sorting
- **Pagination**: Controlled globally by `shared.pagination.StandardResultsSetPagination`. List endpoints automatically return paginated data (default `PAGE_SIZE = 20`).
- **Filtering/Sorting**: Handled natively by `DjangoFilterBackend` and `OrderingFilter`. 
  *Example API call: `/api/v1/users/?ordering=-created_at&is_active=true`*

### 8. Error & Validation Handling
Exception handling is centralized via `shared.exceptions.custom_exception_handler`. 
Never return raw HTTP response errors manually. Instead, raise standard DRF exceptions (`ValidationError`, `NotFound`, `PermissionDenied`). The global handler intercepts these and formats them into a predictable JSON error schema for the frontend.

### 9. Docker Setup
A `docker-compose.yml` is provided for containerized deployment/testing. It spins up the entire stack:
- `db` (Postgres/MySQL)
- `redis` (Cache & Celery Broker)
- `web` (Django Application)
- `worker` (Celery Background Tasks)
- `beat` (Celery Scheduler)

*To run via Docker:*
```bash
docker-compose up --build
```
