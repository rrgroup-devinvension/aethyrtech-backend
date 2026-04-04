# AethyrTech Backend

This is the backend for the AethyrTech project, built with Django and Django REST Framework.

## Requirements

- Python 3.8+
- MySQL
- pip

## Setup

1. **Clone the repository:**

   ```sh
   git clone <repo-url>
   cd aethyrtech-backend
   ```

2. **Install dependencies:**

   ```sh
   pip install -r requirements.txt
   pip install python-dotenv
   ```

3. **Configure environment variables:**

   - Copy `.env.example` to `.env` and update values:
     ```
     SECRET_KEY=your_secret_key
     DEBUG=True
     DB_NAME=your_db_name
     DB_USER=your_db_user
     DB_PASSWORD=your_db_password
     DB_HOST=localhost
     DB_PORT=3306
     ADMIN_EMAIL=admin@example.com
     ADMIN_PASSWORD=your_admin_password
     ```

4. **Apply migrations:**

   ```sh
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Seed initial data (creates superuser):**

   ```sh
   python manage.py seed
   ```

6. **Run the development server:**
   ```sh
   python manage.py runserver
   ```

## Common Project Commands

- **Create a new Django project:**

  ```sh
  django-admin startproject <project_name>
  ```

- **Create a new Django app:**

  ```sh
  python manage.py startapp <app_name>
  ```

- **Make migrations for changes in models:**

  ```sh
  python manage.py makemigrations
  ```

- **Apply migrations to the database:**

  ```sh
  python manage.py migrate
  ```

- **Create a superuser manually:**

  ```sh
  python manage.py createsuperuser
  ```

- **Run the development server:**

  ```sh
  python manage.py runserver
  ```

- **Run custom seed command (creates initial superuser):**

  ```sh
  python manage.py seed
  ```

- **Collect static files:**

  ```sh
  python manage.py collectstatic
  ```

- **Run tests:**
  ```sh
  python manage.py test
  ```

celery -A config worker --loglevel=info

## Project Structure

- `core/` - Core logic and utilities
- `api/` - API endpoints
- `apps/auths/` - Authentication app
- `apps/users/` - Custom user model and user management
- `apps/brand/` - Brand-related features

## Features

- Custom user model (`apps.users.User`)
- JWT authentication
- Exception handling
- Global request/response formatting
- Pagination

## API Usage

- All API endpoints require authentication (JWT or session).
- Example endpoint for JSON POST:
  ```
  POST /api/json-post/
  Content-Type: application/json
  {
    "key": "value"
  }
  ```

## Development

- Use `python manage.py startapp <appname>` to create new apps.
- Add new apps to `INSTALLED_APPS` in `config/settings.py`.

<!-- todo -->

update api call of analytics
base on user show menus
base on brand open page
json builder


python -m debugpy --listen 5678 manage.py runserver

mysql -u root -p compx_db3 < compx_db.sql

mysqldump -u root -p compx_db1 > store_backup.sql


celery -A config beat -l info

celery -A config worker --loglevel=info -Q scheduler,celery

celery -A config worker --pool=threads --concurrency=4 --loglevel=info





SELECT *
FROM qc_products
WHERE brand IN ('Moto', 'Samsung', 'Xiaomi', 'Realme', 'Oppo', 'Lava', 'Vivo')
  AND `rank` <= 55
LIMIT 100


SELECT pincode, keyword, COUNT(*) from qc_products GROUP BY pincode, keyword LIMIT 100




https://aethyrtech.ai/new/dashboard.php

https://aethyrtech.ai/new/dashboard-positive.php

https://aethyrtech.ai/new/insights.php




SELECT COUNT(*) AS total_rankings FROM product_rankings pr JOIN products p ON pr.sku = p.sku WHERE p.scraper_id = 1000000020 AND pr.scraper_id = 1000000020 AND p.id NOT IN ( 15979,16064,16100,16156,16160,16170,16175,16176, 16181,16186,16214,16216,16220,16222,16225,16226, 16229,16230,16236,16244,16252 );


SELECT COUNT(*) AS total_rankings FROM product_rankings pr JOIN products p ON pr.sku = p.sku WHERE p.scraper_id = 1000000020 AND pr.scraper_id = 1000000020;
SELECT COUNT(*) AS total FROM products WHERE scraper_id = 1000000020;

SELECT p.id, p.sku FROM products p LEFT JOIN product_rankings pr ON pr.sku = p.sku WHERE pr.id IS NULL and p.scraper_id=1000000020;
SELECT pr.id, pr.product_id, pr.sku FROM product_rankings pr LEFT JOIN products p ON pr.sku = p.sku WHERE p.id IS NULL and pr.scraper_id=1000000020;





110001
110002
110003
110004
110005
110006
110011
110016
110017
110018
110021
110023
110024
110025
110026
110027
110029
110031
110032
110034
110035
110037
110039
110045
110048
110051
110052
110053
110054
110055
110062
110065
110071
110072
110075
110078
110084
110085
110091
110092
121001
121003
121004
121006
121010
121012
121102
122001
122004
122010
122011
122101
122104
122105
122108
131001
132103