from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import twitter, auth

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

@app.get("/")
async def root():
    return {"message": "Welcome to Social Content Generator API"}
