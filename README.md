# Social Content Generator

An automated platform that crawls business websites, generates social media content using AI, and schedules posts across multiple platforms.

## Features

- Web crawling functionality to extract business content
- Text processing and context extraction
- AI-powered content generation using OpenAI
- Multi-platform posting support (Twitter, Bluesky, LinkedIn)
- Customizable posting schedules
- User authentication and platform integration

## Project Structure

```
social-content-generator/
├── app/
│   ├── auth/         # Authentication related code
│   ├── crawler/      # Web crawler implementation
│   ├── processor/    # Text processing and context extraction
│   ├── generator/    # AI content generation
│   ├── scheduler/    # Posting scheduler
│   └── platforms/    # Platform-specific posting implementations
├── config/           # Configuration files
├── models/           # Database models
├── api/             # API endpoints
└── tests/           # Test files
```

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
- Create a `.env` file with necessary API keys and configurations

3. Initialize the database:
```bash
python scripts/init_db.py
```

## Technology Stack

- Python 3.9+
- FastAPI for backend API
- SQLAlchemy for database ORM
- Celery for task queue
- Redis for caching and task broker
- OpenAI API for content generation
- Platform-specific APIs (Twitter, Bluesky, LinkedIn)
