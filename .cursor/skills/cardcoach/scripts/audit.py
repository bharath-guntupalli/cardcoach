#!/usr/bin/env python3
"""Run CardCoach maths without fetching the web.

python scripts/audit.py audit --transactions txns.csv --rules rules.json --summary summary.json
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import main

if __name__ == "__main__":
    raise SystemExit(main())
