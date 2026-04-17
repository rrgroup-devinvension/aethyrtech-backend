
## Github actions
```
STAGING_HOST=
STAGING_USER=
STAGING_SSH_KEY=	Your .pem private key
```

## Install dependencies
```
sudo apt install -y pkg-config libcairo2-dev python3-dev build-essential cmake
```

> Set environment variables
```
export MYSQLCLIENT_CFLAGS="-I/usr/include/mysql"
export MYSQLCLIENT_LDFLAGS="-L/usr/lib/x86_64-linux-gnu -lmysqlclient"
```

> Install requirements
```
pip install -r requirements.txt
```

## Setup gunicorn

> Install gunicorn

```
pip install gunicorn
```

> Run gunicorn

```
gunicorn config.wsgi:application --bind 127.0.0.1:8000
```

## Allow permission
```
sudo chown -R www-data:www-data /var/www/vhosts/staging.aethyrtech.ai
sudo chmod -R 755 /var/www/vhosts/staging.aethyrtech.ai
```

```
sudo mkdir -p /var/log/aethyrtech
sudo chown -R www-data:www-data /var/log/aethyrtech
sudo chmod -R 755 /var/log/aethyrtech
```


## Django Gunicorn Service (systemd)
> Create on EC2:
```
sudo nano /etc/systemd/system/aethyrtech-gunicorn.service
```

> Service file
```
[Unit]
Description=Gunicorn for AethyrTech Backend
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/vhosts/staging.aethyrtech.ai/aethyrtech-backend

ExecStart=/var/www/vhosts/staging.aethyrtech.ai/aethyrtech-backend/venv/bin/gunicorn \
    --workers 3 \
    --bind 127.0.0.1:8000 \
    --access-logfile /var/log/aethyrtech/gunicorn_access.log \
    --error-logfile /var/log/aethyrtech/gunicorn_error.log \
    config.wsgi:application

Restart=always

StandardOutput=append:/var/log/aethyrtech/gunicorn_stdout.log
StandardError=append:/var/log/aethyrtech/gunicorn_stderr.log

[Install]
WantedBy=multi-user.target
```

## Celery Worker Service
> Create:
```
sudo nano /etc/systemd/system/aethyrtech-celery.service
```
> Worker service
```
[Unit]
Description=Celery Worker for AethyrTech Backend
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/vhosts/staging.aethyrtech.ai/aethyrtech-backend

ExecStart=/var/www/vhosts/staging.aethyrtech.ai/aethyrtech-backend/venv/bin/celery -A config worker \
    --loglevel=info \
    -Q scheduler,celery \
    --logfile=/var/log/aethyrtech/celery_worker.log

Restart=always

StandardOutput=append:/var/log/aethyrtech/celery_stdout.log
StandardError=append:/var/log/aethyrtech/celery_stderr.log

[Install]
WantedBy=multi-user.target
```

## Celery Beat Service
> Create:
```
sudo nano /etc/systemd/system/aethyrtech-celery-beat.service
```

> Beat service
```
[Unit]
Description=Celery Beat for AethyrTech Backend
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/vhosts/staging.aethyrtech.ai/aethyrtech-backend

ExecStart=/usr/bin/celery -A config beat \
    --loglevel=info \
    --logfile=/var/log/aethyrtech/celery_beat.log

Restart=always

StandardOutput=append:/var/log/aethyrtech/celery_beat_stdout.log
StandardError=append:/var/log/aethyrtech/celery_beat_stderr.log

[Install]
WantedBy=multi-user.target
```

## Redis Setup (Required)
> Install
```
sudo apt install redis-server -y
sudo systemctl start redis-server
sudo systemctl enable redis-server
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

> Daemon reload
```
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
```
> Enable
```
sudo systemctl enable aethyrtech-gunicorn
sudo systemctl enable aethyrtech-celery
sudo systemctl enable aethyrtech-celery-beat

```

> Start
```
sudo systemctl start aethyrtech-gunicorn
sudo systemctl start aethyrtech-celery
sudo systemctl start aethyrtech-celery-beat
```

> Restart
```
sudo systemctl restart aethyrtech-gunicorn
sudo systemctl restart aethyrtech-celery
sudo systemctl restart aethyrtech-celery-beat
```

> Check Status

```
sudo systemctl status aethyrtech-gunicorn
sudo systemctl status aethyrtech-celery
sudo systemctl status aethyrtech-celery-beat
```

> Logs
```
journalctl -u aethyrtech-gunicorn -f
journalctl -u aethyrtech-celery -f
journalctl -u aethyrtech-celery-beat -f
```

> Stop
```
sudo systemctl stop aethyrtech-gunicorn
sudo systemctl stop aethyrtech-celery
sudo systemctl stop aethyrtech-celery-beat
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

## Debug
sudo -u www-data /var/www/vhosts/staging.aethyrtech.ai/aethyrtech-backend/venv/bin/celery -A config worker -Q scheduler,celery --loglevel=info

sudo -u www-data /var/www/vhosts/staging.aethyrtech.ai/aethyrtech-backend/venv/bin/gunicorn config.wsgi:application --bind 0.0.0.0:8000