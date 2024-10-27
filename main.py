import argparse

import planner_ui
import planner_ui.application
import repository
from cli import Cli
from config import MainConfig


def _cli(config: MainConfig):
    cli = Cli(config)
    while cli.loop(): pass


def _main():
    parser = argparse.ArgumentParser()
    parser.add_argument(metavar='DATA_DIR', help='the directory in which files are stored', default='./data', nargs='?',
                        dest='data_dir')
    parser.add_argument('-r', '--recipes', metavar='NAME', dest='recipes_name', default='recipes.json',
                        help='Name of the file for storing recipes.')
    parser.add_argument('-c', '--resources', metavar='NAME', dest='resources_name', default='resources.json',
                        help='Name of the file for storing resources.')
    parser.add_argument('--gui', dest='op_mode', help='Use the graphical user interface.', action='store_const',
                        const='gui')
    parser.add_argument('--cli', dest='op_mode', help='Use the command line interface.', action='store_const',
                        const='cli')
    parser.add_argument('-R', '--read-only', dest='is_readonly', help='Do not save changes when exiting', action='store_true')
    parser.add_argument('--theme', dest='gui_theme', help='GUI theme to use. Defaults to \'classic\'.', default='classic')
    parser.add_argument('--productivity', dest='productivity_look', help='Improve the GUI look towards a traditional productivity design.', action='store_true')
    args = parser.parse_args()

    recipes_file = f'{args.data_dir}/{args.recipes_name}'
    resources_file = f'{args.data_dir}/{args.resources_name}'
    print('Using:')
    print(f'  recipes:   {recipes_file}')
    print(f'  resources: {resources_file}')

    repo = repository.load_repository(resources_file, recipes_file)
    config = MainConfig(resources_file, recipes_file, repo, args.gui_theme)
    if args.productivity_look:
        config.productivity_look = True

    op_mode = args.op_mode
    try:
        if op_mode == 'cli' or op_mode is None:
            _cli(config)
        elif op_mode == 'gui':
            planner_ui.application.main(config)
    except Exception as e:
        print(f'Fatal error: {e}. Dumping repository.')
        raise e
    finally:
        if not args.is_readonly:
            repository.save_repository(repo, config.resources_file, config.recipes_file)


if __name__ == '__main__':
    _main()
