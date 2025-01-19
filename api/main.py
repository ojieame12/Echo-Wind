import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import twitter, auth

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

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

@app.on_event("startup")
async def startup_event():
    port = os.getenv("PORT", "Not set")
    logger.info(f"Starting application on port {port}")
    logger.info(f"Database URL: {os.getenv('DATABASE_URL', 'Not set')}")

@app.get("/")
async def root():
    return {"message": "Welcome to Social Content Generator API"}
