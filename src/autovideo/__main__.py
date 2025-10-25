"""Allow running autovideo as a module: python -m autovideo"""

import sys
from .cli import main

if __name__ == '__main__':
    sys.exit(main())
