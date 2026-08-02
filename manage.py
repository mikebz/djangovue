#!/usr/bin/env python
"""Django command-line utility for administrative tasks.

The implementation lives in djangovue/cli.py so that it can also be installed
as the ``manage`` console script; see ``[project.scripts]`` in pyproject.toml.

Author: Mike Borozdin (mikebz@)
"""

from djangovue.cli import main

if __name__ == "__main__":
    main()
