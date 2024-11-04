import json
import logging
import re
import sys
import typing
from argparse import ArgumentError
from datetime import timedelta
from typing import Self

from data import Resource, Recipe, ResourceQuantity, Entity


class DuplicateKeyError(BaseException):

    def __init__(self, msg: str):
        super().__init__(msg)

class InvalidDataError(BaseException):

    def __init__(self, msg: str, part: str):
        super().__init__(msg)
        self.part = part


class RecipeRepository:
    __RX_ID = re.compile('([a-z0-9]+([a-z0-9]|_)*)')

    __slots__=('logger', 'resources', 'recipes', 'mod_recipes', 'mod_resources')

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.resources: dict[str, Resource] = dict()
        self.recipes: dict[str, Recipe] = dict()
        self.mod_recipes = False
        self.mod_resources = False

    def add_resource(self, resource: Resource, is_load=False):
        if len(resource.name) == 0:
            raise InvalidDataError(f'resource name must not be empty', 'name')
        if len(resource.id) == 0:
            raise InvalidDataError(f'resource id must not be empty', 'id')

        if self.resources.get(resource.id, None) is None:
            if not self.validate_id_format(resource.id):
                raise InvalidDataError(f'invalid resource id: "{resource.id}"', 'id')
            self.resources[resource.id] = resource
            if not is_load:
                self.mod_resources = True
        else:
            raise DuplicateKeyError(f'duplicate resource id: {resource.id}')

    def add_recipe(self, recipe: Recipe, is_load=False):
        if len(recipe.name) == 0:
            raise InvalidDataError(f'recipe name must not be empty')
        if len(recipe.id) == 0:
            raise InvalidDataError(f'recipe id must not be empty')

        if self.recipes.get(recipe.id, None) is None:
            if not self.validate_id_format(recipe.id):
                raise InvalidDataError(f'invalid recipe id: "{recipe.id}"')
            self.recipes[recipe.id] = recipe
            if not is_load:
                self.mod_recipes = True
        else:
            raise DuplicateKeyError(f'duplicate recipe id: {recipe.id}')

    def load_resource(self, d: dict):
        resource = Resource(d['name'], d['id'], d.get('raw', False))
        self.add_resource(resource, True)

    def load_recipe(self, d: dict):
        name = d['name']
        id = d['id']
        cycle_time = d['cycle_secs']
        products = [ResourceQuantity(self.resource(res['id']), res['quantity']) for res in d['products']]
        resources = [ResourceQuantity(self.resource(res['id']), res['quantity']) for res in d['resources']]
        recipe = Recipe(
            name,
            id,
            resources,
            products,
            timedelta(seconds=cycle_time)
        )
        if 'source_name' in d:
            recipe.source_name = d['source_name']
        self.add_recipe(recipe, True)

    def delete_resource(self, resource_id: str) -> bool:
        if resource_id in self.resources:
            self.resources.pop(resource_id)
            self.mod_resources = True
            return True
        else:
            return False

    def delete_recipe(self, recipe_id: str) -> bool:
        if recipe_id in self.recipes:
            self.recipes.pop(recipe_id)
            self.mod_recipes = True
            return True
        else:
            return False

    def resource(self, res_id: str) -> typing.Optional[Resource]:
        return self.resources.get(res_id, None)

    def recipe(self, rec_id: str) -> Recipe|None:
        return self.recipes.get(rec_id, None)

    def resource_by_name(self, name: str) -> typing.Optional[Resource]:
        name_lc = name.lower()
        for resource in self.resources.values():
            if resource.name.lower() == name_lc:
                return resource
        return None

    def recipe_by_name(self, name: str) -> typing.Optional[Recipe]:
        name_lc = name.lower()
        for recipe in self.recipes.values():
            if recipe.name.lower() == name_lc:
                return recipe
        return None

    def find_recipes_by_product(self, product: Resource) -> list[Recipe]:
        results = []
        for recipe in self.recipes.values():
            if product.id in recipe.products:
                results.append(recipe)

        return results

    def update_recipe(self, recipe: Recipe):
        self.logger.debug(f'updating recipe {recipe}')
        old = self.recipe(recipe.id)
        if old is None:
            self.add_recipe(recipe, False)
        elif not old.is_equal(recipe):
            for resource in list(recipe.products.values()) + list( recipe.resources.values()):
                if resource not in self.resources:
                    raise ArgumentError(resource, 'resource does not exist in repository!')
            self.recipes[recipe.id] = recipe
            self.mod_recipes = True

    def update_entity(self, entity_id: str, entity: Entity) -> bool:
        if isinstance(entity, Resource):
            old = self.resources.get(entity_id, None)
            if old is None:
                print(f'repository: no such resource with id={entity_id}')
                return False
            if old.id != entity.id:
                if entity.id not in self.resources:
                    self.add_resource(entity, False)
                    self.resources.pop(entity_id)
                    self.mod_resources = True
                else:
                    print(f'Cannot change resource_id from {entity_id} to {entity.id}: id exists ')
                    return False
            else:
                if old.name != entity.name or old.is_raw != entity.is_raw:
                    self.resources[entity_id] = entity
                    self.mod_resources = True
        elif isinstance(entity, Recipe):
            old = self.recipes.get(entity_id, None)
            if old is None:
                print(f'repository: no such recipe with id={entity_id}')
                return False
            if old.id != entity.id:
                if entity.id not in self.recipes:
                    self.add_recipe(entity, False)
                    self.recipes.pop(entity_id)
                    self.mod_recipes = True
                else:
                    print(f'Cannot change recipe_id from {entity_id} to {entity.id}: id exists')
                    return False
            else:
                try:
                    self.update_recipe(entity)
                except ArgumentError as e:
                    print(f'Could not update recipe {entity}: {e}')
                    return False
        return True

    @staticmethod
    def validate_id_format(id_str: str) -> bool:
        return RecipeRepository.__RX_ID.fullmatch(id_str) is not None



def load_repository(resources_path: str, recipes_path: str):
    repo = RecipeRepository()
    j_res_arr = []
    j_rec_arr = []
    with open(resources_path, 'r') as res_file:
        j_res_arr = json.load(res_file)

    for res_dict in j_res_arr:
        repo.load_resource(res_dict)

    with open(recipes_path, 'r') as rec_file:
        j_rec_arr = json.load(rec_file)

    for rec_dict in j_rec_arr:
        repo.load_recipe(rec_dict)

    return repo

def save_repository(repo: RecipeRepository, resources_path: typing.Optional[str], recipes_path: typing.Optional[str], force=False):
    if repo.mod_recipes or force:
        if recipes_path is not None:
            j_rec_arr = []
            vals_sorted = sorted(repo.recipes.values(), key=Recipe.get_id)
            for recipe in vals_sorted:
                j_rec_arr.append(recipe.as_dict())

            if recipes_path != '-':
                with open(recipes_path, 'wt') as recipes_file:
                    json.dump(j_rec_arr, recipes_file)
            else:
                json.dump(j_rec_arr, sys.stdout)
            del vals_sorted
    else:
        print(f'Recipes not modified, skipping saving.')

    if repo.mod_resources or force:
        if resources_path is not None:
            j_res_arr = []
            vals_sorted = sorted(repo.resources.values(), key=Resource.get_id)
            for resource in vals_sorted:
                j_res_arr.append(resource.as_dict())

            if resources_path != '-':
                with open(resources_path, 'wt') as res_file:
                    json.dump(j_res_arr, res_file)
            else:
                json.dump(j_res_arr, sys.stdout)
            del vals_sorted
    else:
        print(f'Resources not modified, skipping saving.')


class RecipeBuilder:

    def __init__(self, repo: RecipeRepository):
        self._repo = repo
        self._resources = []
        self._products = []
        self._cycle_time = timedelta(seconds=1)
        self._name = ''
        self._id = ''

    def name(self, name: str) -> Self:
        self._name = name
        return self

    def id(self, id: str) -> Self:
        self._id = id
        return self

    def resource(self, resource: str|Resource, quantity: float) -> Self:
        resource = self._repo.resource(resource) if resource is str else resource
        if resource is None:
            raise ArgumentError(None, f'resource {resource} not found!')

        self._resources.append(ResourceQuantity(resource, quantity))
        return self

    def product(self, resource: str|Resource, quantity: float) -> Self:
        resource = self._repo.resource(resource) if resource is str else resource
        if resource is None:
            raise ArgumentError(None, f'resource {resource} not found!')

        self._products.append(ResourceQuantity(resource, quantity))
        return self

    def cycle_time(self, time: timedelta) -> Self:
        self._cycle_time = time
        return self

    def build(self) -> Recipe:
        return Recipe(self._name, self._id, self._resources, self._products, self._cycle_time)
