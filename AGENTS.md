# AGENTS.md

Operating guide for coding agents working in this repository. Read this before
making changes.

This file deliberately does **not** duplicate other documentation. For project
structure, setup, and environment variables see `README.md`. For the list of
available commands run `make help` — the `Makefile` is the source of truth and
CI calls the same targets. Only rules and context that live nowhere else belong
here.

## Plan large changes before writing code

A change is **large** if any of these are true:

- it touches more than ~5 files, or adds more than ~200 lines;
- it adds or removes a dependency, or introduces a new framework layer;
- it changes settings, URL routing, the build pipeline, CI, or the Docker setup;
- it adds a Django model or a migration;
- it changes public behavior of an existing endpoint.

For a large change: **stop and write the plan first, then wait for the
maintainer to approve it before implementing.** The plan states the problem, the
approach, the files that will change, the test strategy, and anything
explicitly out of scope. Do not open a large pull request whose plan was never
approved — post the plan and wait.

Small, obvious, single-purpose changes do not need a plan. If you are unsure
which side of the line you are on, it needs a plan.

## Verify before you push

Every pull request must pass the full suite locally before it is opened, and
again after any change made in review. Do not push a branch expecting CI to
tell you whether it works — that round trip is what this rule exists to avoid.

```bash
make frontend-build && make verify
```

`make frontend-build` first is not optional. `make verify` renders
`index.html`, which resolves assets through
`frontend/dist/.vite/manifest.json`. On a fresh checkout that file does not
exist and 9 of the 19 tests fail with `DjangoViteAssetNotFoundError` — a
failure that has nothing to do with your change. `make verify` itself does not
build the frontend; CI does it in a separate step.

A change is done when `make frontend-build && make verify` passes from a clean
tree. Report the result honestly: never describe a partial run as a pass, and
if something was already broken before your change, say so plainly instead of
folding it into your diff.

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

## Conventions

**Python**

- `ruff` and `black` both run in `make lint`. Format with `make format` rather
  than hand-aligning code.
- `mypy` runs with `disallow_untyped_defs = true`. **Every function needs full
  type annotations**, including `-> None`. Migrations are excluded.
- Docstrings are Google-style with `Args:`/`Returns:`/`Raises:` sections, and
  every module has one. Match that, even though no linter enforces it.
- The env helpers in `djangovue/settings.py` (`get_env_bool`, `get_env_list`,
  `get_env_int`) take an optional `environ` mapping so they can be tested
  without mutating `os.environ`. Read configuration through them instead of
  touching `os.environ` inline, and keep new config readers in that shape.
- `.github/instructions/effective_python.instructions.md` carries the broader
  Python style guidance this repo follows.

**Frontend**

- The Vite entry point is named in both `vite.config.js` and
  `backend/templates/index.html`. Renaming it means updating both.
- `publicDir` is disabled; static assets go through Django's staticfiles.
- There is no JS linter or JS test runner. Frontend verification is the build
  plus the template and server e2e checks.

**Tests**

- Python tests live in `backend/tests.py`. Use `TestCase` when the database is
  involved and `SimpleTestCase` when it is not.
- Test names describe behavior (`test_index_view_returns_200_status_code`) and
  docstrings use GIVEN / WHEN / THEN. Follow the existing style.
- Settings-related tests reload `djangovue.settings` under `mock.patch.dict` —
  reuse that pattern instead of asserting against process state.

## Git and pull requests

- Work on the branch you were assigned; never push to `master`.
- Push with `git push -u origin <branch>`; retry network failures with backoff.
- Do not open a pull request unless you were explicitly asked to.
- `CONTRIBUTING.md` requires frontend UI changes to be verified in **Safari on
  macOS** as well as Chrome. An agent in a Linux container cannot do this — if
  your change touches Vue/Vite UI, state plainly in the pull request that Safari
  verification is outstanding and needs a human.

## Do not

- Edit or commit generated output: `frontend/dist/`, `staticfiles/`,
  `db.sqlite3`, `node_modules/`, `.venv/`.
- Hand-edit `uv.lock` or `package-lock.json` — use `uv add` / `uv sync` and
  `npm` so the lockfiles stay reproducible.
- Put secrets in code, settings, `docker-compose.yml`, or CI files. Add the
  variable to `.env.example` with a placeholder and read it through the settings
  helpers.
- Silence a linter, type error, or failing test with an ignore comment to get
  green. Fix the cause, or explain why the suppression is correct.
- Add a dependency or a new framework layer to make a small change easier. This
  is a starter template; the small surface area is the point.
