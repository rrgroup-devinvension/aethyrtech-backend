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

## License
