import sys
from pathlib import Path

# Ensure the package root is importable as ``pys7tomqtt`` when running tests
# directly from this repository.
# ``Path(__file__).resolve().parent`` -> tests/
#                          .parent   -> project root (pys7tomqtt/)
#                          .parent   -> repository root containing the package
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

