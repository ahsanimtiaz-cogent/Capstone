import sys
from pathlib import Path

# Make lang-graph/ importable for tests (so `from graph...` resolves).
_HERE = Path(__file__).resolve().parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
