#!/usr/bin/env python3

import os.path

import yaml
from rich import panel as _panel, prompt as _prompt

import const
import engine
from engine import get_arg_parser


def load_config(args) -> list[dict] | None:
    # Load config
    if not args['url']:
        config_dict = {}
        if os.path.exists(const.GENERAL_CONFIG_PATH):
            with open(const.GENERAL_CONFIG_PATH, 'r') as fd:
                config_dict = yaml.safe_load(fd)
        if config_dict is not None and 'websites' in config_dict and len(config_dict['websites']) != 0:
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
    return [args]


def driver():
    const.console.clear()
    const.console.print(_panel.Panel(
        'Presented by [bold italic]NintenSAGA',
        title='[bold italic]DocCrawler',
        subtitle='Note: Use CLI args for full functions', expand=True,
        title_align='center'), style='green')

    parser = get_arg_parser()
    args = vars(parser.parse_args())
    multi_args = load_config(args)
    n = len(multi_args)

    const.console.print(_panel.Panel(f'{n} task{"s" if n > 1 else ""} in total.'), style='green')
    for single_args in multi_args:
        try:
            engine.CrawlTask(single_args).run()
        except Exception as e:
            const.console.print(f'Error: {e}')
    const.console.rule('[green bold italic]All tasks complete![/]', style='green')


if __name__ == '__main__':
    driver()
