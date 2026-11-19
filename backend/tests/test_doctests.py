"""Run the `>>>` examples in project docstrings as part of the test suite.

Docstrings across the project carry examples. Django's test runner does not
collect doctests on its own, so without this module a wrong example would pass
`make test` unnoticed. Modules are discovered by walking the project packages,
so a new or renamed module needs no change here.
"""

import doctest
import importlib
import pkgutil
import unittest
from types import ModuleType

import backend
import djangovue

PACKAGES: tuple[ModuleType, ...] = (backend, djangovue)
# Migrations are generated, and the tests package is what is running this.
SKIPPED_SUBPACKAGES: tuple[str, ...] = ("migrations", "tests")
# Importing these builds the whole WSGI/ASGI handler and middleware stack as a
# side effect, and neither carries doctests.
SKIPPED_MODULES: tuple[str, ...] = ("djangovue.asgi", "djangovue.wsgi")


def _project_modules() -> list[ModuleType]:
    """Import and return every module in the project packages.

    Returns:
        The package modules themselves and every submodule, except the
        skipped modules and those in the skipped subpackages.

    """
    modules: list[ModuleType] = list(PACKAGES)
    for package in PACKAGES:
        for info in pkgutil.walk_packages(package.__path__, f"{package.__name__}."):
            if info.name in SKIPPED_MODULES or any(
                part in SKIPPED_SUBPACKAGES for part in info.name.split(".")
            ):
                continue
            modules.append(importlib.import_module(info.name))
    return modules


def load_tests(
    loader: unittest.TestLoader,
    tests: unittest.TestSuite,
    pattern: str | None,
) -> unittest.TestSuite:
    """Add each project module's doctests to this module's test suite.

    This is the unittest `load_tests` protocol, which Django's runner honors.
    https://docs.python.org/3/library/unittest.html#load-tests-protocol

    Args:
        loader: The loader collecting tests (unused).
        tests: The tests already found in this module.
        pattern: The discovery pattern (unused).

    Returns:
        The suite with every project doctest added.

    """
    for module in _project_modules():
        tests.addTests(doctest.DocTestSuite(module))
    return tests
