# AGENTS.md

Operating guide for coding agents working in this repository. Read this before
making changes.

This is the **only** agent instruction file in the repository. There is no
second copy under `.github/`, no per-tool variant, and no nested override — if a
rule matters, it goes here. This file also does not duplicate other
documentation: for project structure, setup, and environment variables see
`README.md`; for the list of available commands run `make help`, since the
`Makefile` is the source of truth and CI calls the same targets.

## Plan large changes before writing code

A change is **large** if any of these are true:

- it touches more than 3 files, or adds more than 100 lines;
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

## How to work: TDD and Tidy First

Development follows Kent Beck's Test-Driven Development and Tidy First
discipline. Prioritize clean, well-tested code over quick implementation.

**The cycle — Red, Green, Refactor:**

1. Write one failing test that defines the smallest next increment of
   behavior. One test at a time.
2. Write the least code that makes it pass. No more.
3. Refactor only once tests are green, one named refactoring at a time,
   re-running tests after each step.
4. Repeat. Run the full suite on every increment.

**Tidy First — never mix structural and behavioral changes:**

- *Structural* changes rearrange code without changing behavior: renaming,
  extracting a method, moving code.
- *Behavioral* changes add or modify functionality.
- When both are needed, make the structural change first, in its own commit,
  with tests passing before and after to prove behavior did not shift.

**Commit discipline** — commit only when tests pass, linter and type warnings
are resolved, and the change is a single logical unit. Prefer small, frequent
commits, and say in the message whether the commit is structural or behavioral.

**Code quality** — eliminate duplication ruthlessly, express intent through
naming and structure, make dependencies explicit, keep functions small and
single-purpose, minimize state and side effects, and use the simplest solution
that could possibly work.

Leave a comment when a design decision is non-obvious, and include the URL when
the reasoning comes from an external source.

## Conventions

**Python**

- `ruff` and `black` both run in `make lint`. Format with `make format` rather
  than hand-aligning code.
- `mypy` runs with `disallow_untyped_defs = true`. **Every function needs full
  type annotations**, including `-> None`. Migrations are excluded.
- **No function name may exceed 50 characters.** This applies to test functions
  too — if a name does not fit, the test is usually covering too much.
- Docstrings are Google-style with `Args:`/`Returns:`/`Raises:` sections, and
  every module has one. Match that, even though no linter enforces it.
- The env helpers in `djangovue/settings.py` (`get_env_bool`, `get_env_list`,
  `get_env_int`) take an optional `environ` mapping so they can be tested
  without mutating `os.environ`. Read configuration through them instead of
  touching `os.environ` inline, and keep new config readers in that shape.
- Broader style guidance follows *Effective Python* — see
  https://github.com/SigmaQuan/Better-Python-59-Ways.

**Frontend**

- The Vite entry point is named in both `vite.config.js` and
  `backend/templates/index.html`. Renaming it means updating both.
- `publicDir` is disabled; static assets go through Django's staticfiles.
- There is no JS linter or JS test runner. Frontend verification is the build
  plus the template and server e2e checks.

**Tests**

- Python tests live in `backend/tests.py`.
- **Prefer test functions over test classes.** Reach for a class only when the
  test genuinely needs one — shared fixture setup that cannot be expressed as a
  plain helper, or a Django facility that requires a `TestCase` subclass.
- Test names describe the behavior under test
  (`test_index_view_returns_200_status_code`) and stay within the 50-character
  function-name limit.
- **Every test carries an outline docstring** with three labelled parts:

  ```python
  def test_index_view_returns_200(self) -> None:
      """Intent: the root URL serves the Vue shell to anonymous visitors.

      Steps:
          1. Build a test client with no authentication.
          2. GET "/".

      Verification:
          The response status is 200.
      """
  ```

  *Intent* says what behavior is being protected and why it matters. *Steps*
  lists what the test does, in order. *Verification* states exactly what is
  asserted. A test whose intent cannot be written in one sentence is testing
  more than one thing — split it.

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

- Add a second agent instruction file. Rules belong in this file, at the
  repository root, and nowhere else.
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
