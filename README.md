# BioLoupe Backend 🔬

A high-performance scientific research platform built with FastAPI, following hexagonal architecture principles.

## Technical Stack

- **Python 3.11+** with modern async/await patterns
- **FastAPI** for high-performance async API
- **SQLAlchemy 2.0** (Async) + PostgreSQL
- **Alembic** for database migrations
- **Pydantic v2** for data validation
- **Qdrant** for vector search
- **Redis** for caching and rate limiting
- **MinIO/S3** for object storage
- **Docker + Docker Compose** for containerization

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Docker and Docker Compose
- PostgreSQL 15+ (or use Docker)

### 2. Environment Setup

```bash
# Clone the repository
git clone <repository-url>
cd bioloupe

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Copy environment file
cp .env.example .env
# Edit .env with your configuration
```

### 3. Run with Docker Compose

```bash
# Start all services (PostgreSQL, Redis, Qdrant, MinIO, App)
docker-compose up -d

# View logs
docker-compose logs -f app

# Run migrations
docker-compose exec app alembic upgrade head
```

The API will be available at `http://localhost:8000`

### 4. Run Locally (Development)

```bash
# Start infrastructure services only
docker-compose up -d postgres redis qdrant minio

# Run migrations
alembic upgrade head

# Start the development server
uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### Health Checks

- `GET /api/v1/health` - Comprehensive health check (DB, Redis, Qdrant)
- `GET /api/v1/health/ready` - Readiness probe
- `GET /api/v1/health/live` - Liveness probe

### API Documentation

- `GET /docs` - Swagger UI (Interactive API documentation)
- `GET /redoc` - ReDoc (Alternative API documentation)

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_health.py -v

# Run with markers
pytest -m unit
pytest -m integration
```

## Code Quality

```bash
# Linting
ruff check src/ tests/

# Type checking
mypy src/

# Format check
ruff format --check src/ tests/

# Format code
ruff format src/ tests/
```

## Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

## Project Structure

```
bioloupe/
├── src/
│   └── app/
│       ├── api/           # API endpoints and routes
│       ├── core/          # Core configuration and exceptions
│       ├── db/            # Database setup and clients
│       ├── middleware/    # Custom middleware
│       ├── models/        # SQLAlchemy models
│       ├── schemas/       # Pydantic schemas
│       ├── services/      # Business logic services
│       └── main.py        # Application factory
├── tests/                 # Test files
├── alembic/              # Database migrations
├── .github/              # CI/CD workflows
├── Dockerfile            # Multi-stage Docker build
├── docker-compose.yml    # Local development setup
└── requirements.txt      # Python dependencies
```

## Architecture Principles

This project follows **hexagonal architecture** with strict separation of concerns:

- **Domain Layer**: Pure business logic (no framework dependencies)
- **Application Layer**: Use cases and orchestration
- **Infrastructure Layer**: Database, external services, APIs
- **Presentation Layer**: HTTP endpoints, WebSocket, CLI

See `.github/instructions/rules.md` for detailed architecture rules.

## Observability

### Structured Logging

All requests include:
- JSON structured logs
- `X-Process-ID` correlation header
- Request/response timing
- Error tracking

### Monitoring Endpoints

- `/api/v1/health` - Service health with dependency status
- `/api/v1/health/ready` - Kubernetes readiness probe
- `/api/v1/health/live` - Kubernetes liveness probe

## CI/CD

GitHub Actions workflow runs on every PR:
- Linting with Ruff
- Type checking with mypy
- Unit and integration tests with pytest
- Coverage reporting

## Contributing

1. Follow the coding rules in `.github/instructions/rules.md`
2. Write tests for new features
3. Ensure all tests pass: `pytest`
4. Run linting: `ruff check src/`
5. Run type checking: `mypy src/`
6. Create a pull request

## License

[Your License]
