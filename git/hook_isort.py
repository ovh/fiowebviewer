#!/usr/bin/env python
import sys

from isort.hooks import (
    git_hook,
)

"""
Git pre-commit hook to check staged files for isort errors
:param bool strict - if True, return number of errors on exit,
    causing the hook to fail. If False, return zero so it will
    just act as a warning.
:return number of errors if in strict mode, 0 otherwise.
"""

if __name__ == '__main__':
    sys.exit(git_hook(strict=True))
