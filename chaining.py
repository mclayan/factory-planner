import typing
from abc import ABC, abstractmethod
from typing import Iterator, Optional

import data
import persistence


class TreeConfig:

    def __init__(self):
        self.blacklist: set[data.Recipe] = set()
        self.recipe_preferences = RecipePreferences()


class RecipePreferences:

    def __init__(self):
        self._prefs: dict[data.Resource, data.Recipe] = dict()

    def __getitem__(self, item: data.Resource | str) -> Optional[data.Recipe]:
        if isinstance(item, data.Resource):
            return self._prefs.get(item, None)
        elif isinstance(item, str):
            for k, v in self._prefs.items():
                if k.get_id() == item:
                    return v
        else:
            raise TypeError(f'Expected either {data.Resource} or str, got: {type(item)}')
        return None

    def __contains__(self, item):
        if isinstance(item, data.Resource):
            return self._prefs.__contains__(item)
        elif isinstance(item, str):
            for key in self._prefs.keys():
                if key == item:
                    return True
        return False

    def __repr__(self) -> str:
        return list(map(lambda kv: f'{kv[0].get_name()}={kv[1].get_name()}', self._prefs.items())).__repr__()

    def add_preference(self, resource: data.Resource, recipe: data.Recipe):
        self._prefs[resource] = recipe


class ResQtRecipe:

    def __init__(self, resource: data.Resource, qt: float, prod_source: data.Recipe):
        self.quantity = qt
        self.recipe = prod_source
        self.resource = resource


class ResourceAggregate:

    def __init__(self):
        self.recipes: dict[str, ResQtRecipe] = dict()
        self.raw: dict[str, data.ResourceQuantity] = dict()

    def add(self, res_qt: data.ResourceQuantity, recipe: typing.Optional[data.Recipe]):
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

    def calculate_productions(self) -> list[tuple[str, data.TargetedProduction, float]]:
        results = []
        for rqr in self.recipes.values():
            production = rqr.recipe.production(rqr.resource)
            rec_fact = rqr.quantity / production.base_rpm
            results.append((f'Recipe: {rqr.recipe.name}', production, rec_fact))
        for rr in self.raw.values():
            results.append(
                (f'Resource: {rr.resource.name}', data.TargetedProduction(rr.resource, [], [], 1.0), rr.quantity))
        return results


class BaseNode(ABC):
    __slots__ = ('parent', 'children', 'tree')

    def __init__(self, parent: typing.Optional['BaseNode'], tree: 'ProductionTree'):
        self.parent = parent
        self.tree = tree

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

    def __init__(self, resource: data.ResourceQuantity, parent: typing.Optional[BaseNode], tree: 'ProductionTree',
                 end_type: str = 'unknown'):
        super().__init__(parent, tree)
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

    def __init__(self, product: data.Resource, parent: typing.Optional['BaseNode'], tree: 'ProductionTree'):
        super().__init__(parent, tree)
        self.product = product
        self.slots: list[ProdNode] = []
        self.active_slot = 0

    def add(self, node: 'ProdNode'):
        node.parent = self
        self.slots.append(node)

    def sort(self, config: TreeConfig):
        self.slots.sort(key=lambda node: node.production.get_base_rpm(), reverse=True)
        if self.product in config.recipe_preferences:
            preferred_recipe = config.recipe_preferences[self.product]
            i = 0
            for prod_node in self.slots:
                if prod_node.recipe.id == preferred_recipe.id:
                    self.active_slot = i
                    break
                i += 1

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
            production = node.production.str_for_rpm(node.rpm, node.recipe.name)
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

    def get_alternatives(self) -> set[data.ProductionAssoc]:
        alts = set()
        slot_alts = list()
        for slot in self.slots:
            alts.add(slot.recipe)
            slot_alts.extend(slot.get_alternatives())
        if len(alts) > 1:
            slot_alts.extend([data.ProductionAssoc(self.product, a) for a in alts])

        return set(slot_alts)


class ProdNode(BaseNode):

    def __init__(self, recipe: data.Recipe, production: data.TargetedProduction, rpm: float,
                 parent: typing.Optional['ProdNode'],
                 tree: 'ProductionTree'):
        super().__init__(parent, tree)
        self.production = production
        self.recipe = recipe
        self.rpm = rpm
        self.children: list[AltNode | EndNode] = []

    def resolve_children(self,
                         repository: persistence.RecipeRepository,
                         level: int,
                         max_level: int,
                         parent_recipes: set[str],
                         config: TreeConfig):
        for dependency in self.production.for_rpm(self.rpm).resources:
            alternatives = AltNode(dependency.resource, self, self.tree)
            recipes = set(filter(lambda r: r.id not in parent_recipes,
                                 repository.find_recipes_by_product(dependency.resource, config.blacklist)))

            if len(recipes) == 0:
                self.children.append(EndNode(dependency, self, self.tree))
                continue

            for recipe in recipes:
                production = recipe.production(dependency.resource)
                child_node = ProdNode(recipe, production, dependency.quantity, None, self.tree)

                if level < max_level:
                    parents = parent_recipes.copy()
                    parents.add(self.recipe.id)
                    child_node.resolve_children(repository, level + 1, max_level, parents, config)

                alternatives.add(child_node)

            alternatives.sort(config)
            self.children.append(alternatives)

    def __iter__(self):
        return self.children.__iter__()

    def __str__(self):
        return f'Product="{self.production.product.name}" rpm={self.rpm}'

    def print_node(self):
        print(f'{self.production.str_for_rpm(self.rpm, self.recipe.name)}')

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
        aggregate.add(data.ResourceQuantity(self.production.product, self.rpm), self.recipe)

        for child_node in self.children:
            child_node.aggregate_resources(aggregate)

    def get_alternatives(self) -> set[data.ProductionAssoc]:
        alts = list()
        for child_node in self.children:
            if isinstance(child_node, AltNode):
                alts.extend(child_node.get_alternatives())
        return set(alts)


class ProductionTree:

    def __init__(self, root_recipe: data.Recipe, target_product: data.Resource, target_rpm: float):
        self.root = ProdNode(root_recipe, root_recipe.production(target_product), target_rpm, None, self)
        self.config = TreeConfig()

    def build(self, repository: persistence.RecipeRepository, max_depth: int = 15):
        self.root.resolve_children(repository, 0, max_depth, set(), self.config)

    def print_tree(self):
        self.root.print_node()
        self.root.print_children(0, '')

    def get_aggregate(self) -> ResourceAggregate:
        aggregate = ResourceAggregate()
        self.root.aggregate_resources(aggregate)

        return aggregate

    def find_alternatives(self) -> set[data.ProductionAssoc]:
        return self.root.get_alternatives()


# ----------------------------------------------------------------------------------------------------------------------#
#   Graph                                                                                                              #
# ----------------------------------------------------------------------------------------------------------------------#

class GraphNode:
    __slots__ = ('consumers', 'producers', 'recipe', 'is_root', 'level')

    def __init__(self, recipe: data.ScaledRecipe, dependency_level: int):
        self.consumers: dict[str, 'GraphNode'] = dict()
        self.producers: dict[str, 'GraphNode'] = dict()
        self.recipe = recipe
        self.level = dependency_level

    def register_consumer(self, consumer: 'GraphNode'):
        recipe_id = consumer.recipe.recipe_id()
        if recipe_id not in self.consumers:
            self.consumers[recipe_id] = consumer
        consumer.register_producer(self)

    def register_producer(self, producer: 'GraphNode'):
        recipe_id = producer.recipe_id()
        if recipe_id not in self.producers:
            self.producers[recipe_id] = producer

    def resource_demand(self) -> data.ResourceQuantities:
        demands = data.ResourceQuantities([])
        products = self.recipe.scaled_components().products
        for consumer in self.consumers.values():
            consumer_resources = consumer.recipe.scaled_components().resources
            for demand_id, demand_qt in consumer_resources.pairs():
                if demand_id in products:
                    demands.add(demand_qt)

        return demands

    def update_scale(self, int_scale=False):
        demands = self.resource_demand()
        if len(demands) > 0:
            self.recipe.scale_for_min_rpm(demands)
            if int_scale:
                self.recipe.ceil_scale()

    def update_scale_rec(self, level: int, max_level: int = 20, int_scale=False):
        self.update_scale(int_scale)
        if level < max_level:
            for producer in self.producers.values():
                producer.update_scale_rec(level + 1, max_level=max_level, int_scale=int_scale)

    def set_scale(self, scale: float):
        self.recipe.scale = max(scale, 1.0)

    def recipe_id(self):
        return self.recipe.recipe_id()

    def __repr__(self):
        return f'GraphNode["{self.recipe.recipe.name}"]'

    def __str__(self):
        return f'{self.recipe.scale:.1f}x {self.recipe.recipe.str_for_rpm()}'


class ProductionGraph:
    __slots__ = ('nodes', 'root', 'integer_scales', 'root_product')

    def __init__(self, root_recipe: data.Recipe, scale: float, target_product: Optional[data.Resource]):
        root_node = GraphNode(data.ScaledRecipe(root_recipe, scale), 0)
        self.root_product = target_product
        self.nodes: dict[str, GraphNode] = {root_recipe.id: root_node}
        self.root = root_node
        self.integer_scales = False

    def add_recipe(self, recipe: data.Recipe, consumer: GraphNode, level: int) -> GraphNode:
        recipe_id = recipe.id
        if recipe_id not in self.nodes:
            node = GraphNode(data.ScaledRecipe(recipe, 1.0), level)
            self.nodes[recipe_id] = node
        else:
            node = self.nodes[recipe_id]
            if level < node.level:
                node.level = level
        node.register_consumer(consumer)
        node.update_scale(self.integer_scales)
        return node

    def update_scales(self):
        self.root.update_scale_rec(0, int_scale=self.integer_scales)

    def as_list(self) -> list[GraphNode]:
        result = list(self.nodes.values())
        result.sort(key=lambda node: node.level)
        return result

    def get_total_resources(self) -> data.ResourceQuantities:
        totals = data.ResourceQuantities([])
        for node in self.nodes.values():
            recipe = node.recipe.scaled_components()
            for resource in recipe.resources:
                totals.add(resource)
        return totals

    def get_total_products(self) -> data.ResourceQuantities:
        totals = data.ResourceQuantities([])
        for node in self.nodes.values():
            recipe = node.recipe
            recipe_components = recipe.scaled_components()
            for product in recipe_components.products:
                totals.add(product)
        return totals


def _add_tree_node(graph: ProductionGraph, tree_node: BaseNode, consumer_node: GraphNode, level: int):
    if isinstance(tree_node, ProdNode):
        current_node = graph.add_recipe(tree_node.recipe, consumer_node, level)
        for child_tree_node in tree_node:
            _add_tree_node(graph, child_tree_node, current_node, level + 1)
    elif isinstance(tree_node, AltNode):
        _add_tree_node(graph, tree_node.active, consumer_node, level)
    elif isinstance(tree_node, EndNode):
        pass


def convert_to_graph(tree: ProductionTree, target_product: Optional[data.Resource]) -> ProductionGraph:
    scale = tree.root.rpm / tree.root.production.base_rpm
    graph = ProductionGraph(tree.root.recipe, scale, target_product)
    for node in tree.root:
        _add_tree_node(graph, node, graph.root, 1)

    graph.update_scales()
    return graph
