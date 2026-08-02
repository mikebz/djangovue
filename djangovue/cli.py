"""Console entry point for Django management commands.

Installed as the ``manage`` script (see ``[project.scripts]`` in
pyproject.toml), so commands can be run as ``uv run manage <command>``.
``manage.py`` in the project root calls the same function.

Author: Mike Borozdin (mikebz@)
"""

import os
import sys


def main() -> None:
    """Run Django management commands from the command line."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djangovue.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        # The above import may fail for some other reason. Ensure that the
        # issue is really that Django is missing.
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)
