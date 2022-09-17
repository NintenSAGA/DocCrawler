import sys
import os
from rich.console import Console


console = Console()

ROOT_PATH = sys.path[0]
DOWNLOAD_PATH = os.path.join(ROOT_PATH, 'Download/')
CONFIG_PATH = os.path.join(ROOT_PATH, '../config.yaml')