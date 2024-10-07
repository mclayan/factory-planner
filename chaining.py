import typing
from abc import ABC, abstractmethod
from argparse import ArgumentError
from typing import Iterator

from data import Resource, Production, ResourceQuantity, Recipe
from repository import RecipeRepository


class ResQtRecipe:

    def __init__(self, resource: Resource, qt: float, prod_source: Recipe):
        self.quantity = qt
        self.recipe = prod_source
        self.resource = resource


class ResourceAggregate:

    def __init__(self):
        self.recipes: dict[str, ResQtRecipe] = dict()
        self.raw: dict[str, ResourceQuantity] = dict()

    def add(self, res_qt: ResourceQuantity, recipe: typing.Optional[Recipe]):
        if recipe is None:
            existing = self.raw.get(res_qt.resource.id, None)
            if existing is not None:
                existing.quantity += res_qt.quantity
            else:
                self.raw[res_qt.resource.id] = res_qt
        else:
            existing = self.recipes.get(recipe.id, None)
            if existing is not None:
                existing.quantity += res_qt.quantity
            else:
                self.recipes[recipe.id] = ResQtRecipe(res_qt.resource, res_qt.quantity, recipe)

    def __iter__(self):
        return self.recipes.values().__iter__()

    def calculate_productions(self) -> list[tuple[str, Production, float]]:
        results = []
        for rqr in self.recipes.values():
            production = rqr.recipe.production(rqr.resource)
            rec_fact = rqr.quantity / production.base_rpm
            results.append((f'Recipe: {rqr.recipe.name}', production, rec_fact))
        for rr in self.raw.values():
            results.append((f'Resource: {rr.resource.name}', Production(rr.resource, [], [], 1.0), rr.quantity))
        return results


class BaseNode(ABC): ...


class BaseNode(ABC):
    __slots__ = ('parent', 'children')

    def __init__(self, parent: BaseNode | None):
        self.parent = parent

    @abstractmethod
    def __iter__(self) -> Iterator:
        pass

    @abstractmethod
    def print_node(self): ...

    @abstractmethod
    def print_children(self, level: int, pfx: str): ...

    @abstractmethod
    def aggregate_resources(self, aggregate: ResourceAggregate): ...


class EndNode(BaseNode):

    def __init__(self, resource: ResourceQuantity, parent: BaseNode, end_type: str = 'unknown'):
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

    def print_node(self):
        print(f'{self.resource.resource.name}: {self.resource.quantity:.1f}')

    def print_children(self, level: int, pfx: str):
        return

    def aggregate_resources(self, aggregate: ResourceAggregate):
        aggregate.add(self.resource, None)


class AltNode(BaseNode):

    def __init__(self, product: Resource):
        self.product = product
        self.slots = []
        self.active_slot = 0

    def add(self, node: 'ProdNode'):
        self.slots.append(node)

    def sort(self, order: str = 'stations'):
        if order == 'stations':
            self.slots.sort(key=lambda node: node.production.get_base_rpm(), reverse=True)
        elif order == 'energy':
            pass

    @property
    def active(self) -> typing.Optional['ProdNode']:
        if len(self.slots) > self.active_slot:
            return self.slots[self.active_slot]
        elif len(self.slots) > 0:
            return self.slots[0]
        else:
            return None

    def __iter__(self):
        active = self.active
        if active is None:
            raise Exception('invalid active slot!')
        else:
            return active.__iter__()

    def print_node(self):
        if len(self.slots) > 0:
            node = self.active
            production = node.production.str_for_rpm(node.rpm)
        else:
            production = '<n/a>'
        print(f'[{self.active_slot}] {production}')

    def print_children(self, level: int, pfx: str):
        if len(self.slots) > 0:
            node = self.active
            if node is not None:
                node.print_children(level + 1, pfx)

    def aggregate_resources(self, aggregate: ResourceAggregate):
        active = self.active
        if active is not None:
            active.aggregate_resources(aggregate)


class ProdNode(BaseNode):

    def __init__(self, recipe: Recipe, production: Production, rpm: float, parent: typing.Optional['ProdNode']):
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

    def __str__(self):
        return f'Product="{self.production.product.name}" rpm={self.rpm}'

    def print_node(self):
        print(f'{self.production.str_for_rpm(self.rpm)}')

    def print_children(self, level: int, pfx: str):
        # ├ └ ─

        i = 1
        for child_node in self.children:
            last_child = i < len(self.children)
            w_str = '{}── '.format('├' if last_child else '└',
                                             width=level * 2)
            c_pfx = '{pfx}{}   '.format(
                '│' if last_child else ' ',
                pfx=pfx
            )
            print(pfx, end='')
            print(w_str, end='')
            child_node.print_node()
            child_node.print_children(level + 1, c_pfx)
            i += 1

    def aggregate_resources(self, aggregate: ResourceAggregate):
        aggregate.add(ResourceQuantity(self.production.product, self.rpm), self.recipe)

        for child_node in self.children:
            child_node.aggregate_resources(aggregate)


class ProductionTree:

    def __init__(self, root_recipe: Recipe, target_product: Resource, target_rpm: float):
        self.root = ProdNode(root_recipe, root_recipe.production(target_product), target_rpm, None)

    def build(self, repository: RecipeRepository, max_depth: int = 15):
        self.root.resolve_children(repository, 0, max_depth)

    def print_tree(self):
        self.root.print_node()
        self.root.print_children(0, '')

    def get_aggregate(self) -> ResourceAggregate:
        aggregate = ResourceAggregate()
        self.root.aggregate_resources(aggregate)

        return aggregate
