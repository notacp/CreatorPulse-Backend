# CreatorPulse Backend

FastAPI backend for the CreatorPulse AI-powered LinkedIn content generation platform.

## Features

- **FastAPI** with async/await support
- **PostgreSQL** with pgvector for vector similarity search
- **Redis** for caching and job queues
- **Celery** for background job processing
- **Supabase** integration for authentication and database
- **Structured logging** with JSON output
- **Comprehensive error handling** with custom exceptions
- **Rate limiting** and security middleware
- **Docker** support for development and production

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL with pgvector extension
- Redis
- Docker and Docker Compose (optional)

### Environment Setup

1. Copy the environment file:
```bash
cp .env.example .env
```

2. Update the `.env` file with your configuration:
- Database connection details
- API keys (Gemini, SendGrid, Twitter)
- JWT secret key
- Redis connection details

### Development with Docker

1. Start all services:
```bash
docker-compose up -d
```

2. The API will be available at `http://localhost:8000`
3. API documentation at `http://localhost:8000/docs`

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start the development server:
```bash
uvicorn app.main:app --reload
```

3. Start Celery worker (in another terminal):
```bash
celery -A app.celery worker --loglevel=info
```

4. Start Celery beat scheduler (in another terminal):
```bash
celery -A app.celery beat --loglevel=info
```

## API Documentation

The API follows the OpenAPI 3.0 specification and provides:

- **Authentication**: JWT-based authentication with Supabase
- **Sources**: RSS feed and Twitter handle management
- **Style Training**: AI writing style analysis
- **Drafts**: AI-generated LinkedIn post drafts
- **Feedback**: User feedback collection and analytics

### Health Checks

- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed health check with service status

### API Endpoints

All API endpoints are prefixed with `/v1`:

- `/v1/auth/*` - Authentication endpoints
- `/v1/sources/*` - Content source management
- `/v1/style/*` - Style training endpoints
- `/v1/drafts/*` - Draft generation and management
- `/v1/user/*` - User settings and preferences
- `/v1/feedback/*` - Feedback collection

## Architecture

### Core Components

- **FastAPI Application**: Main web application with async support
- **Database Models**: SQLAlchemy models with PostgreSQL
- **Pydantic Schemas**: Request/response validation
- **Background Jobs**: Celery tasks for async processing
- **External Integrations**: Gemini AI, SendGrid, Twitter API

### Database Schema

The application uses PostgreSQL with the following main tables:

- `users` - User accounts and preferences
- `sources` - Content sources (RSS feeds, Twitter handles)
- `user_style_posts` - User's writing samples for style training
- `style_vectors` - Vector embeddings for style matching
- `generated_drafts` - AI-generated LinkedIn post drafts
- `draft_feedback` - User feedback on generated drafts
- `email_delivery_log` - Email delivery tracking

### Background Jobs

Celery handles asynchronous tasks:

- **Content Fetching**: Monitor RSS feeds and Twitter handles
- **Style Processing**: Generate embeddings for style training
- **Draft Generation**: Create personalized LinkedIn posts
- **Email Delivery**: Send draft emails to users
- **Maintenance**: Cleanup old data and update metrics

## Configuration

The application uses environment variables for configuration:

### Required Variables

- `DATABASE_URL` - PostgreSQL connection string
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_KEY` - Supabase anon key
- `SUPABASE_SERVICE_KEY` - Supabase service key
- `JWT_SECRET_KEY` - Secret key for JWT tokens
- `GEMINI_API_KEY` - Google Gemini API key
- `SENDGRID_API_KEY` - SendGrid API key
- `TWITTER_BEARER_TOKEN` - Twitter API bearer token

### Optional Variables

- `REDIS_URL` - Redis connection string (default: redis://localhost:6379/0)
- `ENVIRONMENT` - Environment name (development/production)
- `DEBUG` - Enable debug mode (true/false)
- `LOG_LEVEL` - Logging level (DEBUG/INFO/WARNING/ERROR)

## Testing

Run tests with pytest:

```bash
pytest
```

Run tests with coverage:

```bash
pytest --cov=app
```

## Deployment

### Production Deployment

1. Set environment variables for production
2. Use a production WSGI server like Gunicorn:
```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

3. Set up reverse proxy (nginx) for SSL termination
4. Configure monitoring and logging
5. Set up database migrations
6. Deploy Celery workers and beat scheduler

### Environment Variables for Production

- Set `ENVIRONMENT=production`
- Set `DEBUG=false`
- Use strong `JWT_SECRET_KEY`
- Configure proper CORS origins
- Set up SSL certificates
- Configure monitoring and alerting

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the MIT License.