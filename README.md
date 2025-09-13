# djangovue
![Vue.js Logo](https://github.com/mikebz/djangovue/raw/master/frontend/img/logo.png "Vue.js")

This is a starter project for Django with Vue.js.  I fell in love with the readability you get in Vue.js and 
decided to create a project where all components are laid out in the most readable way.

Note that this doesn't have features like hot reloading for webpack, but it's a good webpack starting point to build on.

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

4. Install JavaScript dependencies and build
```bash
npm install
npm run build
```

5. Run Django migrations
```bash
uv run python manage.py migrate
```

6. Run the Django project
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
make frontend-install    # Install Node.js dependencies
make frontend-build      # Build for production
make frontend-watch      # Watch for changes and rebuild
```

### Using UV directly:
```bash
uv run python manage.py <command>     # Run Django commands
uv add <package>                      # Add production dependency  
uv add --dev <package>                # Add development dependency
uv sync                               # Install dependencies
```

## 📦 What's New

- **Python 3.10+** required (upgraded from 3.9)
- **Django 5.1** (upgraded from 4.2)
- **UV package manager** for faster dependency management
- **Modern linting** with Ruff (replaces pylint)
- **Code formatting** with Black
- **Improved URL patterns** (modern Django path() syntax)
- **Development helper script** for common tasks

## 📝 Migration Notes

If you're upgrading from the old setup:
- `requirements.txt` is now replaced by `pyproject.toml`
- Use `uv sync` instead of `pip install -r requirements.txt`
- Virtual environment is automatically managed by UV in `.venv/`
- All dependencies are pinned in `uv.lock` for reproducible builds

## Sources
This only worked because people before me created some wonderful examples.
- https://github.com/djstein/vue-django-webpack
- https://github.com/ezhome/django-webpack-loader
