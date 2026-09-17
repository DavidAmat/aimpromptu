"""rebuild.py with the core extent installed."""
import sys
sys.path.insert(0, sys.argv[1])
import extent_core; extent_core.install()
exec(open(sys.argv[1] + '/rebuild.py').read())
