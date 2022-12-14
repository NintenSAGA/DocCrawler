import argparse
import os
import re
import urllib.parse
import zipfile
from concurrent import futures as _futures
from urllib import parse as _parse

import bs4
import rarfile
import requests
from rich import progress as _progress, panel as _panel, columns as _columns
from rich.markup import escape

import taskexception
from const import DOWNLOAD_PATH, console


class TaskInfo:
    def __init__(self,
                 download_path, url, filename,
                 order, cookies, update,
                 unzip):
        self.download_path = download_path
        self.url = url
        self.filename = filename
        self.order = order
        self.cookies = cookies
        self.update = update
        self.unzip = unzip


class BoxProgress(_progress.Progress):
    def get_renderables(self):
        yield _panel.Panel(self.make_tasks_table(self.tasks), border_style='white')


def get_arg_parser():
    # Argument parsing
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('-u', '--url', help='Target url', type=str)
    arg_parser.add_argument('-r', '--regex', help='Target regex', type=str, default='')
    arg_parser.add_argument('-e', '--ex', help='Target extensions', type=str, nargs='+')
    arg_parser.add_argument('-a', '--all', help='Match all', action='store_true')
    arg_parser.add_argument('-n', '--name', help='Use tag text as filename', action='store_true')
    arg_parser.add_argument('-d', '--dir', help='Output directory', type=str, default='')
    arg_parser.add_argument('-o', '--order', help='Add order prefix', action='store_true')
    arg_parser.add_argument('-U', '--update', help='Update existed file', action='store_true')
    arg_parser.add_argument('-z', '--unzip', help='Unzip compressed files', action='store_true')

    return arg_parser


def open_page(url, cookies={}):
    return bs4.BeautifulSoup(requests.get(url, cookies=cookies).content.decode('utf-8'), 'html5lib')


def download_doc(task: TaskInfo, my_console=console) -> (str, bool):
    response = requests.get(task.url, cookies=task.cookies, stream=True)
    path_str = urllib.parse.urlparse(response.url).path
    path_str = os.path.split(path_str)[-1]
    path_str = urllib.parse.unquote(path_str)

    if task.filename is None:
        filename = path_str
    else:
        ext = path_str.split('.')[-1]
        if ext.endswith('/'):
            ext = 'html'
        filename = task.filename.removesuffix(f'.{ext}')
        filename = f'{filename}.{ext}'

    filename = task.order + filename
    path = os.path.join(task.download_path, filename)

    # ---- Update ---- #
    updated = False
    if task.update or not os.path.exists(path):
        updated = True
        with open(path, mode='wb') as fd:
            for chunk in response.iter_content(chunk_size=128):
                fd.write(chunk)

    # ---- Unzip ---- #
    if updated and task.unzip and re.match(r'.*(rar|zip)$', filename) is not None:
        out_dir = os.path.join(task.download_path, re.sub(r'\.[^.]*$', '', filename, count=1))
        if not os.path.exists(out_dir):
            os.mkdir(out_dir)

        unzipped = False
        if filename.endswith('zip'):
            with zipfile.ZipFile(path) as zf:
                zi = zf.infolist()
                for member in zi:
                    member.filename = member.filename.encode('cp437').decode('gbk')
                    zf.extract(member, path=out_dir)
            unzipped = True
        elif filename.endswith('rar'):
            try:
                with rarfile.RarFile(path) as rf:
                    ri = rf.infolist()
                    for member in ri:
                        rf.extract(member, path=out_dir)
                unzipped = True
            except Exception as e:
                my_console.print(f'[red]Got error: {e}')
                if os.uname().sysname == 'Darwin':
                    my_console.print('Try install unrar on your mac: \nbrew install carlocab/personal/unrar')
        if unzipped:
            my_console.print(f'< [white]Unzipped: {filename}')

    response.close()
    return filename, updated


def parallel_process(queue: list[TaskInfo]):
    failed = 0
    with BoxProgress(
            _progress.TextColumn("[progress.description]{task.description}"),
            _progress.SpinnerColumn(),
            _progress.BarColumn(),
            _progress.TaskProgressColumn(),
            _progress.TimeElapsedColumn(),
    ) as progress, \
            _futures.ThreadPoolExecutor(max_workers=32) as executor:
        # ---- Setup workers ---- #
        completed, total = 0, len(queue)
        task = progress.add_task('Downloading...', total=total)
        futures = []
        for t_info in queue:
            futures.append(executor.submit(download_doc, t_info, progress.console))
        # ---- Working Loop ---- #
        file_list = []
        while completed < total:
            done, not_done = _futures.wait(futures, return_when=_futures.FIRST_COMPLETED)
            # ---- Gather results ---- #
            for future in done:
                if future.exception() is None:
                    name, updated = future.result()
                    file_list.append((name, updated))
                    progress.console.print(f'< [white]{"Downloaded" if updated else "Existed"}: {name}')
                else:
                    progress.console.print(f'[red]{future.exception()}')
                    failed += 1
                completed += 1
            progress.update(task, completed=completed)
            # Update futures
            futures = list(not_done)

        # ---- Fin ---- #
        progress.update(task, description='[green]Completed')

    success = len(queue) - failed
    return success, failed


class CrawlTask:
    def __init__(self, args, cookies=None):
        if cookies is None:
            cookies = {}
        self.args = args
        self.cookies = cookies

        self.url: str

        self.html_text: str
        self.download_path: str
        self.title: str

        self.soup: bs4.BeautifulSoup

    def __fetch_url(self):
        # Fetch url
        url = self.args['url']
        if not url:
            console.print(_panel.Panel('Please enter the url:'))
            url = console.input('> ')

        if not url.startswith('http'):
            url = 'https://' + url

        # Fetch URL #
        with console.status(f"Fetching {url}..."):
            try:
                response = requests.get(url, cookies=self.cookies)
                self.html_text = response.content.decode('utf-8')
            except requests.exceptions.RequestException as e:
                console.print(f'[red]Fetch failed!\n{e}')
                raise taskexception.TaskException()
        self.url = url

    def __load_ext(self):
        # Load extensions
        extensions = []
        if not self.args['all']:
            if self.args['ex']:
                extensions = self.args['ex']
            else:
                console.print('Please enter file extensions\n(Separate with blank, no leading dot. Empty for all.):')
                extensions = console.input('> ')
                extensions = extensions.split()
        return extensions

    def __get_pattern_with_ext(self):
        ext = self.__load_ext()

        if len(ext) == 0:
            self.args['all'] = True
            # console.print('Matching all extensions')
        else:
            # console.print(f'Extensions: {ext}')
            pass

        try:
            if self.args['all']:
                ext_str = '[^/]+'
            else:
                ext_str = f"({'|'.join(ext)})"

            return re.compile(rf'.*\.{ext_str}$')
        except re.error as e:
            console.print(f'[red]Bad extensions: {ext}\nMessage: {e}')
            raise taskexception.TaskException()

    def __get_pattern_with_regex(self):
        re_str = self.args['regex']
        # console.print(f'Matching pattern {re_str}')
        return re.compile(rf'{re_str}')

    def __get_pattern(self):
        if self.args['regex'] == '':
            return self.__get_pattern_with_ext()
        else:
            return self.__get_pattern_with_regex()

    def __collect_docs(self):
        self.soup = bs4.BeautifulSoup(self.html_text, 'html.parser')
        self.title = self.soup.title.text

        # ---- Check whether download path is legal ---- #
        self.download_path = os.path.join(DOWNLOAD_PATH, self.title)
        if self.args['dir'] != '':
            self.download_path = self.args['dir']
            if not os.path.exists(self.download_path):
                console.print(f'[red]Directory {self.download_path} not exists!')
                raise taskexception.TaskException()
        else:
            if not os.path.exists(self.download_path):
                os.makedirs(self.download_path)

        # Get Regex pattern
        pat = self.__get_pattern()

        # ---- Salutations ---- #
        console.print(_panel.Panel(
            title=f'[dark_orange underline bold italic]{self.title}[/]',
            renderable=f'[white]Will be saved at [underline]{escape(self.download_path)}[/underline]'
        ), style='dark_orange')

        # ---- Crawl all the documents' link ---- #
        url_map = {}
        order = 1
        with console.status('Crawling documents...'):
            tags = self.soup.find_all(name='a', href=pat)
            if len(tags) == 0:
                console.print('No document was found!')
                return None
            for tag in tags:
                furl = tag['href']
                # Whether change names
                name = None
                this_order = ''
                if self.args['name']:
                    if tag.text.strip() != '':
                        name = tag.text.strip()
                    elif 'title' in tag.attrs:
                        name = tag['title'].strip()
                # Whether add order prefix
                if self.args['order']:
                    this_order = str(order) + '. '
                    order += 1
                # Redirect URL
                furl = _parse.urljoin(self.url, furl)

                if furl not in url_map.keys():
                    url_map[furl] = TaskInfo(self.download_path, furl, name, this_order,
                                             self.cookies, self.args['update'], self.args['unzip'])

        console.print(f'Found {len(url_map)} documents in total.')
        return list(url_map.values())

    def run(self):
        console.print()

        self.__fetch_url()
        queue = self.__collect_docs()
        if queue is None:
            return
        success, failed = parallel_process(queue)

        columns = _columns.Columns(expand=True)
        columns.add_renderable(_panel.Panel(f'{success}', title='Success', style='green'))
        columns.add_renderable(_panel.Panel(f'{failed}', title='Failed', style='red'))
        console.print(columns, justify='center')

        console.rule('[light_slate_blue bold italic]Task complete![/]', style='light_slate_blue')
