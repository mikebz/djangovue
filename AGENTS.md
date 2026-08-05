# AGENTS.md

Operating guide for coding agents working in this repository. Read this before
making changes.

This is the **only** agent instruction file in the repository. There is no
second copy under `.github/`, no per-tool variant, and no nested override — if a
rule matters, it goes here. This file also does not duplicate other
documentation:

- setup, environment variables, and deployment — `README.md`
- how the code fits together, and where a thing lives — `ARCHITECTURE.md`
- the list of available commands — `make help`, since the `Makefile` is the
  source of truth and CI calls the same targets

Keep it that way when you edit this file. This file carries **rules** — what to
do and what not to do. It does not name individual functions, count tests, or
explain how a subsystem works; that belongs in `ARCHITECTURE.md`, where one
change updates one file. A description copied into two files drifts in one of
them, and a rule that recites implementation detail goes stale every time the
implementation moves.

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

`make frontend-build` first is not optional. Several checks render the Django
template, which cannot resolve frontend assets until the frontend has been
built — on a clean checkout they fail for that reason alone, with nothing wrong
in your change. If you hit asset-resolution failures, you skipped the build;
see *Frontend integration* in `ARCHITECTURE.md`. Do not "fix" them.

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
- `mypy` runs in `strict` mode with the `django-stubs` plugin. **Every function
  needs full type annotations**, including `-> None`, and module-level settings
  carry explicit annotations too. Migrations are excluded. Run `make typecheck`
  rather than bare `mypy` — the target prepares the environment the plugin
  needs to import settings.
- **No function name may exceed 50 characters.** This applies to test functions
  too — if a name does not fit, the test is usually covering too much.
- Docstrings are Google-style with `Args:`/`Returns:`/`Raises:` sections, and
  every module has one. Match that, even though no linter enforces it.
- Read configuration through the env helpers in `djangovue/utils.py`, never by
  touching `os.environ` inline, and keep new config readers in the shape of the
  ones already there.
- Adding a setting: put it in `.env.example` with a placeholder and read it
  through the env helpers. Never re-implement the loading or the
  environment-beats-file precedence.
- Changing what the page loads: anything served from a new origin, or any
  inline script or style, has to be reflected in the Content Security Policy,
  and `{{ csp_nonce }}` comes before `'unsafe-inline'`.
- Broader style guidance follows *Effective Python* — see
  https://github.com/SigmaQuan/Better-Python-59-Ways.

**Frontend**

- The Vite entry point is named in both the Vite config and the Django
  template. Renaming it means updating both.
- Static assets go through Django's staticfiles, not Vite's public directory.
  Do not add a second static pipeline.
- There is no JS linter or JS test runner. Frontend verification is the build
  plus the template and server e2e checks.

**Tests**

- Python tests live in the `backend/tests/` package, one `test_<subject>.py`
  per subject. Add a test to the module whose subject it matches, or start a
  new module — do not let one grow into a catch-all.
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

  Some older tests still carry a `GIVEN:`/`WHEN:`/`THEN:` form. That style is
  retired: write new tests with the outline above, and convert a docstring you
  are already editing. Do not convert the rest as a drive-by — a whole-file
  conversion is its own structural commit.

- Settings-related tests reload the settings module under a patched
  environment — reuse that pattern instead of asserting against process state.

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
