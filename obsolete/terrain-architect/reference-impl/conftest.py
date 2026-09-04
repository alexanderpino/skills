"""Put the package root and tests/ on sys.path so tests can `import flow`,
`import inputs`, `import asserts` without packaging ceremony."""
import os
import sys

_here = os.path.dirname(__file__)
for _p in (_here, os.path.join(_here, "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
