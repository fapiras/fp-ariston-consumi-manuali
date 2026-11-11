"""Import the private client directly for its independent upstream tests."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[2] / 'custom_components/fp_ariston_consumi/vendor'))
