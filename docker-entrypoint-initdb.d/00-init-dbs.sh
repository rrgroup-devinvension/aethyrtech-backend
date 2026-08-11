#!/bin/bash
set -e

echo "Starting database initialization script..."

# Create additional databases and grant permissions to devuser
mysql -u root -p"$MYSQL_ROOT_PASSWORD" <<-EOSQL
  CREATE DATABASE IF NOT EXISTS \`xbytesdata\`;
  CREATE DATABASE IF NOT EXISTS \`compx_db\`;
  
  -- Create devuser and grant access
  CREATE USER IF NOT EXISTS 'devuser'@'%' IDENTIFIED BY 'devpass123';
  GRANT ALL PRIVILEGES ON aethyrtech_staging.* TO 'devuser'@'%';
  GRANT ALL PRIVILEGES ON aethyrtech.* TO 'devuser'@'%';
  GRANT ALL PRIVILEGES ON xbytesdata.* TO 'devuser'@'%';
  GRANT ALL PRIVILEGES ON compx_db.* TO 'devuser'@'%';
  FLUSH PRIVILEGES;
EOSQL

echo "Databases xbytesdata and compx_db created and permissions granted."

# Load default.sql into main database
if [ -f /backups/docker/db/default.sql ]; then
  echo "Found default.sql! Loading into main database..."
  # Use DB_NAME from env if available, fallback to aethyrtech
  DB_NAME="${DB_NAME:-aethyrtech_staging}"
  mysql -u root -p"$MYSQL_ROOT_PASSWORD" "$DB_NAME" < /backups/docker/db/default.sql
  echo "default.sql loaded."
else
  echo "No default.sql found in /backups/docker/db/"
fi

# Load xbytes_db.sql into xbytesdata
if [ -f /backups/docker/db/xbytes_db.sql ]; then
  echo "Found xbytes_db.sql! Loading into xbytesdata..."
  mysql -u root -p"$MYSQL_ROOT_PASSWORD" xbytesdata < /backups/docker/db/xbytes_db.sql
  echo "xbytes_db.sql loaded."
else
  echo "No xbytes_db.sql found in /backups/docker/db/"
fi

# Load compx_db.sql into compx_db
if [ -f /backups/docker/db/compx_db.sql ]; then
  echo "Found compx_db.sql! Loading into compx_db..."
  mysql -u root -p"$MYSQL_ROOT_PASSWORD" compx_db < /backups/docker/db/compx_db.sql
  echo "compx_db.sql loaded."
else
  echo "No compx_db.sql found in /backups/docker/db/"
fi

echo "Database initialization script completed."
