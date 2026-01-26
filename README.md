# BioLoupe Backend 🔬

A high-performance scientific research collaboration platform built with FastAPI, featuring complete authentication, authorization (RBAC), OAuth integration, and audit logging.

## 🌟 Key Features

- ✅ **JWT Authentication** - Secure login with access & refresh tokens
- ✅ **OAuth 2.0 Integration** - Google & GitHub sign-in with PKCE flow
- ✅ **Role-Based Access Control (RBAC)** - Team and session permission hierarchies
- ✅ **Audit Logging** - Comprehensive activity tracking with automated cleanup
- ✅ **Rate Limiting** - Redis-based protection against abuse
- ✅ **File Management** - S3/MinIO storage with validation
- ✅ **Vector Search** - Qdrant integration for semantic search
- ✅ **Health Monitoring** - Kubernetes-ready health checks
- ✅ **Structured Logging** - JSON logs with correlation IDs

## 🛠 Technical Stack

- **Python 3.11+** with modern async/await patterns
- **FastAPI** for high-performance async API
- **SQLAlchemy 2.0** (Async) + PostgreSQL
- **Alembic** for database migrations
- **Pydantic v2** for data validation and settings
- **JWT & OAuth 2.0** for authentication
- **Redis** for caching, rate limiting & session state
- **Qdrant** for vector search
- **MinIO/S3** for object storage
- **Docker + Docker Compose** for containerization

## ⚡ Quick Start

### 1. Prerequisites

- Python 3.11+
- Docker and Docker Compose
- PostgreSQL 15+ (or use Docker)
- Git

### 2. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/MohamedYassineKhaldi00/bioloupe.git
cd bioloupe

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Copy environment file and configure
cp .env.example .env
# Edit .env with your configuration (DATABASE_URL, JWT_SECRET_KEY, OAuth credentials, etc.)
```

### 3. Run with Docker Compose (Recommended)

```bash
# Start all services (PostgreSQL, Redis, Qdrant, MinIO, App)
docker-compose up --build

# View logs
docker-compose logs -f app

# Run migrations (in another terminal)
docker-compose exec app alembic upgrade head

# Create initial data (optional)
docker-compose exec app python -m src.app.db.init_db
```

The API will be available at:

- 🌐 API: `http://localhost:8000`
- 📚 Docs: `http://localhost:8000/docs`
- 📖 ReDoc: `http://localhost:8000/redoc`

### 4. Run Locally (Development Mode)

```bash
# Start infrastructure services only
docker-compose up -d postgres redis qdrant minio

# Run migrations
alembic upgrade head

# Start the development server with auto-reload
uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8000

# Or use the run script
python run.py

# Or use make commands (if available)
make run
```

### 5. Verify Installation

```bash
# Check health endpoint
curl http://localhost:8000/api/v1/health

# Should return:
# {
#   "status": "healthy",
#   "database": "connected",
#   "redis": "connected",
#   "qdrant": "connected"
# }
```

## 📚 API Endpoints

### Authentication & Authorization

- `POST /api/v1/auth/register` - Create new user account
- `POST /api/v1/auth/login` - Login with email/password
- `POST /api/v1/auth/refresh` - Refresh access token
- `GET /api/v1/auth/me` - Get current user info
- `POST /api/v1/oauth/google/authorize` - Initiate Google OAuth
- `POST /api/v1/oauth/google/callback` - Handle Google OAuth callback
- `POST /api/v1/oauth/github/authorize` - Initiate GitHub OAuth
- `POST /api/v1/oauth/github/callback` - Handle GitHub OAuth callback

### Teams & Sessions

- `POST /api/v1/teams` - Create team (requires authentication)
- `GET /api/v1/teams/{id}` - Get team details (RBAC enforced)
- `POST /api/v1/sessions` - Create session in team (member+)
- `GET /api/v1/sessions/{id}` - Get session details (RBAC enforced)

### Audit Logs

- `GET /api/v1/audit` - List audit logs (admin only)
- `GET /api/v1/audit/{id}` - Get specific audit log
- `GET /api/v1/audit/user/{user_id}` - User's activity history

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

## 🔧 Code Quality

```bash
# Linting
ruff check src/ tests/

# Auto-fix linting issues
ruff check src/ tests/ --fix

# Type checking
mypy src/

# Format check
ruff format --check src/ tests/

# Auto-format code
ruff format src/ tests/
```

**Quality Standards**:

- Type hints enforced with mypy
- Code style with Ruff (replaces Black, isort, flake8)
- 100% type coverage required
- Comprehensive docstrings

## 🗃 Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history

# View current version
alembic current
```

**Migrations Include**:

- `001_initial_schema.py` - Core tables (users, teams, sessions)
- `002_oauth_accounts.py` - OAuth integration tables
- `003_audit_logs.py` - Audit logging infrastructure

## 📚 Documentation

Comprehensive documentation available:

- `ARCHITECTURE.md` - System architecture and design
- `AUTHENTICATION_IMPLEMENTATION.md` - JWT auth implementation
- `AUTHORIZATION_SYSTEM.md` - RBAC system details
- `OAUTH_INTEGRATION.md` - OAuth 2.0 integration guide
- `AUDIT_LOGGING_IMPLEMENTATION.md` - Audit system documentation
- `AUDIT_LOGGING_QUICKREF.md` - Quick reference for audit logging
- `DEVELOPER_GUIDE.md` - Complete developer guide
- `DEV_TOOLS.md` - Development tools setup
- `CONTRIBUTING.md` - Contribution guidelines

## 🔒 Environment Variables

Key configuration (see `.env.example` for complete list):

```bash
# Application
APP_NAME=BioLoupe
ENVIRONMENT=development
DEBUG=true

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/bioloupe

# Security
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# OAuth
OAUTH_GOOGLE_CLIENT_ID=your-google-client-id
OAUTH_GOOGLE_CLIENT_SECRET=your-google-client-secret
OAUTH_GITHUB_CLIENT_ID=your-github-client-id
OAUTH_GITHUB_CLIENT_SECRET=your-github-client-secret

# Redis
REDIS_URL=redis://localhost:6379/0

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333

# MinIO/S3
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
```

## 📂 Project Structure

```
bioloupe/
├── src/
│   └── app/
│       ├── api/
│       │   ├── dependencies/      # Auth, permissions, common dependencies
│       │   └── v1/
│       │       └── endpoints/     # Auth, OAuth, teams, sessions, audit, health
│       ├── core/                  # Config, security, exceptions, middleware
│       ├── db/                    # Database setup, Qdrant, Redis clients
│       ├── middleware/            # Audit & logging middleware
│       ├── models/                # SQLAlchemy models (User, Team, Session, AuditLog)
│       ├── schemas/               # Pydantic schemas for validation
│       ├── services/              # Business logic (auth, OAuth, RBAC, audit, cache)
│       └── main.py                # FastAPI application factory
├── tests/                         # Comprehensive test suite
├── alembic/                       # Database migrations
│   └── versions/                  # Migration scripts
├── .github/
│   └── instructions/              # AI coding rules & architecture guidelines
├── Dockerfile                     # Multi-stage production build
├── docker-compose.yml             # Local development environment
└── requirements.txt               # Python dependencies
```

## 🏗 Architecture Principles

This project follows **hexagonal architecture** with strict separation of concerns:

- **Domain Layer**: Pure business logic (no framework dependencies)
- **Application Layer**: Use cases and orchestration (services)
- **Infrastructure Layer**: Database, Redis, Qdrant, S3, external APIs
- **Presentation Layer**: FastAPI endpoints, request/response handling

### Key Design Rules

- ✅ Files limited to 200 lines, functions to 30 lines
- ✅ Single responsibility per function/class
- ✅ No business logic in controllers or routes
- ✅ Dependency injection throughout
- ✅ Explicit error handling (no silent failures)
- ✅ Type hints enforced with mypy

See `.github/instructions/rules.instructions.md` for complete architecture guidelines.

## 🔐 Authentication & Authorization

### JWT Authentication

- **Access Tokens**: 15-minute expiry (configurable)
- **Refresh Tokens**: 7-day expiry (configurable)
- **Password Hashing**: Bcrypt with 12 rounds
- **Token Storage**: Redis for session management

### OAuth 2.0 Integration

- **Providers**: Google and GitHub
- **Flow**: Authorization Code with PKCE
- **State Management**: Redis-backed state validation
- **Account Linking**: Multiple OAuth accounts per user

### RBAC System

**Team Roles** (hierarchical):

1. **Owner** - Full control, can transfer ownership
2. **Admin** - Manage members and sessions
3. **Member** - Create sessions, view team
4. **Viewer** - Read-only access

**Session Permissions** (hierarchical):

1. **Admin** - Full control of session
2. **Write** - Edit materials and metadata
3. **Read** - View-only access

Permission resolution uses caching for performance. See `AUTHORIZATION_SYSTEM.md` for details.

## 📊 Audit Logging

Comprehensive activity tracking for compliance and security:

- **User Actions**: Login, OAuth, profile changes
- **Team Actions**: Creation, member management, role changes
- **Session Actions**: CRUD operations, participant management
- **Material Actions**: Upload, download, modifications

**Features**:

- JSON structured logs with metadata
- IP address and user agent tracking
- Automated cleanup (configurable retention)
- Query by user, team, action type, or date range

See `AUDIT_LOGGING_QUICKREF.md` for implementation details.

## 📈 Observability

### Structured Logging

All requests include:

- JSON structured logs with correlation IDs
- `X-Process-ID` header for request tracing
- Request/response timing metrics
- Automatic error tracking and stack traces

### Health Monitoring

- `/api/v1/health` - Comprehensive health check with dependency status
- `/api/v1/health/ready` - Kubernetes readiness probe
- `/api/v1/health/live` - Kubernetes liveness probe

Each health check validates:

- PostgreSQL connection
- Redis connectivity
- Qdrant availability
- Application status

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src --cov-report=html --cov-report=term

# Run specific test file
pytest tests/test_health.py -v

# Run tests by marker
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only

# Run with verbose output
pytest -vv
```

**Test Coverage**:

- Unit tests for services and utilities
- Integration tests for API endpoints
- RBAC permission testing
- Authentication flow testing

## 🚀 CI/CD

GitHub Actions workflow runs on every PR and push:

- ✅ Linting with Ruff
- ✅ Type checking with mypy
- ✅ Unit and integration tests with pytest
- ✅ Coverage reporting (minimum threshold enforced)
- ✅ Docker build validation
- ✅ Security scanning

## 🤝 Contributing

We welcome contributions! Please follow these guidelines:

1. **Read the Rules**: Follow coding standards in `.github/instructions/rules.instructions.md`
2. **Write Tests**: All new features require tests
3. **Type Safety**: Add type hints to all functions
4. **Documentation**: Update relevant docs for user-facing changes
5. **Run Checks**:
    ```bash
    pytest                    # All tests pass
    ruff check src/ tests/    # No linting errors
    mypy src/                 # No type errors
    ```
6. **Create PR**: Use descriptive titles and link related issues

### Development Workflow

```bash
# Create feature branch
git checkout -b feat/your-feature

# Make changes and test
pytest -vv

# Check code quality
ruff check src/ tests/
mypy src/

# Commit with conventional commits
git commit -m "feat: add new feature"

# Push and create PR
git push origin feat/your-feature
```

## 📝 License

[Add your license here]

## 🙏 Acknowledgments

Built with:

- FastAPI for the excellent async framework
- SQLAlchemy for powerful ORM capabilities
- Qdrant for vector search
- Redis for caching and rate limiting
- MinIO for S3-compatible storage

## 📞 Support

For questions and support:

- 📖 Check the documentation in the `/docs` folder
- 🐛 Report bugs via GitHub Issues
- 💡 Request features via GitHub Issues
- 📧 Contact the team at [your-email]

---

**Built with ❤️ for the scientific research community**
