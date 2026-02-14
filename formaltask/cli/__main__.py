"""Allow formaltask.cli to be run as: python -m formaltask.cli"""

import sys

from .pm import main

if __name__ == "__main__":
    sys.exit(main())
