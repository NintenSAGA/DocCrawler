import os
import sys

from rich.console import Console

console = Console()

ROOT_PATH = sys.path[0]
GENERAL_CONFIG_PATH = os.path.join(ROOT_PATH, '../general_config.yaml')
MOODLE_CONFIG_PATH = os.path.join(ROOT_PATH, '../moodle_config.yaml')

DOWNLOAD_PATH = os.path.join(ROOT_PATH, '../Download/')
TMP_PATH = os.path.join(ROOT_PATH, './tmp/')

# ---- Moodle ---- #
MAIN_PAGE_URL = 'https://selearning.nju.edu.cn/my/'
SUPPOSE_MAIN_TITLE = '(个人主页|Dashboard)'
