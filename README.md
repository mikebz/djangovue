# djangovue
![Vue.js Logo](https://github.com/mikebz/djangovue/raw/master/frontend/img/logo.png "Vue.js")

This is a starter project for Django with Vue.js. The frontend uses Vue 3 + Vite, and the backend uses
Django 6 with environment-driven settings.

## Why this starter in 2026?

If you are starting a new web product in 2026, this stack is a pragmatic default:

- Fast path to production: Django gives you auth, admin, migrations, ORM, and security defaults without adding a large backend framework surface area.
- Modern frontend workflow: Vue 3 + Vite keeps local feedback fast, while production assets stay lean and easy to deploy.
- Fewer moving pieces: one backend service, one frontend build pipeline, and a single repository with consistent local and CI commands.
- Better dependency ergonomics: UV makes Python environments and locking much faster and more reproducible than older pip-based workflows.
- CI-ready from day one: linting, tests, security checks, and integration checks are already wired into GitHub Actions.

This template is especially useful for teams that want to ship quickly without committing to a complex microservice or full-SPA infrastructure upfront.

You could use LLM prompts or a flexible CLI generator of course but there are tradeoffs.

### Djangovue

Delivers a pre-validated, connected and working started with Vite, Vue 3, and Django with minimal configuration overhead.  This has been proven
to work for projects that got to several million dollars in revenue, so it's a well lit path.

### Generator CLIs

Instantiates a infrastructure including PostgreSQL, Redis, Docker, and secure authentication pipelines. The primary drawback is 
substantial structural complexity and needing to understand the tradeoffs that you are signing up for.  Ex: cookiecutter-django

### LLM Generated Apps

Maximum flexibility, generating bespoke scaffolding. Conversely, it risks integration errors across and requires you to verify 
the final output.

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
```

Django loads `.env` from the project root on startup, so `uv run python
manage.py ...`, Gunicorn, and the test suite all see the same configuration —
nothing has to be exported into your shell. Any `make` target that starts
Django creates `.env` from `.env.example` if it is missing, so `make setup` is
enough on a fresh checkout.

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

Configuration is read from the process environment, with `.env` in the project
root filling in whatever the environment does not already define:

1. real environment variables — a shell `export`, `docker run -e`, a Compose
   `environment:` entry, or a CI secret;
2. `.env` — your local, git-ignored file, copied from `.env.example`;
3. the defaults in `djangovue/settings.py`, except for the two required
   variables below.

Environment variables always win, so a deployment can override a single key
without touching the file — and a deployment that passes every variable in
needs no `.env` at all. `.env` is excluded from the Docker image for the same
reason; `make docker-run` passes it in with `--env-file`.

Required:
- `SECRET_KEY`: Django secret key.
- `ALLOWED_HOSTS`: Comma-separated hostnames allowed when `DEBUG=0`.

Optional:
- `DEBUG`: `1/true` for development mode, defaults to `0`.
- `DATABASE_URL`: Database connection URL. Defaults to local SQLite.
- `DB_CONN_MAX_AGE`: Database persistent connection age in seconds (default `60`).
- `SECURE_SSL_REDIRECT`: Force HTTPS redirects (defaults to `0`, set to `1` in TLS-terminated production).
- `USE_X_FORWARDED_PROTO`: Trust `X-Forwarded-Proto` from a controlled reverse proxy (default `0`).
- `SECURE_HSTS_SECONDS`: HSTS max-age in seconds (default `0`, meaning off). Only turn this on once the site is fully served over HTTPS — browsers will refuse plain HTTP for the whole max-age.
- `SECURE_HSTS_INCLUDE_SUBDOMAINS`: Apply HSTS to subdomains too (default `0`).
- `SECURE_HSTS_PRELOAD`: Add the HSTS `preload` directive (default `0`). The browser preload list rejects any submission without `SECURE_HSTS_INCLUDE_SUBDOMAINS=1` and `SECURE_HSTS_SECONDS` of at least `31536000`, so enabling this without both is refused at startup rather than shipping a header that will never be accepted.
- `DJANGO_VITE_DEV_MODE`: Enables Vite dev server mode.
- `DJANGO_VITE_DEV_SERVER_HOST`: Vite host (default `127.0.0.1`).
- `DJANGO_VITE_DEV_SERVER_PORT`: Vite port (default `3000`).

## Content Security Policy

Responses carry a Content Security Policy built with Django 6's native CSP
support (`SECURE_CSP` plus `django.middleware.csp.ContentSecurityPolicyMiddleware`).

A built deployment is same-origin throughout: scripts, styles, and XHR are
limited to `'self'`, framing and plugins are denied outright, and `data:` URIs
are allowed only for images and fonts because Vite inlines small assets that
way.

`DJANGO_VITE_DEV_MODE=1` widens the policy to the Vite dev server only: its
HTTP origin for modules and styles, its websocket origin for hot module
replacement, and `'unsafe-inline'` styles because Vite injects single-file
component CSS as inline `<style>` elements while developing. None of those
relaxations apply once the frontend is built.

Inline scripts and styles of your own should carry the per-request nonce, which
`django.template.context_processors.csp` exposes to templates:

```html
<script nonce="{{ csp_nonce }}">…</script>
```

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
docker compose up --build
```

The production container serves Django through Gunicorn and exposes a health
endpoint at `/healthz`. It ships without a `.env` file, so configuration is
passed in at run time — `make docker-run` forwards your local one with
`--env-file .env`, and any `-e` flag overrides a single key from it.

The Compose stack is for development: it mounts the working tree, runs
`runserver` so edits reload, reads the same `.env`, and points Django at the
Vite dev server running in the `frontend` service.

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
- **Tooling stays current**: Python 3.12+, Django 6.0, Vue 3.5, Vite 8, Ruff, Black, mypy (strict, with `django-stubs`), Docker, and CI automation are already integrated.

## 📝 Migration Notes

If you're upgrading from the old setup:
- `requirements.txt` is now replaced by `pyproject.toml`
- Use `uv sync` instead of `pip install -r requirements.txt`
- Virtual environment is automatically managed by UV in `.venv/`
- All dependencies are pinned in `uv.lock` for reproducible builds
- **Python 3.12+** is now required (Django 6.0 dropped 3.10 and 3.11)
- **GitHub Actions** automatically test all changes
- **Docker support** available for containerized deployments
- **Automated security scanning** monitors for vulnerabilities

## Sources
This project builds on the Django, Vue, and Vite ecosystems.
- https://vuejs.org/
- https://vite.dev/
- https://docs.djangoproject.com/
