import os
import re
import sys
from concurrent import futures as _futures
from urllib import parse as _parse

import bs4
import requests
from rich import progress as _progress, panel as _panel, columns as _columns
from rich.markup import escape

from const import DOWNLOAD_PATH, console

class BoxProgress(_progress.Progress):
    def get_renderables(self):
        yield _panel.Panel(self.make_tasks_table(self.tasks), border_style='white')


def download_doc(download_path: str, url: str, filename: str) -> str:
    response = requests.get(url)
    ext = response.url.split('.')[-1]
    if ext.endswith('/'):
        ext = 'html'
    filename = filename.removesuffix(f'.{ext}')
    path = os.path.join(download_path, f'{filename}.{ext}')
    with open(path, mode='wb') as fd:
        fd.write(response.content)

    return filename


def fetch_url(url: str):
    response = requests.get(url)
    return response.content.decode('utf-8')


def single_task(args):
    console.print()

    # Fetch url
    url = args['url']
    if not args['url']:
        console.print(_panel.Panel('Please enter the url:'))
        url = console.input('> ')

    if not url.startswith('http'):
        url = 'https://' + url
    # console.print(f'< [white]URL: {url}')

    # Fetch URL #
    with console.status(f"Fetching {url}..."):
        try:
            html_text = fetch_url(url)
        except requests.exceptions.RequestException as e:
            console.print(f'[red]Fetch failed!\n{e}')
            sys.exit(1)

    # Load extensions
    extensions = []
    if not args['all']:
        if args['ex']:
            extensions = args['ex']
        else:
            console.print('Please enter file extensions\n(Separate with blank, no leading dot. Empty for all.):')
            extensions = console.input('> ')
            extensions = extensions.split()

    # Parse download url from HTML
    soup = bs4.BeautifulSoup(html_text, 'html.parser')
    title = soup.title.text
    # title = title.replace(' ', '_')
    download_path = os.path.join(DOWNLOAD_PATH, title)

    if args['dir'] != '':
        download_path = args['dir']
        if not os.path.exists(download_path):
            console.print(f'[red]Directory {download_path} not exists!')
            sys.exit(1)
    else:
        if not os.path.exists(download_path):
            os.makedirs(download_path)

    console.print(
        _panel.Panel(
            title=f'[dark_orange underline bold italic]{title}[/]',
            renderable=f'[white]Will be saved at [underline]{escape(download_path)}[/underline]'
        ), style='dark_orange'
    )

    if len(extensions) == 0:
        args['all'] = True
        console.print('Matching all extensions')
    else:
        console.print(f'Extensions: {extensions}')

    queue = []
    url_set = set()
    order = 1
    with console.status('Crawling documents...'):
        try:
            if args['all']:
                ext_str = '[^/]+'
            else:
                ext_str = f"({'|'.join(extensions)})"
            tags = soup.find_all(name='a', href=re.compile(rf'.*\.{ext_str}$'))
        except re.error as e:
            console.print(f'[red]Bad extensions: {extensions}\nMessage: {e}')
            sys.exit(1)

        if len(tags) == 0:
            console.print('No document was found!')
            return

        for tag in tags:
            furl = tag['href']

            name = furl.split('/')[-1]
            if args['name']:
                if tag.text.strip() != '':
                    name = tag.text.strip()
                elif 'title' in tag.attrs:
                    name = tag['title'].strip()

            if args['order']:
                name = f'{order}. {name}'
                order += 1
            furl = _parse.urljoin(url, furl)
            if furl not in url_set:
                url_set.add(furl)
                queue.append((furl, name))
                # console.log(f'Found: {queue[-1]}')

    console.print(f'Found {len(queue)} documents in total.')
    failed = 0

    with BoxProgress(
            _progress.TextColumn("[progress.description]{task.description}"),
            _progress.SpinnerColumn(),
            _progress.BarColumn(),
            _progress.TaskProgressColumn(),
            _progress.TimeElapsedColumn(),
    ) as progress, \
            _futures.ThreadPoolExecutor() as executor:
        futures = []
        for pair in queue:
            futures.append(executor.submit(download_doc, download_path, pair[0], pair[1]))

        completed, total = 0, len(queue)
        task = progress.add_task('Downloading...', total=total)
        while completed < total:
            done, not_done = _futures.wait(futures, return_when=_futures.FIRST_COMPLETED)

            for future in done:
                if future.exception() is None:
                    name = future.result()
                    progress.console.print(f'< [white]Downloaded: {name}')
                else:
                    failed += 1
                completed += 1
                progress.update(task, completed=completed)

            futures = list(not_done)
        progress.update(task, description='[green]Completed')

    success = len(queue) - failed

    columns = _columns.Columns(expand=True)
    columns.add_renderable(_panel.Panel(f'{success}', title='Success', style='green'))
    columns.add_renderable(_panel.Panel(f'{failed}', title='Failed', style='red'))
    console.print(columns, justify='center')

    console.rule('[light_slate_blue bold italic]Task complete![/]', style='light_slate_blue')
