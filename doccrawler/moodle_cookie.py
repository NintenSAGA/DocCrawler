import datetime
import os.path
import time

import bs4
import requests
from PIL import Image

from const import TMP_PATH, console
from doccrawler.const import QR_IMG_PATH, MOODLE_LOGIN, AUTH_API, QR_API, CHECK_API

if not os.path.exists(TMP_PATH):
    os.makedirs(TMP_PATH)


def __ts():
    return int((datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)).total_seconds() * 1000)


def getCookie() -> str:
    session = requests.session()
    r = session.get(MOODLE_LOGIN, allow_redirects=True)
    soup = bs4.BeautifulSoup(r.content.decode('utf-8'), 'html.parser')

    form = soup.find(name='form', id='qrLoginForm')
    payload = {}
    for child in form.find_all(name='input'):
        payload[child['name']] = child['value']

    login_api = f"https://authserver.nju.edu.cn{form['action']}"

    auth = AUTH_API.format(__ts())
    uuid = session.get(auth).text
    payload['uuid'] = uuid

    qr = QR_API.format(uuid)
    r = session.get(qr)
    with open(QR_IMG_PATH, 'wb') as fd:
        fd.write(r.content)
    img = Image.open(QR_IMG_PATH)
    img.show()

    check = CHECK_API.format(__ts(), uuid)
    status = 0
    console.print('> Please scan the QR code with WeChat...')
    while status != '1':
        status = session.get(check).text
        time.sleep(0.5)
    console.print('[green]Scanned!')
    os.remove(QR_IMG_PATH)

    session.post(login_api, data=payload, allow_redirects=True)
    return f'MoodleSession={session.cookies["MoodleSession"]}'
