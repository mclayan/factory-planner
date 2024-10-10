import argparse

import planner_ui
import planner_ui.application
from cli import Cli, AddRecipeCommand, AddResourceCommand, FindRecipes, BuildDependecyTree, ListObjects, \
    AddRawResourceRecipe
import repository
from repository import RecipeRepository


class MainConfig:

    def __init__(self, resources_file, recipes_file, repo):
        self.resources_file = resources_file
        self.recipes_file = recipes_file
        self.repository = repo


def _cli(config: MainConfig):
    repo = config.repository
    commands = [AddRecipeCommand(repo), AddResourceCommand(repo), FindRecipes(repo), BuildDependecyTree(repo),
                ListObjects(repo), AddRawResourceRecipe(repo)]

    cli = Cli(repo, commands)
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
    args = parser.parse_args()

    recipes_file = f'{args.data_dir}/{args.recipes_name}'
    resources_file = f'{args.data_dir}/{args.resources_name}'
    print('Using:')
    print(f'  recipes:   {recipes_file}')
    print(f'  resources: {resources_file}')

    repo = repository.load_repository(resources_file, recipes_file)
    config = MainConfig(resources_file, recipes_file, repo)

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
        repository.save_repository(repo, config.resources_file, config.recipes_file)


if __name__ == '__main__':
    _main()
