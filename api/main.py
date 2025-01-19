import os
import logging
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from api.routes import twitter, auth

# Configure logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Log startup information immediately
logger.info("Starting FastAPI application initialization")
logger.info(f"Python version: {sys.version}")
logger.info(f"Current working directory: {os.getcwd()}")

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/health")
async def health_check():
    logger.info("Health check endpoint called")
    return {"status": "healthy"}

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth")
app.include_router(twitter.router, prefix="/platforms/twitter")

@app.get("/")
async def root():
    logger.info("Root endpoint called")
    return {"message": "Welcome to Social Content Generator API"}

@app.on_event("startup")
async def startup_event():
    port = os.getenv("PORT", "Not set")
    logger.info(f"Application startup event triggered")
    logger.info(f"PORT environment variable: {port}")
    logger.info(f"DATABASE_URL: {os.getenv('DATABASE_URL', 'Not set')}")
    logger.info("All environment variables:")
    for key, value in os.environ.items():
        if not any(secret in key.lower() for secret in ['secret', 'password', 'token']):
            logger.info(f"{key}: {value}")
        else:
            logger.info(f"{key}: [REDACTED]")
