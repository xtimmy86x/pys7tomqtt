import sys
from pathlib import Path

# Ensure project root is on the Python path when running tests directly from
# this repository.  The package contains an ``__init__`` at the root which would
# otherwise require imports like ``pys7tomqtt.attribute`` in the tests.
sys.path.append(str(Path(__file__).resolve().parent.parent))

