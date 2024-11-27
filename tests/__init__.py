# Include "from tests import torrentula" at top of each test file to load the following:

# Add parent directory to sys.path to make 'torrentula' package importable
import sys
import os
current_dir = os.path.dirname(__file__)
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(parent_dir)
import torrentula