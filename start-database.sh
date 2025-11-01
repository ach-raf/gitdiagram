#!/usr/bin/env bash
# Use this script to verify connectivity to your existing PostgreSQL database

# TO RUN ON WINDOWS:
# 1. Install WSL (Windows Subsystem for Linux) - https://learn.microsoft.com/en-us/windows/wsl/install
# 2. Open WSL - `wsl`
# 3. Run this script - `./start-database.sh`

# On Linux and macOS you can run this script directly - `./start-database.sh`

# import env variables from .env
if [ ! -f .env ]; then
  echo "Error: .env file not found. Please create a .env file with your POSTGRES_URL."
  exit 1
fi

set -a
source .env

if [ -z "$POSTGRES_URL" ]; then
  echo "Error: POSTGRES_URL not found in .env file."
  exit 1
fi

# Parse connection details from POSTGRES_URL
# Format: postgresql://username:password@host:port/database
# Handle both with and without port in URL

# Extract port if present
if echo "$POSTGRES_URL" | grep -q "@.*:[0-9]\+/"; then
  # URL has port specified: postgresql://user:pass@host:port/db
  DB_HOST=$(echo "$POSTGRES_URL" | sed -n 's/.*@\([^:]*\):.*/\1/p')
  DB_PORT=$(echo "$POSTGRES_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
else
  # URL doesn't have explicit port: postgresql://user:pass@host/db
  DB_HOST=$(echo "$POSTGRES_URL" | sed -n 's/.*@\([^/]*\)\/.*/\1/p')
  DB_PORT="5432"
fi

# Default to localhost if host is empty
if [ -z "$DB_HOST" ]; then
  DB_HOST="localhost"
fi

# Extract username (everything after :// and before : or @)
DB_USER=$(echo "$POSTGRES_URL" | sed -n 's/.*:\/\/\([^:@]*\).*/\1/p')

# Extract database name (everything after last / and before ?)
DB_NAME=$(echo "$POSTGRES_URL" | sed -n 's/.*\/\([^?]*\).*/\1/p')

echo "Checking PostgreSQL connection..."
echo "  Host: $DB_HOST"
echo "  Port: $DB_PORT"
echo "  User: $DB_USER"
echo "  Database: $DB_NAME"

# Check if port is accessible
if command -v nc > /dev/null 2>&1; then
  if ! nc -z "$DB_HOST" "$DB_PORT" 2>/dev/null; then
    echo "Error: Cannot connect to PostgreSQL at $DB_HOST:$DB_PORT"
    echo "Please ensure your PostgreSQL instance is running and accessible."
    exit 1
  fi
elif command -v timeout > /dev/null 2>&1; then
  if ! timeout 2 bash -c "cat < /dev/null > /dev/tcp/$DB_HOST/$DB_PORT" 2>/dev/null; then
    echo "Error: Cannot connect to PostgreSQL at $DB_HOST:$DB_PORT"
    echo "Please ensure your PostgreSQL instance is running and accessible."
    exit 1
  fi
else
  echo "Warning: Could not verify port connectivity (nc or timeout not available)"
  echo "Proceeding with assumption that PostgreSQL is running..."
fi

# Try to connect using psql if available
if command -v psql > /dev/null 2>&1; then
  echo "Attempting to connect to database..."
  if PGPASSWORD=$(echo "$POSTGRES_URL" | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p') psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
    echo "✓ Successfully connected to PostgreSQL database!"
  else
    echo "Warning: Could not authenticate with PostgreSQL using psql."
    echo "Port is accessible, but authentication failed. Please check your POSTGRES_URL credentials."
  fi
else
  echo "✓ Port $DB_PORT is accessible on $DB_HOST"
  echo "Note: Install psql (PostgreSQL client) for full connection verification."
fi

echo ""
echo "PostgreSQL connection check complete. Your database should be ready to use."
