# Architecture

How the code fits together, for anyone — human or agent — who needs to know
where a thing lives before changing it.

This document covers implementation: modules, the seams between them, and the
couplings that are not obvious from reading one file. It is deliberately not a
setup guide. For installation, the command list, environment variable
reference, and what the Content Security Policy allows, see `README.md`. For
the rules about how to make a change here, see `AGENTS.md`.

## Layout

| Path | Contains |
| --- | --- |
| `djangovue/` | Project configuration: settings, URL root, WSGI/ASGI entry points, shared helpers |
| `backend/` | The Django app: views, URLs, templates, tests |
| `frontend/` | Vue source (`js/`) and image assets, built by Vite into `frontend/dist/` |
| `scripts/` | End-to-end checks invoked by `make e2e` |

`manage.py` and `djangovue/cli.py` are the same entry point twice. `cli.py` is
installed as the `manage` console script through `[project.scripts]` in
`pyproject.toml`, which is what makes `uv run manage <command>` work.
`manage.py` calls the same entry point, so the conventional Django invocation
still works.

## Request path

`djangovue/urls.py` mounts Django admin at `admin/` and includes
`backend/urls.py` at the root. That app serves two routes:

- `/` renders `backend/templates/index.html`, the shell that mounts the Vue
  application.
- `/healthz` returns a small JSON body for container readiness and liveness
  probes. The production image depends on it.

## Configuration

`djangovue/settings.py` reads configuration from the process environment, with
`.env` filling in what the environment does not already define. The layering
and the variable reference are documented in *Environment Variables* in
`README.md`; this section is about where the code lives.

`djangovue/utils.py` holds the pieces settings is assembled from:

- **`.env` parsing and loading.** Settings applies `.env` at import time rather
  than leaving it to a task runner, which is what makes `uv run manage ...`,
  Gunicorn, the test suite, and the e2e scripts all see the same configuration.
  Variables already present in the environment are never overwritten, so a
  container or CI job overrides a single key without a file at all. A missing
  file is not an error.
- **Typed environment readers** for booleans, lists, strings, and integers.
  Each takes an optional `environ` mapping, which is what lets the tests
  exercise them without mutating `os.environ`. New configuration readers should
  keep that shape.
- **Security policy construction.** The Content Security Policy is built here
  and applied as `SECURE_CSP` in settings, using Django 6's native CSP support.
  Host formatting is shared with the dev-server origins so IPv6 hosts get
  bracketed correctly. HSTS preload settings are validated at import time — an
  unacceptable combination raises rather than shipping a header the browser
  preload list would reject.

`SECRET_KEY` is required and raises `ImproperlyConfigured` when absent. This is
why the mypy `django-stubs` plugin, which imports the settings module, needs an
environment; `make typecheck` prepares one, bare `mypy` does not.

## Frontend integration

Vite builds `frontend/js/main.js` into `frontend/dist/` with a manifest, and
`django-vite` resolves `{% vite_asset %}` tags in the Django template through
`frontend/dist/.vite/manifest.json`. Three consequences follow:

- **The entry path is named in two places** — the Vite config input and the
  template tag. Renaming it means changing both.
- **Rendering the template requires a build.** On a clean checkout the manifest
  does not exist, so anything that renders `index.html` — Django checks, the
  view tests, the e2e scripts — fails on asset resolution until the frontend
  is built. That is not a code defect, and `make verify` builds first for
  exactly this reason. CI builds in its own step before the same targets.
- **`DJANGO_VITE_DEV_MODE` switches the source of assets.** Off, they resolve
  through the built manifest; on, they point at the running Vite dev server and
  the CSP widens to admit it. The `Makefile` forces it off for the targets that
  must render against the manifest.

`publicDir` is disabled in the Vite config: static assets are served through
Django's staticfiles rather than copied by Vite, so there is one static
pipeline instead of two.

## Tests

Python tests live in the `backend/tests/` package, one module per subject:
views and routing, settings and environment handling, and security headers and
policy construction. Settings-related tests reload the settings module under a
patched environment rather than asserting against process state, because
settings is evaluated at import time.

`make e2e` adds two checks that the unit tests cannot cover: a template render
against the built manifest, and a server boot smoke test.
