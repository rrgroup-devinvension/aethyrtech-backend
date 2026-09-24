
## Services

> sudo nano /etc/systemd/system/aethyrtech-gunicorn.service

```
[Unit]
Description=Gunicorn for AethyrTech Backend
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/vhosts/staging-api

ExecStart=/var/www/vhosts/staging-api/.venv/bin/gunicorn \
    --workers 3 \
    --bind 127.0.0.1:8000 \
    --access-logfile /var/www/vhosts/staging-api/logs/gunicorn_access.log \
    --error-logfile /var/www/vhosts/staging-api/logs/gunicorn_error.log \
    config.wsgi:application

Restart=always

StandardOutput=append:/var/www/vhosts/staging-api/logs/gunicorn_stdout.log
StandardError=append:/var/www/vhosts/staging-api/logs/gunicorn_stderr.log

[Install]
WantedBy=multi-user.target
```



> sudo nano /etc/systemd/system/aethyrtech-celery.service

```
[Unit]
Description=Celery Worker for AethyrTech Backend
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/vhosts/staging-api

ExecStart=/var/www/vhosts/staging-api/.venv/bin/celery -A config worker \
    --loglevel=info \
    -Q scheduler,celery \
    --logfile=/var/www/vhosts/staging-api/logs/celery_worker.log

Restart=always

StandardOutput=append:/var/www/vhosts/staging-api/logs/celery_stdout.log
StandardError=append:/var/www/vhosts/staging-api/logs/celery_stderr.log

[Install]
WantedBy=multi-user.target
```

## Reload systemd

# After saving the file:

sudo ls -ld /var/www/vhosts/staging-api/logs
sudo setfacl -R -m u:www-data:rX /var/www/vhosts/staging-api
sudo ls -ld /var/www/vhosts/staging-api/logs
sudo setfacl -m u:www-data:rwx /var/www/vhosts/staging-api/logs

sudo systemctl daemon-reload

# Django service

sudo systemctl start aethyrtech-gunicorn
sudo systemctl status aethyrtech-gunicorn --no-pager

# Cerery Service

sudo systemctl start aethyrtech-celery
sudo systemctl status aethyrtech-celery --no-pager


