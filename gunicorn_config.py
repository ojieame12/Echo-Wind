import os

# Get port from environment variable with fallback to 10000
port = os.environ.get('PORT', '10000')
print(f"Starting server on port {port}")

workers = 4
worker_class = 'uvicorn.workers.UvicornWorker'
bind = f"0.0.0.0:{port}"
accesslog = '-'
errorlog = '-'
