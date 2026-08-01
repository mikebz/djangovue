# AGENTS.md

Operating guide for coding agents working in this repository. Read this before
making changes. Everything below was verified against the current tree — if a
command here stops matching reality, fix this file in the same change.

## What this project is

A Django 5 + Vue 3 starter application, served as a single origin:

- **Backend**: Django 5.1 on Python 3.11+ (CI and tooling target 3.13),
  dependencies managed by [uv](https://docs.astral.sh/uv/), locked in `uv.lock`.
- **Frontend**: Vue 3.5 built by Vite, output to `frontend/dist/` and pulled
  into Django templates by `django-vite` via the Vite manifest.
- **Config**: environment-driven settings, no secrets in code.

There is one Django app (`backend`) with two views (`/` and `/healthz`) and no
models yet. Treat it as a template, not a large product: keep it small,
readable, and boring.

## Repository map

| Path | What lives there |
| --- | --- |
| `djangovue/` | Project config: `settings.py` (env helpers + Django settings), `urls.py`, `wsgi.py` |
| `backend/` | The single Django app: `views.py`, `urls.py`, `apps.py`, `models.py` (empty), `tests.py`, `templates/index.html` |
| `frontend/js/` | Vue source — `main.js` (entry, mounts `#app`), `App.vue` |
| `frontend/dist/` | Vite build output **(generated, gitignored — never edit or commit)** |
| `scripts/` | `e2e_template_check.py` (template renders expected markers), `e2e_server_smoke.sh` (server boots and answers `/`) |
| `.github/workflows/` | `ci.yml`, `dependencies.yml`, `codeql-analysis.yml` |
| `Makefile` | The canonical entry point for every command; CI calls these same targets |

## Setup

```bash
make install           # uv sync --extra dev  (creates .venv)
make frontend-install  # npm ci               (creates node_modules)
make migrate
```

Environment variables: the `Makefile` includes `.env.example` first, then `.env`
if present, and exports every key it finds. So `make` targets already have
working defaults — **you usually do not need to create `.env`** to run tests or
the app locally. If you invoke `uv run python manage.py ...` directly, export
the vars yourself first:

```bash
set -a; source .env.example; set +a
```

`SECRET_KEY` is mandatory: `djangovue/settings.py` raises
`ImproperlyConfigured` at import time when it is missing, and `ALLOWED_HOSTS`
becomes mandatory too once `DEBUG` is off. Both failures look like unrelated
import errors, so check the environment first when Django refuses to start.

## Commands

Always prefer `make`; the targets set the env vars the underlying commands need.

| Command | Purpose |
| --- | --- |
| `make help` | List every target |
| `make verify` | **The gate.** lint → typecheck → check → test → e2e |
| `make test` | Django test suite (`manage.py test`) |
| `make lint` | `ruff check` + `ruff format --check` + `black --check` |
| `make format` | `ruff format` + `black` (run this before committing) |
| `make lint-fix` | `ruff check --fix` |
| `make typecheck` | `mypy` |
| `make check` | `manage.py check` |
| `make e2e` | Migrate, render-check the template, smoke-test the server |
| `make frontend-build` | `vite build`, then assert `dist/` and the manifest exist |
| `make run` | Build frontend, serve Django on `0.0.0.0:8000` |
| `make frontend-dev` | Vite dev server on `:3000` (HMR; needs `DJANGO_VITE_DEV_MODE=1`) |

### Build the frontend before running tests

`make test`, `make e2e`, and therefore `make verify` render `index.html`, which
calls `{% vite_asset %}` and reads `frontend/dist/.vite/manifest.json`. On a
fresh checkout that file does not exist and **9 of the 19 tests fail** with
`DjangoViteAssetNotFoundError`. This is not a regression you introduced:

```bash
make frontend-build && make verify
```

CI does the same thing — it runs `make frontend-build` before `make check` and
`make test`.

## Definition of done

A change is finished when `make frontend-build && make verify` passes from a
clean tree. Do not report success on a partial run, and do not commit with
lint, type, or test failures outstanding. If something is genuinely broken
before your change, say so explicitly rather than folding it into your diff.

## Conventions

**Python**

- Line length 88; `ruff` (E, W, F, I, B, C4, UP) and `black` both run — format
  with `make format` rather than hand-aligning code.
- `mypy` runs with `disallow_untyped_defs = true` over `backend/`, `djangovue/`,
  `manage.py`, and `scripts/e2e_template_check.py`. **Every function needs full
  type annotations**, including `-> None`. Migrations are excluded.
- Docstrings are Google-style with `Args:`/`Returns:`/`Raises:` sections, and
  every module has one. Match that, even though no linter enforces it.
- The env helpers in `settings.py` (`get_env_bool`, `get_env_list`,
  `get_env_int`) take an optional `environ` mapping so they can be tested
  without mutating `os.environ`. Keep new config readers in that shape and read
  config through them instead of touching `os.environ` inline.
- `.github/instructions/effective_python.instructions.md` carries the broader
  Python style guidance this repo follows.

**Frontend**

- Vue 3 SFCs under `frontend/js/`. The Vite entry point is
  `frontend/js/main.js`, referenced by name in both `vite.config.js` and
  `backend/templates/index.html` — renaming it means updating all three.
- `publicDir` is disabled; static assets go through Django's staticfiles
  (`frontend/` and `frontend/dist/` are both in `STATICFILES_DIRS`).
- There is no JS linter or JS test runner. Frontend verification is
  `make frontend-build` plus the template/server e2e checks.

**Tests**

- All Python tests live in `backend/tests.py`. Use `TestCase` when the database
  is involved and `SimpleTestCase` when it is not.
- Test names describe behavior (`test_index_view_returns_200_status_code`) and
  docstrings use GIVEN / WHEN / THEN. Follow the existing style.
- Settings-related tests reload `djangovue.settings` under `mock.patch.dict` —
  reuse that pattern instead of asserting against process state.

## How to work

This repo follows Kent Beck's TDD and Tidy First discipline; the long-form
version is in `.github/AGENTS.md`. The short version:

1. Write one failing test that describes the smallest next increment.
2. Write the least code that makes it pass.
3. Refactor only with tests green.
4. **Never mix structural and behavioral changes in one commit.** Structural
   changes (rename, extract, move) land first, on their own, with tests passing
   before and after. Behavioral changes follow.
5. Small, frequent commits. Each commit message says which kind it is.

Leave a comment when a design decision is non-obvious, and include the URL when
the reasoning comes from an external source.

## Git and PRs

- Work on the branch you were assigned; never push to `master`.
- Push with `git push -u origin <branch>`; retry network failures with backoff.
- Do not open a pull request unless you were explicitly asked to.
- `CONTRIBUTING.md` requires frontend UI changes to be verified in **Safari on
  macOS** as well as Chrome. An agent in a Linux container cannot do this — if
  your change touches Vue/Vite UI, say plainly in the PR or your summary that
  Safari verification is still outstanding and needs a human.

## Do not

- Edit or commit generated output: `frontend/dist/`, `staticfiles/`,
  `db.sqlite3`, `node_modules/`, `.venv/`.
- Hand-edit `uv.lock` or `package-lock.json` — use `uv add` / `uv sync` and
  `npm` so the lockfiles stay reproducible.
- Put secrets in code, settings, `docker-compose.yml`, or CI files. Add the
  variable to `.env.example` with a placeholder and read it via the settings
  helpers.
- Silence a linter, type error, or failing test with an ignore comment to get
  green. Fix the cause, or explain why the suppression is correct.
- Add a dependency or a new framework layer to make a small change easier. This
  is a starter template; the small surface area is the point.
