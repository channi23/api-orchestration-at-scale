"""Initialize the future run's swap window, before model loading and after review approval."""
import json
from .e0b import config
from .resources import initialize_swap_baseline

if __name__=='__main__':
    print(json.dumps(initialize_swap_baseline(config()),indent=2))
