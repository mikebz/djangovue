# djangovue
![Vue.js Logo](https://github.com/mikebz/djangovue/raw/master/frontend/img/logo.png "Vue.js")

This is a starter project for Django with Vue.js.  I fell in love with the readability you get in Vue.js and
decided to create a project where all components are laid out in the most readable way.

The frontend uses Vue 3 + Vite, and the backend uses Django 5 with environment-driven settings.

## ⚡ Modern Package Management (UV)

This project now uses [UV](https://github.com/astral-sh/uv) for fast, reliable Python package management instead of pip.

## How to get started?
1. Get a copy of the repo on your machine
```bash
git clone https://github.com/mikebz/djangovue.git
cd djangovue
```

2. Install UV (if not already installed)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. Install Python dependencies with UV
```bash
uv sync --extra dev
```

4. Configure environment variables
```bash
cp .env.example .env
set -a
source .env
set +a
```

If you skip this step, the Makefile will load `.env.example` as a fallback so
`make run`, `make test`, and other commands still work with the example defaults.

5. Install JavaScript dependencies and build
```bash
npm ci
npm run build
```

6. Run Django migrations
```bash
uv run python manage.py migrate
```

7. Run the Django project
```bash
uv run python manage.py runserver
# Or use the Makefile:
make run
```

At this point you should be able to navigate to localhost:8000 and see a template rendered.

## 🛠️ Development Commands

### Using the Makefile (Recommended):
```bash
make help           # Show all available commands
make setup          # Initial project setup (install deps + migrate)
make dev            # Prepare for development
make run            # Start development server
make migrate        # Run migrations
make test           # Run tests
make lint           # Run code linter (ruff)
make format         # Format code (black)
make check          # Run Django system checks
make qa             # Run all quality checks and fixes
```

### Frontend commands:
```bash
make frontend-dev        # Start Vite development server (HMR)
make frontend-build      # Build for production
make frontend-watch      # Watch for changes and rebuild
make frontend-preview    # Preview production build
```

Or use npm directly:
```bash
npm run dev              # Start Vite development server
npm run build            # Build for production
npm run preview          # Preview production build
```

### Using UV directly:
```bash
uv run python manage.py <command>     # Run Django commands
uv add <package>                      # Add production dependency
uv add --dev <package>                # Add development dependency
uv sync                               # Install dependencies
```

## Environment Variables

Required:
- `SECRET_KEY`: Django secret key.
- `ALLOWED_HOSTS`: Comma-separated hostnames allowed when `DEBUG=0`.

Optional:
- `DEBUG`: `1/true` for development mode, defaults to `0`.
- `DATABASE_URL`: Database connection URL. Defaults to local SQLite.
- `DB_CONN_MAX_AGE`: Database persistent connection age in seconds (default `60`).
- `SECURE_SSL_REDIRECT`: Force HTTPS redirects (defaults to `0`, set to `1` in TLS-terminated production).
- `USE_X_FORWARDED_PROTO`: Trust `X-Forwarded-Proto` from a controlled reverse proxy (default `0`).
- `DJANGO_VITE_DEV_MODE`: Enables Vite dev server mode.
- `DJANGO_VITE_DEV_SERVER_HOST`: Vite host (default `127.0.0.1`).
- `DJANGO_VITE_DEV_SERVER_PORT`: Vite port (default `3000`).

## CI/CD & Deployment

### GitHub Actions Workflows

This project includes comprehensive CI/CD pipelines:

#### **Continuous Integration** (`ci.yml`)
- **Python Linting**: Ruff linting and Black formatting
- **Frontend Linting**: Build validation and asset checking
- **Python Tests**: Django test suite
- **Integration Tests**: Full application testing
- **Security Scanning**: Dependency vulnerability checks

#### **Dependency Management** (`dependencies.yml`)
- **Weekly Updates**: Automated dependency updates
- **Security Monitoring**: Vulnerability scanning and reporting
- **Pull Requests**: Automated PRs for dependency updates

### Local Development with Docker

```bash
# Build and run with Docker
make docker-build
make docker-run

# Development environment with Docker Compose
make docker-dev

# Or manually:
docker-compose up --build
```

The production container now serves Django through Gunicorn and exposes a health endpoint at `/healthz`.

### Manual Testing

```bash
# Run all quality checks
make qa

# Build production assets
make prod-build

# Test Docker build
make docker-build
```

## �📦 What's New

- **Python 3.11+** required (upgraded from 3.10+, using Python 3.13.5)
- **Django 5.1** (upgraded from 4.2)
- **UV package manager** for faster dependency management
- **Vite 6.x** build tool (replaced Webpack 3.x) - 50x faster dev server
- **Vue 3.5** (upgraded from Vue 2.x, latest Vue with Composition API)
- **Hot Module Replacement (HMR)** for instant development feedback
- **Modern linting** with Ruff (replaces pylint)
- **Code formatting** with Black
- **Improved URL patterns** (modern Django path() syntax)
- **Makefile** for development automation
- **GitHub Actions CI/CD** with comprehensive testing
- **Docker support** for containerized deployment
- **Automated dependency updates** and security monitoring

## 📝 Migration Notes

If you're upgrading from the old setup:
- `requirements.txt` is now replaced by `pyproject.toml`
- Use `uv sync` instead of `pip install -r requirements.txt`
- Virtual environment is automatically managed by UV in `.venv/`
- All dependencies are pinned in `uv.lock` for reproducible builds
- **Python 3.11+** is now required (upgraded from 3.10+)
- **GitHub Actions** automatically test all changes
- **Docker support** available for containerized deployments
- **Automated security scanning** monitors for vulnerabilities

## Sources
This only worked because people before me created some wonderful examples.
- https://github.com/djstein/vue-django-webpack
- https://github.com/ezhome/django-webpack-loader
