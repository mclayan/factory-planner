from abc import ABC, abstractmethod
from typing import Iterator

from data import Resource, Production, ResourceQuantity, Recipe
from repository import RecipeRepository

class BaseNode(ABC):
    pass

class BaseNode(ABC):

    __slots__ = ('parent', 'children')

    def __init__(self, parent: BaseNode|None):
        self.parent = parent

    @abstractmethod
    def __iter__(self) -> Iterator:
        pass


class EndNode(BaseNode):

    def __init__(self, resource: ResourceQuantity, parent: BaseNode, end_type: str='unknown'):
        super().__init__(parent)
        self.resource = resource
        if end_type.lower() == 'source':
            self.end_type = 'source'
        else:
            self.end_type = 'unknown'

    def is_source(self) -> bool:
        return self.end_type == 'source'

    def __iter__(self) -> Iterator:
        return list().__iter__()


class ProdNode:
    pass


class AltNode(BaseNode):

    def __init__(self, product: Resource):
        self.product = product
        self.slots = []
        self.active_slot = 0

    def add(self, node: ProdNode):
        self.slots.append(node)


    def sort(self, order: str = 'stations'):
        if order == 'stations':
            self.slots.sort(key=Production.get_base_rpm, reverse=True)
        elif order == 'energy':
            pass

    def active(self) -> ProdNode|None:
        if len(self.slots) > self.active_slot:
            return self.slots[self.active_slot]
        elif len(self.slots) > 0:
            return self.slots[0]
        else:
            return None

    def __iter__(self):
        active = self.active()
        if active is None:
            raise Exception('invalid active slot!')
        else:
            return active.__iter__()


class ProdNode(BaseNode):

    def __init__(self, recipe: Recipe, production: Production, rpm: float, parent: ProdNode|None):
        super().__init__(parent)
        self.production = production
        self.recipe = recipe
        self.rpm = rpm
        self.children = []

    def resolve_children(self, repository: RecipeRepository, level: int, max_level: int):
        for dependency in self.production.for_rpm(self.rpm).resources:
            if not dependency.resource.is_raw:
                alternatives = AltNode(dependency.resource)
                recipes = repository.find_recipes_by_product(dependency.resource)
                if len(recipes) == 0:
                    self.children.append(EndNode(dependency, self))
                    continue

                for recipe in recipes:
                    production = recipe.production(dependency.resource)
                    child_node = ProdNode(recipe, production, dependency.quantity, self)

                    if level < max_level:
                        child_node.resolve_children(repository, level + 1, max_level)

                    alternatives.add(child_node)

                alternatives.sort()
                self.children.append(alternatives)
            else:
                self.children.append(EndNode(dependency, self, end_type='source'))

    def __iter__(self):
        return self.children.__iter__()


class ProductionTree:

    def __init__(self, root_recipe: Recipe, target_product: Resource, target_rpm: float):
        self.root = ProdNode(root_recipe, root_recipe.production(target_product), target_rpm, None)

    def build(self, repository: RecipeRepository, max_depth:int=15):
        self.root.resolve_children(repository, 0, max_depth)


