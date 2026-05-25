# djangovue
![Vue.js Logo](https://github.com/mikebz/djangovue/raw/master/frontend/img/logo.png "Vue.js")

This is a starter project for Django with Vue.js. The frontend uses Vue 3 + Vite, and the backend uses
Django 5 with environment-driven settings.

## Why this starter in 2026?

If you are starting a new web product in 2026, this stack is a pragmatic default:

- Fast path to production: Django gives you auth, admin, migrations, ORM, and security defaults without adding a large backend framework surface area.
- Modern frontend workflow: Vue 3 + Vite keeps local feedback fast, while production assets stay lean and easy to deploy.
- Fewer moving pieces: one backend service, one frontend build pipeline, and a single repository with consistent local and CI commands.
- Better dependency ergonomics: UV makes Python environments and locking much faster and more reproducible than older pip-based workflows.
- CI-ready from day one: linting, tests, security checks, and integration checks are already wired into GitHub Actions.

This template is especially useful for teams that want to ship quickly without committing to a complex microservice or full-SPA infrastructure upfront.

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

The Makefile always loads `.env.example` defaults and then applies `.env`
overrides when present, exporting those env-driven Django/Vite settings for
local commands.

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

`make run` builds the frontend and starts Django on `0.0.0.0:8000` so the app
is reachable through port forwarding.

If you are running in a dev container or Codespaces, open the forwarded port URL
from the VS Code Ports tab. Host-browser `localhost:8000` may point at your own
machine instead of the container.

From inside the container, the app is available at `http://127.0.0.1:8000/`.

If you want hot module replacement instead, start the Vite dev server with
`make frontend-dev` and forward port `3000` too.

This project uses Vite for the frontend build, and the `make` targets mirror the same commands used in CI.

## 🛠️ Development Commands

### Using the Makefile (Recommended):
```bash
make help           # Show all available commands
make setup          # Initial project setup (install deps + migrate)
make run            # Build frontend and start Django on one port
make migrate        # Run migrations
make test           # Run tests
make lint           # Run code linter (ruff)
make format         # Format code (black)
make check          # Run Django system checks
make verify         # Run lint, checks, tests, and e2e
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
make verify

# Build production assets
make prod-build

# Test Docker build
make docker-build
```

## Why this framework choice still holds up

- **Django + Vue remains a strong split**: backend-rendered pages and APIs on Django, interactive UI on Vue, without overengineering routing or deployment.
- **Vite replaced legacy bundler complexity**: builds are fast and predictable, and local iteration is much smoother than older webpack-era setups.
- **Strong defaults with room to grow**: start with SQLite and one service, then move to Postgres, workers, and CDN/static hosting patterns when needed.
- **Tooling stays current**: Python 3.11+, Django 5.1, Vue 3.5, Vite 6, Ruff, Black, mypy, Docker, and CI automation are already integrated.

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
This project builds on the Django, Vue, and Vite ecosystems.
- https://vuejs.org/
- https://vite.dev/
- https://docs.djangoproject.com/
