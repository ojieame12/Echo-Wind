#!/bin/bash

# Run migrations
echo "Running database migrations..."
alembic upgrade head

# Start the application
echo "Starting Uvicorn server..."
uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level debug
