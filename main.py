import argparse

from cli import Cli, AddRecipeCommand, AddResourceCommand, FindRecipes, BuildDependecyTree, ListObjects
import repository

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(metavar='DATA_DIR', help='the directory in which files are stored', default='./data', nargs='?', dest='data_dir')
    parser.add_argument('-r', '--recipes', metavar='NAME', dest='recipes_name', default='recipes.json', help='Name of the file for storing recipes.')
    parser.add_argument('-c', '--resources', metavar='NAME', dest='resources_name', default='resources.json', help='Name of the file for storing resources.')
    args = parser.parse_args()
    recipes_file = f'{args.data_dir}/{args.recipes_name}'
    resources_file = f'{args.data_dir}/{args.resources_name}'
    print('Using:')
    print(f'  recipes:   {recipes_file}')
    print(f'  resources: {resources_file}')

    repo = repository.load_repository(resources_file, recipes_file)
    commands = [AddRecipeCommand(repo), AddResourceCommand(repo), FindRecipes(repo), BuildDependecyTree(repo), ListObjects(repo)]

    cli = Cli(repo, commands)
    try:
        while cli.loop(): pass
    except Exception as e:
        print(f'Fatal error: {e}. Dumping repository.')
        raise e
    finally:
        repository.save_repository(repo, resources_file, recipes_file)
