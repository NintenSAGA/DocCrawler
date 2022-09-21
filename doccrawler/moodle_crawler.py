import os.path
import re
import urllib.parse
from http.cookies import SimpleCookie

import bs4
import requests
import yaml

import engine
import moodle_cookie
from const import console, MAIN_PAGE_URL, SUPPOSE_MAIN_TITLE, \
    MOODLE_CONFIG_PATH, DOWNLOAD_PATH, SLIDE_SEC_CHN, VIDEO_SEC_CHN, MOODLE_RESOURCE_PAT, MOODLE_FOLDER_PAT


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
    if re.match(rf'{SUPPOSE_MAIN_TITLE}', title.strip()) is None:
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
        # console.print(f'Found: {name}')

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
        if 'exclude' not in info.keys():
            info['exclude'] = False

        info_dicts[cid] = info
        results.append({'url': url, 'cid': cid})

    moodle_config['courses'] = info_dicts
    return results


def driver():
    # ---- Load config ---- #
    config_dict, moodle_config = load_config()
    parser = engine.get_arg_parser()
    auth_ok = 'cookies' in moodle_config.keys()
    while True:
        if not auth_ok:
            # raw_cookies = _prompt.Prompt.ask('Please enter your cookies')
            raw_cookies = moodle_cookie.getCookie()
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

    queue = []
    for course in courses:
        url = course['url']
        cid = course['cid']
        course_info = moodle_config['courses'][cid]
        if course_info['exclude']:
            console.print(f'> Excluded: {course_info["name"]}')
            continue

        args = vars(parser.parse_args(course_info['my_args']))

        home_soup = engine.open_page(url, cookies)
        sec_map = {}

        for section in home_soup.find_all(name='li', id=re.compile(r'section-[0-9]')):
            name = section.h3.text.strip()
            sec_map[name] = section

        # ---- Slides ---- #
        if SLIDE_SEC_CHN in sec_map.keys():
            slide_sec = sec_map[SLIDE_SEC_CHN]
            # Simple files
            tags = slide_sec.find_all(name='a', href=re.compile(MOODLE_RESOURCE_PAT))
            for i, tag in enumerate(tags, start=1):
                # print(tag.text)
                url = tag['href']
                name = None
                order = ''
                if args['name']:
                    name = tag.text.strip()
                if args['order']:
                    order = f'{i}. '
                queue.append(engine.TaskInfo(course_info['dir'], url, name,
                                             order, cookies, args['update'],
                                             args['unzip']))
            # Folders
            tags = slide_sec.find_all(name='a', href=re.compile(MOODLE_FOLDER_PAT))
            for tag in tags:
                furl = tag['href']
                out_dir = os.path.join(course_info['dir'], tag.text)
                out_dir = out_dir.rstrip(' 文件夹').rstrip(' Folder')
                if not os.path.exists(out_dir):
                    os.makedirs(out_dir)
                folder = engine.open_page(furl, cookies)
                sub_tags = folder.find_all(name='a', href=re.compile(f'.*mod_folder.*'))
                for i, sub_tag in enumerate(sub_tags, start=1):
                    sub_url = sub_tag['href']
                    name = None
                    order = ''
                    if args['name']:
                        name = sub_tag.text.strip()
                    if args['order']:
                        order = f'{i}. '
                    queue.append(engine.TaskInfo(out_dir, sub_url, name,
                                                 order, cookies, args['update'],
                                                 args['unzip']))
        # ---- Videos ---- #
        if VIDEO_SEC_CHN in sec_map.keys():
            ans = console.input('Found videos. Would you like to download them? (Y/N)')
            if ans.lower() != 'y':
                continue
            video_sec = sec_map[VIDEO_SEC_CHN]
            tags = video_sec.find_all(name='a', href=re.compile(MOODLE_RESOURCE_PAT))
            out_dir = os.path.join(course_info['dir'], 'videos')
            if not os.path.exists(out_dir):
                os.makedirs(out_dir)
            for i, tag in enumerate(tags, start=1):
                video = engine.open_page(tag['href'], cookies)
                v_tag = video.find(name='source', type='video/mp4')
                v_url = v_tag['src']
                name = None
                order = ''
                if args['name']:
                    name = v_tag.text.strip()
                if args['order']:
                    order = f'{i}. '
                queue.append(engine.TaskInfo(out_dir, v_url, name,
                                             order, cookies, args['update'],
                                             args['unzip']))

        console.print(f'> Found {len(queue)} files for {course_info["name"]}')

    engine.parallel_process(queue)
    # soup = bs4.BeautifulSoup(requests.get(course[0], cookies=cookies).content.decode('utf-8'), 'html.parser')
    # for tag in soup.find_all(name='a', href=re.compile(MOODLE_FOLDER_PAT)):
    #     url = urllib.parse.urljoin(course[0], tag['href'])


if __name__ == '__main__':
    driver()
