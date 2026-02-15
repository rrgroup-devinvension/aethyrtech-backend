
## Github actions
```
STAGING_HOST=
STAGING_USER=
STAGING_SSH_KEY=	Your .pem private key
```

## Django Gunicorn Service (systemd)
> Create on EC2:
```
/etc/systemd/system/django-staging.service
```

> Service file
```
[Unit]
Description=Django Staging App
After=network.target redis.service

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/aethyrtech/django-staging
EnvironmentFile=/opt/aethyrtech/django-staging/.env

ExecStart=/opt/aethyrtech/django-staging/venv/bin/gunicorn \
    config.wsgi:application \
    --workers 4 \
    --bind 0.0.0.0:8000

Restart=always
RestartSec=5

StandardOutput=append:/opt/aethyrtech/logs/django.out.log
StandardError=append:/opt/aethyrtech/logs/django.err.log

[Install]
WantedBy=multi-user.target
```

## Celery Worker Service
> Create:
```
/etc/systemd/system/celery-worker-staging.service
```
> Worker service
```
[Unit]
Description=Celery Worker (Django Staging)
After=network.target redis.service

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/aethyrtech/django-staging
EnvironmentFile=/opt/aethyrtech/django-staging/.env

ExecStart=/opt/aethyrtech/django-staging/venv/bin/celery \
  -A config worker \
  --loglevel=info \
  -Q scheduler,celery

Restart=always
RestartSec=5

StandardOutput=append:/opt/aethyrtech/logs/celery-worker.log
StandardError=append:/opt/aethyrtech/logs/celery-worker.err.log

[Install]
WantedBy=multi-user.target
```

## Celery Beat Service
> Create:
```
/etc/systemd/system/celery-beat-staging.service
```

> Beat service
```
[Unit]
Description=Celery Beat Scheduler
After=network.target redis.service

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/aethyrtech/django-staging
EnvironmentFile=/opt/aethyrtech/django-staging/.env

ExecStart=/opt/aethyrtech/django-staging/venv/bin/celery \
  -A config beat \
  --loglevel=info

Restart=always
RestartSec=5

StandardOutput=append:/opt/aethyrtech/logs/celery-beat.log
StandardError=append:/opt/aethyrtech/logs/celery-beat.err.log

[Install]
WantedBy=multi-user.target
```

## Redis Setup (Required)
> Install
```
sudo apt install redis-server
sudo systemctl enable redis
sudo systemctl start redis
```
> Verify
```
redis-cli ping
```

## Environment File Example
```
/opt/aethyrtech/django-staging/.env
```
> Value 
```
# Django secret key
SECRET_KEY=your-secret-key

# Debug mode: True or False
DEBUG=True

# Database settings (used by Django's DATABASES config)
DB_NAME=aethyrtech1
DB_USER=root
DB_PASSWORD=ritesh123
DB_HOST=localhost
DB_PORT=3306

# Superuser credentials
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=admin123

# JSON Builder DB (separate from main app DB)
# Set these to point the JSON builders to an external/internal MySQL instance.
JSON_BUILDER_DB_HOST=localhost
JSON_BUILDER_DB_PORT=3306
JSON_BUILDER_DB_USER=root
JSON_BUILDER_DB_PASSWORD=ritesh123
JSON_BUILDER_DB_NAME=compx_db1

XBYTE_API_KEY=ddd
XBYTE_API_URL=https://quickcommerce-india-api.xbyteapi.com/quickcommerce_india

LLM_SERVICE=gemini
LLM_API=dddd
LLM_MODEL=gemini-2.5-flash
```

## Enable Services Once

```
sudo systemctl daemon-reload

sudo systemctl enable django-staging
sudo systemctl enable celery-worker-staging
sudo systemctl enable celery-beat-staging

sudo systemctl start django-staging
sudo systemctl start celery-worker-staging
sudo systemctl start celery-beat-staging

```

## Logs Monitoring

> Django
```
tail -f /opt/aethyrtech/logs/django.out.log
```

> Celery Worker
```
tail -f /opt/aethyrtech/logs/celery-worker.log
```

> Celery Beat
```
tail -f /opt/aethyrtech/logs/celery-beat.log
```
