#!/bin/bash
set -e

#############################################
# 🚀 AlfJobs Environment Setup Script
#############################################

# Usage: ./setup-alfjobs.sh staging
# Supported: dev | staging | production
#############################################

ENVIRONMENT=$1

if [[ -z "$ENVIRONMENT" ]]; then
  echo "❌ ERROR: Environment not provided!"
  echo "✅ Usage: ./setup-alfjobs.sh <dev|staging|production>"
  exit 1
fi

APP_USER="alfjobs"
APP_DIR="/opt/alfjobs/$ENVIRONMENT"
SERVICE_NAME="alfjobs-$ENVIRONMENT"
JAR_NAME="alfjobs-backend.jar"
ENV_FILE="$APP_DIR/.env"
LOG_DIR="$APP_DIR/logs"
UPLOAD_DIR="$APP_DIR/uploads"
BACKUP_DIR="$APP_DIR/backups"

echo "📌 Starting setup for environment: $ENVIRONMENT"

#############################################
# ✅ Update & install Java 21
#############################################
echo "Installing Java..."
sudo apt update -y
sudo apt install -y openjdk-21-jdk

#############################################
# ✅ Create AlfJobs System User
#############################################
echo "Creating app user if not exists..."
id -u $APP_USER &>/dev/null || sudo useradd -r -s /bin/false $APP_USER

#############################################
# ✅ Create folder structure
#############################################
echo "Creating folder structure..."
sudo mkdir -p "$APP_DIR" "$UPLOAD_DIR" "$LOG_DIR" "$BACKUP_DIR"
sudo chown -R $APP_USER:$APP_USER /opt/alfjobs
sudo chmod -R 755 /opt/alfjobs

#############################################
# ✅ SystemD Service File Creation
#############################################
echo "Creating systemd service..."
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"

sudo bash -c "cat > $SERVICE_FILE" << EOF
[Unit]
Description=AlfJobs $ENVIRONMENT Spring Boot Application
After=network.target

[Service]
User=$APP_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$ENV_FILE
ExecStart=/usr/bin/java -jar $APP_DIR/$JAR_NAME
SuccessExitStatus=143
Restart=always
RestartSec=5
StandardOutput=append:$LOG_DIR/app.out.log
StandardError=append:$LOG_DIR/app.err.log

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME

#############################################
# ✅ Log Rotation
#############################################
echo "Configuring log rotation..."
LOGROTATE_FILE="/etc/logrotate.d/$SERVICE_NAME"

sudo bash -c "cat > $LOGROTATE_FILE" << EOF
$LOG_DIR/*.log {
    daily
    rotate 14
    compress
    missingok
    notifempty
    copytruncate
    create 0640 $APP_USER $APP_USER
    maxsize 100M
}
EOF

#############################################
# ✅ Create .env Template if not exist
#############################################
if [[ ! -f "$ENV_FILE" ]]; then
echo "Creating .env template..."
sudo bash -c "cat > $ENV_FILE" << 'EOF'
# ==============================
# 🌍 Spring Boot Configuration
# ==============================
SPRING_PROFILES_ACTIVE=staging
SERVER_PORT=8080
# ==============================
# 🗄️ Database Configuration
# ==============================
SPRING_DATASOURCE_URL=jdbc:postgresql://YOUR-RDS-ENDPOINT/alfjobs
SPRING_DATASOURCE_USERNAME=postgres
SPRING_DATASOURCE_PASSWORD=
# ==============================
# 🔐 JWT Security Configuration
# ==============================
JWT_SECRET=
JWT_ACCESS_TOKEN_EXPIRATION=9000000
JWT_REFRESH_TOKEN_EXPIRATION=86400000
JWT_LONG_REFRESH_TOKEN_EXPIRATION=2592000000
# ==============================
# 📧 Email Configuration
# ==============================
SPRING_MAIL_HOST=smtp.gmail.com
SPRING_MAIL_PORT=587
SPRING_MAIL_USERNAME=
SPRING_MAIL_PASSWORD=
# ==============================
# 🌐 CORS Configuration
# ==============================
CORS_ALLOWED_ORIGINS=http://localhost:4200
# ==============================
# 📁 File Upload Configuration
# ==============================
FILE_UPLOAD_DIR=/opt/alfjobs/staging/uploads
# ==============================
# 🔗 App Links (Frontend)
# ==============================
RESET_LINK=http://localhost:4200/
VERIFICATION_LINK=http://localhost:4200/
# ==============================
# 👑 Super Admin Credentials
# ==============================
SUPERADMIN_EMAIL=superadmin@alfjobs.com
SUPERADMIN_PASSWORD=Admin@1234
# ==============================
# 📄 Logging Configuration
# ==============================
LOG_FILE_PATH=/opt/alfjobs/staging/logs/alfjobs-backend.log
EOF

sudo chown $APP_USER:$APP_USER "$ENV_FILE"
fi

#############################################
# ✅ Setup Completed
#############################################
echo ""
echo "🎯 Setup completed for ➜ $ENVIRONMENT ✅"
echo "📌 Place your JAR at: $APP_DIR/$JAR_NAME"
echo "⚙️ Then start service:"
echo "sudo systemctl start $SERVICE_NAME"
echo "🔍 Check logs:"
echo "tail -f $LOG_DIR/app.out.log"
