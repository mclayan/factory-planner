import json
from argparse import ArgumentError
from datetime import timedelta
from typing import Self

from data import Resource, Recipe, ResourceQuantity


class DuplicateKeyError(Exception):

    def __init__(self, msg: str):
        super().__init__(msg)


class RecipeRepository:

    def __init__(self):
        self.resources: dict[str, Resource] = dict()
        self.recipes: dict[str, Recipe] = dict()
        self.mod_recipes = False
        self.mod_resources = False

    def add_resource(self, resource: Resource):
        if self.resources.get(resource.id, None) is None:
            self.resources[resource.id] = resource
            self.mod_resources = True
        else:
            raise DuplicateKeyError(f'duplicate resource id: {resource.id}')

    def add_recipe(self, recipe: Recipe):
        if self.recipes.get(recipe.id, None) is None:
            self.recipes[recipe.id] = recipe
            self.mod_recipes = True
        else:
            raise DuplicateKeyError(f'duplicate recipe id: {recipe.id}')

    def load_resource(self, d: dict):
        resource = Resource(d['name'], d['id'])
        self.add_resource(resource)

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
        self.add_recipe(recipe)

    def resource(self, res_id: str) -> Resource|None:
        return self.resources.get(res_id, None)

    def recipe(self, rec_id: str) -> Recipe|None:
        return self.recipes.get(rec_id, None)

    def resource_by_name(self, name: str) -> Resource|None:
        for resource in self.resources.values():
            if resource.name == name:
                return resource
        return None

    def recipe_by_name(self, name: str) -> Recipe|None:
        for recipe in self.recipes.values():
            if recipe.name == name:
                return recipe
        return None

    def find_recipes_by_product(self, product: Resource) -> list[Recipe]:
        results = []
        for recipe in self.recipes.values():
            if recipe.products.get(product.id) is not None:
                results.append(recipe)

        return results



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

def save_repository(repo: RecipeRepository, resources_path: str, recipes_path: str):
    if repo.mod_recipes:
        j_rec_arr = []
        for recipe in repo.recipes.values():
            j_rec_arr.append(recipe.as_dict())

        with open(recipes_path, 'wt') as recipes_file:
            json.dump(j_rec_arr, recipes_file)

    if repo.mod_resources:
        j_res_arr = []
        for resource in repo.resources.values():
            j_res_arr.append(resource.as_dict())

        with open(resources_path, 'wt') as res_file:
            json.dump(j_res_arr, res_file)


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
            raise ArgumentError(f'resource {resource} not found!')

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
