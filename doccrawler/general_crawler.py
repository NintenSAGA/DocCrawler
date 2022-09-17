#!/usr/bin/env python3

import argparse
import os.path

import yaml
from rich import panel as _panel, prompt as _prompt

import const
import engine


def load_config(args) -> list[dict] | None:
    # Load config
    if not args['url']:
        config_dict = {}
        if os.path.exists(const.CONFIG_PATH):
            with open(const.CONFIG_PATH, 'r') as fd:
                config_dict = yaml.safe_load(fd)
        if 'websites' in config_dict and len(config_dict['websites']) != 0:
            entries = list(config_dict['websites'].items())
            entries.insert(0, ('None', ''))
            entries.append(('All', ''))
            choices = [str(i) for i in range(0, len(entries))]
            choice_prompt = []
            for i, entry in enumerate(entries):
                choice_prompt.append(f'[green bold]{i}[/] - {entry[0]}')
            engine.console.print(_panel.Panel('\n'.join(choice_prompt), title='Found existed presets:'))

            choice = _prompt.IntPrompt.ask('Choose one', choices=choices, default=0, show_choices=False)
            if choice == len(choices) - 1:
                arg_list = []
                for i in range(1, len(entries) - 1):
                    web_config = entries[i][1]
                    tmp_args = args.copy()
                    for key, val in web_config.items():
                        tmp_args[key] = val
                    arg_list.append(tmp_args)
                return arg_list
            elif choice != 0:
                web_config = entries[choice][1]
                for key, val in web_config.items():
                    args[key] = val
    return None


def parse_args():
    # Argument parsing
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('-u', '--url', help='Target url', type=str)
    arg_parser.add_argument('-e', '--ex', help='Target extensions.', type=str, nargs='+')
    arg_parser.add_argument('-a', '--all', help='Match all', action='store_true')
    arg_parser.add_argument('-n', '--name', help='Use tag text as filename', action='store_true')
    arg_parser.add_argument('-d', '--dir', help='Output directory', type=str, default='')
    arg_parser.add_argument('-o', '--order', help='Add order prefix', action='store_true')
    args = arg_parser.parse_args()
    return vars(args)


def driver():
    engine.console.clear()
    engine.console.print(
        _panel.Panel('Presented by [bold italic]NintenSAGA', title='[bold italic]DocCrawler',
                     subtitle='Note: Use CLI args for full functions', expand=True,
                     title_align='center'), style='green')

    args = parse_args()
    multi_args = load_config(args)

    if multi_args is None:
        engine.single_task(args)
    else:
        engine.console.print(_panel.Panel('Will run all the presets'), style='green')
        for single_args in multi_args:
            engine.single_task(single_args)
        engine.console.rule('[green bold italic]All tasks complete![/]', style='green')


if __name__ == '__main__':
    driver()
