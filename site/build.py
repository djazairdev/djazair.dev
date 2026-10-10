#!/usr/bin/env python3
"""Build djazair.dev into site/dist. Standard library only (Python 3.12+).

    python3 site/build.py            # build
    python3 site/build.py --dev      # also build the /_dev/ component pages
    python3 site/build.py --out DIR  # build somewhere else
    python3 site/build.py --all-languages  # also the Arabic pages, to translate or review them
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from djsite.build import main  # noqa: E402

if __name__ == '__main__':
    sys.exit(main())
