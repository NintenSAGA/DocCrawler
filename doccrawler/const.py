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
QR_IMG_PATH = os.path.join(TMP_PATH, './qrcode.png')
MOODLE_LOGIN = 'https://selearning.nju.edu.cn/login/index.php?authCAS=CAS'
AUTH_API = 'https://authserver.nju.edu.cn/authserver/qrCode/get?ts={}'
QR_API = 'https://authserver.nju.edu.cn/authserver/qrCode/code?uuid={}'
CHECK_API = 'https://authserver.nju.edu.cn/authserver/qrCode/status?ts={}&uuid={}'
MOODLE_AUTH_API = 'https://selearning.nju.edu.cn/login/index.php?authCAS=CAS&ticket={}'

MOODLE_RESOURCE_PAT = 'https://selearning.nju.edu.cn/mod/resource/.*'
MOODLE_FOLDER_PAT = 'https://selearning.nju.edu.cn/mod/folder/.*'
