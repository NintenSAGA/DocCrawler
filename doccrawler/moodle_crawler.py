import os.path
import re
import urllib.parse
from http.cookies import SimpleCookie

import bs4
import requests
import yaml
from rich import prompt as _prompt

import engine
from const import console, MAIN_PAGE_URL, SUPPOSE_MAIN_TITLE, MOODLE_CONFIG_PATH, DOWNLOAD_PATH


def load_config() -> (dict, dict):
    if not os.path.exists(MOODLE_CONFIG_PATH):
        return {}, {}
    with open(MOODLE_CONFIG_PATH, 'r') as fd:
        config_dict = yaml.safe_load(fd)
    if config_dict is None:
        return {}, {}
    if 'moodle' in config_dict.keys():
        return config_dict, config_dict['moodle']
    else:
        return config_dict, {}


def save_config(moodle_config, config_dict):
    config_dict['moodle'] = moodle_config
    with open(MOODLE_CONFIG_PATH, 'w') as fd:
        yaml.safe_dump(config_dict, fd, allow_unicode=True)


def fetch_course_list(cookies, moodle_config):
    response = requests.get(MAIN_PAGE_URL, cookies=cookies)
    html = response.content.decode('utf-8')
    soup = bs4.BeautifulSoup(html, 'html.parser')

    title = soup.title.text
    if title != SUPPOSE_MAIN_TITLE:
        return None

    # Course data
    info_dicts = {}
    if 'courses' in moodle_config.keys() and moodle_config['courses'] is not None:
        info_dicts = moodle_config['courses']

    # ---- Find all the course IDs ---- #
    pat = re.compile(r'.*/course/.*')
    courses = soup.find_all(name='a', href=pat)
    results = []
    for course in courses:
        url = course['href']
        cid = int(url.split('=')[-1])
        name = course.find_next(name='span', attrs={'class': 'media-body'}).text
        console.print(f'Found: {name}')

        info = {}
        if cid in info_dicts.keys():
            info = info_dicts[cid]
        if 'dir' not in info.keys():
            info['dir'] = os.path.join(DOWNLOAD_PATH, name)
            if not os.path.exists(info['dir']):
                os.makedirs(info['dir'])
        if 'name' not in info.keys():
            info['name'] = name
        if 'my_args' not in info.keys():
            info['my_args'] = []

        info_dicts[cid] = info
        results.append((url, cid))

    moodle_config['courses'] = info_dicts
    return results


def driver():
    # ---- Load config ---- #
    config_dict, moodle_config = load_config()
    parser = engine.get_arg_parser()
    auth_ok = 'cookies' in moodle_config.keys()
    while True:
        if not auth_ok:
            raw_cookies = _prompt.Prompt.ask('Please enter your cookies')
            moodle_config['cookies'] = raw_cookies
        else:
            raw_cookies = str(moodle_config['cookies'])
        sc = SimpleCookie()
        for cookie in raw_cookies.split('; '):
            cookie = urllib.parse.quote(cookie, safe='=')
            sc.load(cookie)
        cookies = {k: v.value for k, v in sc.items()}

        try:
            courses = fetch_course_list(cookies, moodle_config)
        except Exception as e:
            print(e)
            courses = None

        if courses is None:
            console.print('[red]Invalid cookies. Please retry.')
            auth_ok = False
        else:
            break

    save_config(moodle_config, config_dict)

    for course in courses:
        course_info = moodle_config['courses'][course[1]]
        argv = ['-u', course[0],
                '-r', 'https://selearning.nju.edu.cn/mod/resource/.*',
                '-d', course_info['dir']]
        argv += course_info['my_args']
        args = vars(parser.parse_args(argv))
        engine.CrawlTask(args, cookies).run()


if __name__ == '__main__':
    driver()
