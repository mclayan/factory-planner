import shlex
from argparse import ArgumentParser, ArgumentError
from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import timedelta
from itertools import product
from typing import Any

from chaining import ProductionTree
from data import Resource, ResourceQuantity, Recipe
from repository import RecipeRepository, DuplicateKeyError, RecipeBuilder


class ObjectStub:
    pass


def generate_id(name: str) -> str:
    return name.lower().replace(' ', '_')


class ObjectStub:

    def __init__(self, name: str | None, id: str | None):
        self.name = name
        self.id = id

    @staticmethod
    def parse(s: str) -> ObjectStub | None:
        if s.startswith('@'):
            if len(s) <= 1:
                print(f'Error: invalid resource_id: "@". Should be "@<id>"')
                return None
            else:
                return ObjectStub(name=None, id=s[1:])
        else:
            return ObjectStub(name=s, id=None)

    def __str__(self):
        return f'ObjectStub[id={self.id} name={self.name}]'

def noopt() -> Any:
    pass

class CliCommand(ABC):

    def __init__(self, parser: ArgumentParser):
        self.parser = parser
        self.parser.exit_on_error = False
        self.parser.exit = noopt

    @abstractmethod
    def command_name(self) -> str:
        pass

    def parse_arguments(self, arg_str: str):
        return self.parser.parse_args(shlex.split(arg_str))

    @abstractmethod
    def execute(self, command_str: str):
        pass


class AddResourceCommand(CliCommand):
    cmd_name = 'add-resource'

    def command_name(self) -> str:
        return AddResourceCommand.cmd_name

    def __init__(self, repo: RecipeRepository):
        parser = ArgumentParser(prog=AddResourceCommand.cmd_name)
        parser.add_argument('-i', '--id', metavar='NAME', dest='resource_id', help='Set resource id.', default='')
        parser.add_argument('-r', '--raw', action='store_true', dest='is_raw', help='Make resource a raw base resource.')
        parser.add_argument('name', metavar='NAME', help='Name of the resource', default='')

        super().__init__(parser)
        self.repository = repo

    def execute(self, command_str: str):
        args = self.parse_arguments(command_str)
        resource_name: str = args.name
        resource_id: str = args.resource_id
        if len(resource_id) == 0:
            resource_id = generate_id(resource_name)
        resource = Resource(resource_name, resource_id)
        try:
            self.repository.add_resource(resource)
            print(f'{resource_id}: {resource}')
        except DuplicateKeyError as e:
            print(f'Failed to add resource: {e}')


class AddRecipeCommand(CliCommand):
    cmd_name = 'add-recipe'

    def __init__(self, repo: RecipeRepository):
        parser = ArgumentParser(prog=AddRecipeCommand.cmd_name)
        parser.add_argument('-i', '--id', metavar='NAME', dest='recipe_id', help='Set recipe id.')
        parser.add_argument('-t', '--time', metavar='DURATION', dest='cycle_time',
                            help='Time in seconds one cycle takes.', type=str, required=True)
        parser.add_argument('-p', '--product', help='Resource produced by executing the recipe.', nargs='+',
                            action='extend', dest='products')
        parser.add_argument('-r', '--resource', help='Resource produced by executing the recipe.', nargs='+',
                            action='extend', dest='resources')
        parser.add_argument('name', metavar='NAME', help='Name of the recipe.')
        super().__init__(parser)

        self.repository = repo

    def command_name(self) -> str:
        return AddRecipeCommand.cmd_name

    @staticmethod
    def parse_resources(res_list: list[str]) -> list[tuple[ObjectStub, float]]:
        results = []
        it_res: Iterator[str] = res_list.__iter__()
        while True:
            try:
                res = it_res.__next__()
            except StopIteration:
                break
            try:
                count = it_res.__next__()
            except StopIteration:
                print(
                    f'Error: invalid value for "{res}": each resource/product argument must be specified as "<name> <quantity>"')
                return []

            resource = ObjectStub.parse(res)
            quantity = float(count)
            results.append((resource, quantity))

        return results

    def execute(self, command_str: str):
        args = self.parse_arguments(command_str)
        recipe_name = args.name
        recipe_id = args.recipe_id
        if recipe_id is None or len(recipe_id.strip()) == 0:
            recipe_id = generate_id(recipe_name)

        if self.repository.recipe(recipe_id) is not None:
            print(f'Error: a recipe with the id {recipe_id} already exists!')
            return

        time_parts: list[str] = args.cycle_time.split(':')
        time_parts.reverse()
        (cycle_secs, cycle_mins, cycle_hours) = (0, 0, 0)
        i = 0
        for part in time_parts:
            if i == 0:
                cycle_secs = float(part)
            elif i == 1:
                cycle_mins = float(part)
            elif i == 2:
                cycle_hours = float(part)
            else:
                break
            i += 1

        product_stubs = self.parse_resources(args.products)
        if len(args.products) > 0 and len(product_stubs) == 0:
            return
        resource_stubs = self.parse_resources(args.resources)
        if len(args.resources) > 0 and len(resource_stubs) == 0:
            return

        builder = RecipeBuilder(self.repository) \
            .cycle_time(timedelta(hours=cycle_hours, minutes=cycle_mins, seconds=cycle_secs))\
            .name(recipe_name) \
            .id(recipe_id)

        for prod_spec, qt in product_stubs:
            product = self.repository.resource_by_name(
                prod_spec.name) if prod_spec.name is not None else self.repository.resource(prod_spec.id)
            try:
                builder.product(product, qt)
            except ArgumentError as e:
                print(f'Error: {e.message}')
                return

        for res_spec, qt in resource_stubs:
            resource = self.repository.resource_by_name(
                res_spec.name) if res_spec.name is not None else self.repository.resource(res_spec.id)
            try:
                builder.resource(resource, qt)
            except ArgumentError as e:
                print(f'Error: {e.message}')
                return

        recipe = builder.build()
        try:
            self.repository.add_recipe(recipe)
            print(recipe)
        except DuplicateKeyError as e:
            print(f'Failed to add recipe "{recipe_name}": {e}')


class FindRecipes(CliCommand):
    cmd_name = 'find-recipe'

    def command_name(self) -> str:
        return FindRecipes.cmd_name

    def execute(self, command_str: str):
        args = self.parse_arguments(command_str)

        recipes = []
        product = None
        if args.product is not None:
            product_spec = ObjectStub.parse(args.product)
            if product_spec is None:
                return
            product = self.repository.resource_by_name(product_spec.name) if product_spec.name is not None \
                else self.repository.resource(product_spec.id)
            recipes = self.repository.find_recipes_by_product(product)
        elif args.recipe_name is not None:
            recipe = self.repository.recipe_by_name(args.recipe_name)
            if recipe is not None:
                recipes.append(recipe)
        elif args.recipe_id is not None:
            recipe = self.repository.recipe(args.recipe_id)
            if recipe is not None:
                recipes.append(recipe)

        for recipe in recipes:
            print(recipe)
            if product is not None:
                production = recipe.production(product)
                print(f'└──⏵ {production}')

    def __init__(self, repo: RecipeRepository):
        parser = ArgumentParser(prog=FindRecipes.cmd_name)
        parser.add_argument('-p', '--product', metavar="NAME | @<ID>", dest='product',
                            help='Find recipes by producing product')
        parser.add_argument('-n', '--name', metavar="NAME", dest='recipe_name', help='Find recipes by name')
        parser.add_argument('-i', '--id', metavar="RECIPE_ID", dest='recipe_id', help='Find recipes by id')
        super().__init__(parser)

        self.repository = repo


class BuildDependecyTree(CliCommand):
    cmd_name = 'tree'

    def __init__(self, repo: RecipeRepository):
        parser = ArgumentParser()
        parser.add_argument('recipe_sel', metavar='RECIPE')
        parser.add_argument('-l', '--limit', type=int, dest='limit', default=None, help='Maximum tree depth (recursion)')
        parser.add_argument('-p', '--product', type=str, dest='product', default=None, help='Product to select from recipe. Optional if recipe produces only one product.')
        parser.add_argument('-r', '--rpm', type=float, default=None, help='Target RPM of the selected product. If not set, the default RPM for the product in the recipe will be used.')

        super().__init__(parser)

        self.repository = repo


    def command_name(self) -> str:
        return self.cmd_name

    def execute(self, command_str: str):
        args = self.parse_arguments(command_str)
        recipe_sel = ObjectStub.parse(args.recipe_sel)
        if recipe_sel is None:
            print(f'invalid recipe selection: {args.recipe_sel}')
            return

        recipe = None
        if recipe_sel.name is not None:
            recipe = self.repository.recipe_by_name(recipe_sel.name)
        else:
            recipe = self.repository.recipe(recipe_sel.id)

        if recipe is None:
            print(f'Cannot find recipe "{recipe_sel}"')
            return


        if len(recipe.products) > 1:
            product_sel = ObjectStub.parse(args.product)
            if product_sel is None:
                print(f'Invalid product selection: {args.product}')
                return
            else:
                if product_sel.name is not None:
                    product = self.repository.resource_by_name(product_sel.name)
                else:
                    product = self.repository.resource(product_sel.id)
        else:
            product = recipe.nth_product(0)

        if product is None:
            print(f'Failed to select product')
            return

        if args.rpm is not None:
            rpm = args.rpm
        else:
            rpm = recipe.production(product).get_base_rpm()

        tree = ProductionTree(recipe, product, rpm)
        if args.limit is None:
            tree.build(self.repository)
        else:
            tree.build(self.repository, args.limit)

        print('Dependency tree:')
        tree.print_tree()
        print('\nAggregated resources:')
        aggregate = tree.get_aggregate()
        for rtpl in aggregate.calculate_productions():
            print(f'{rtpl[0]} ({rtpl[2]:.1f}) => {rtpl[1]}')


class ListObjects(CliCommand):
    cmd_name = 'ls'

    def __init__(self, repo: RecipeRepository):
        parser = ArgumentParser()
        parser.add_argument('-p', '--product', type=str, default=None, help='Display specific resource/product.')
        parser.add_argument('-r', '--recipe', type=str, default=None, help='Display specific recipe.')
        parser.add_argument('type_name', metavar='TYPE', nargs='?', default=None, choices=['r', 'recipes', 'R', 'resources'])
        super().__init__(parser)
        self.repository = repo

    def command_name(self) -> str:
        return ListObjects.cmd_name

    def execute(self, command_str: str):
        args = self.parse_arguments(command_str)
        result = None
        if args.product is not None:
            if args.recipe is not None or args.type_name is not None:
                print(f'Invalid input: exactly one of "-r", "-p" or TYPE must be set at the same time.')
                return
            else:
                res_spec = ObjectStub.parse(args.product)
                if res_spec.name is None and res_spec.id is None:
                    print(f'invalid product selection: {args.product}')
                    return
                if res_spec.name is not None:
                    result = self.repository.resource_by_name(res_spec.name)
                else:
                    result = self.repository.resource(res_spec.id)
                print(result)
        elif args.recipe is not None:
            if args.product is not None or args.type_name is not None:
                print(f'Invalid input: exactly one of "-r", "-p" or TYPE must be set at the same time.')
                return
            else:
                recipe_spec = ObjectStub.parse(args.recipe)
                if recipe_spec.name is None and recipe_spec.id is None:
                    print(f'invalid recipe selection: {args.recipe}')
                    return
                if recipe_spec.name is not None:
                    result = self.repository.recipe_by_name(recipe_spec.name)
                else:
                    result = self.repository.recipe(recipe_spec.id)
                print(result)
        else:
            if args.type_name is None:
                print(f'Invalid input: exactly one of "-r", "-p" or TYPE must be set at the same time.')
                return
            if args.type_name in ['recipes', 'r']:
                for (r_id, recipe) in self.repository.recipes.items():
                    print(f'{r_id} -> "{recipe.name}"')
            else:
                for (r_id, resource) in self.repository.resources.items():
                    print(f'{r_id} -> "{resource.name}"')



class Cli:

    def __init__(self, repo: RecipeRepository, commands: list[CliCommand]):
        self.repo = repo
        self.commands = commands

    def list_recipes(self, product_id: str):
        product = self.repo.resource_by_name(product_id)
        if product is not None:
            pass
        else:
            print(f'no product with id="{product_id}" found')

    def get_command(self, name: str) -> CliCommand | None:
        for cmd in self.commands:
            if cmd.command_name() == name:
                return cmd
        return None

    def loop(self) -> bool:
        user_input = input("=> ").strip().split(' ', 1)
        if len(user_input) > 0:
            cmd_name = user_input[0]
            if cmd_name == 'exit' or user_input == 'quit':
                return False
            if cmd_name == 'help':
                if len(user_input) > 1:
                    command = self.get_command(user_input[1])
                    if command is not None:
                        command.parser.print_help()
                    else:
                        print(f'help: unknown command "{cmd_name}"')
                else:
                    for cmd in self.commands:
                        print(cmd.command_name())
            else:
                command = self.get_command(cmd_name)
                if command is None:
                    print(f'Error: unknown command "{cmd_name}"')
                else:
                    try:
                        command.execute(user_input[1] if len(user_input) > 1 else '')
                    except ArgumentError as e:
                        print(f'Error: {e}')
        return True
