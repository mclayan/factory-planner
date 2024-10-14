import copy
import math
import typing
from abc import ABC
from datetime import timedelta
from typing import Self

class Entity(ABC):

    def __init__(self, name: str, entity_id: str):
        self.name = name
        self.id = entity_id

    def get_name(self) -> str:
        return self.name

    def get_id(self) -> str:
        return self.id


class Resource(Entity):

    def __init__(self, name: str, res_id: str, is_raw: bool=False):
        super().__init__(name, res_id)
        self.is_raw = is_raw

    def __str__(self):
        return self.name

    def n(self, n: float) -> 'ResourceQuantity':
        return ResourceQuantity(self, n)

    def as_dict(self) -> dict[str, str]:
        return {
            'name': self.name,
            'id': self.id,
            'raw': self.is_raw,
        }


class ResourceQuantity:

    def __init__(self, resource: Resource, quantity: float):
        self.resource = resource
        self.quantity = quantity

    def scale(self, fac: float) -> Self:
        return ResourceQuantity(self.resource, self.quantity * fac)

    def __str__(self):
        return f'{self.quantity:.1f}x({self.resource.name})'

    def __copy__(self) -> typing.Self:
        return ResourceQuantity(self.resource, self.quantity)

    def as_dict(self) -> dict:
        return {
            'id': self.resource.id,
            'quantity': self.quantity
        }

    def is_equal(self, other):
        if not isinstance(other, ResourceQuantity):
            return False
        return self.resource == other.resource and self.quantity == other.quantity


class ResourceQuantities:

    def __init__(self, resources: list[ResourceQuantity]):
        self._inner: dict[str, ResourceQuantity] = dict()
        for res in resources:
            res_id = res.resource.id
            if res.resource.id in self._inner:
                self._inner[res_id].quantity += res.quantity
            else:
                self._inner[res_id] = res

    def add(self, res_qt: ResourceQuantity):
        res_id = res_qt.resource.id
        if res_id in self._inner:
            self._inner[res_id].quantity += res_qt.quantity
        else:
            self._inner[res_id] = res_qt

    def pairs(self):
        return self._inner.items()

    def values(self):
        return self._inner.values()

    def keys(self):
        return self._inner.keys()

    def __getitem__(self, item):
        return self._inner.__getitem__(item)

    def __setitem__(self, key, value):
        self._inner.__setitem__(key, value)

    def __contains__(self, item):
        return self._inner.__contains__(item)

    def __iter__(self):
        return self._inner.values().__iter__()

    def __len__(self):
        return self._inner.__len__()

    def __copy__(self):
        cp = super().__new__(ResourceQuantities)
        cp._inner = copy.copy(self._inner)
        return cp

    def is_equal(self, other):
        if not isinstance(other, ResourceQuantities):
            return False
        if len(self._inner.items()) != len(other._inner.items()):
            return False

        for res_id, qt in self._inner.items():
            other_qt = other._inner.get(res_id, None)
            if other_qt is None or not other_qt.is_equal(qt):
                return False
        return True

    def copy_shallow(self) -> typing.Self:
        copied = ResourceQuantities([])
        for res_qt in self._inner.values():
            copied.add(ResourceQuantity(res_qt.resource, res_qt.quantity))
        return copied


class ProductionResources:

    def __init__(self, resources: list[ResourceQuantity], byproducts: list[ResourceQuantity]):
        self.resources = resources
        self.byproducts = byproducts


class TargetedProduction:

    def __init__(self, product: Resource,
                 resources: list[ResourceQuantity],
                 byproducts: list[ResourceQuantity],
                 base_rpm: float):
        self.product = product
        self.resources = resources
        self.byproducts = byproducts
        self.base_rpm = base_rpm

    def for_rpm(self, rpm: float) -> ProductionResources:
        resources = [r_qt.scale(rpm) for r_qt in self.resources]
        byproducts = [r_qt.scale(rpm) for r_qt in self.byproducts]
        return ProductionResources(resources, byproducts)

    def __str__(self) -> str:
        return self.str_for_rpm(self.base_rpm)

    def str_for_rpm(self, rpm: float):
        recipe_fact = rpm / self.base_rpm
        result = f'{recipe_fact:.1f}x "{self.product.name}": ['
        r_count = 0
        for resource in self.resources:
            if r_count > 0:
                result += f' + {resource.scale(rpm)}'
            else:
                result += str(resource.scale(rpm))
            r_count += 1
        result += f' -> {rpm:.1f}x({self.product})'
        for bp in self.byproducts:
            result += f' + {bp.scale(rpm)}'

        return result + ' p.m.]'

    def get_base_rpm(self) -> float:
        return self.base_rpm


class RecipeComponents:

    def __init__(self, resources: ResourceQuantities, products: ResourceQuantities):
        self.resources = resources
        self.products = products


class Recipe(Entity):

    def __init__(self, name: str, recipe_id: str, resources: list[ResourceQuantity], products: list[ResourceQuantity], cycle_time: timedelta):
        super().__init__(name, recipe_id)
        self.cycle_time = cycle_time.total_seconds()
        self.resources = ResourceQuantities([r for r in resources])
        self.products = ResourceQuantities([p for p in products])
        self.source_name: typing.Optional[str] = None

    def production(self, product: Resource) -> typing.Optional[TargetedProduction]:
        if product.id not in self.products:
            return None
        else:
            prod_qt = self.products[product.id]
            prod_factor = prod_qt.quantity
            byproducts = [prod.scale(prod_factor) for p_id, prod in self.products.pairs() if p_id != product.id]
            rpm = (60 / self.cycle_time) * prod_factor
            return TargetedProduction(product, [res.scale(1 / prod_factor) for res in self.resources], byproducts, rpm)

    def scaled(self, factor: float) -> RecipeComponents:
        rpm_factor = 60 / self.cycle_time
        scale_factor = rpm_factor * factor
        requirements = ResourceQuantities([rq.scale(scale_factor) for rq in self.resources])
        products = ResourceQuantities([rq.scale(scale_factor) for rq in self.products])
        return RecipeComponents(requirements, products)


    def __copy__(self) -> typing.Self:
        cp = super().__new__(Recipe)
        cp.id = self.id
        cp.name = self.name
        cp.cycle_time = self.cycle_time
        cp.source_name = self.source_name
        cp.resources = copy.copy(self.resources)
        cp.products = copy.copy(self.products)

        return cp

    def __str__(self) -> str:
        result = f'Recipe "{self.name}": ['
        r_count = 0
        for resource in self.resources:
            if r_count > 0:
                result += f' + {resource}'
            else:
                result += str(resource)
            r_count += 1
        if r_count == 0:
            result += self.source_name if self.source_name is not None else '()'
        result += f' -> '
        prod_count = 0
        for prod in self.products:
            if prod_count > 0:
                result += f' + {prod}'
            else:
                result += str(prod)
            prod_count += 1

        return result + ']'

    def str_for_rpm(self) -> str:
        result = f'Recipe "{self.name}": ['
        r_count = 0
        components = self.scaled(1.0)
        for resource in components.resources:
            if r_count > 0:
                result += f' + {resource}'
            else:
                result += str(resource)
            r_count += 1
        if r_count == 0:
            result += self.source_name if self.source_name is not None else '()'
        result += f' -> '
        prod_count = 0
        for prod in components.products:
            if prod_count > 0:
                result += f' + {prod}'
            else:
                result += str(prod)
            prod_count += 1

        return result + ' RPM]'

    def nth_product(self, n: int) -> typing.Optional[Resource]:
        i = 0
        for product in self.products:
            if i == n:
                return product.resource
            i += 1
        return None

    def as_dict(self) -> dict:
        result = {
            'name': self.name,
            'id': self.id,
            'cycle_secs': self.cycle_time,
            'products': [r.as_dict() for r in self.products],
            'resources': [r.as_dict() for r in self.resources]
        }
        if self.source_name is not None:
            result['source_name'] = self.source_name
        return result

    def scale_factor_for_product(self, product: Resource, target_rpm: float) -> float:
        base_production = self.production(product)
        return target_rpm / base_production.base_rpm

    def is_equal(self, other) -> bool:
        if not isinstance(other, Recipe):
            return False
        if self.source_name != other.source_name \
            or self.name != other.name \
            or self.id != other.id:
            return False

        return self.resources.is_equal(other.resources)



class ScaledRecipe:

    def __init__(self, recipe: Recipe, scale: float):
        self.recipe = recipe
        self.scale = scale

    def scaled_components(self) -> RecipeComponents:
        return self.recipe.scaled(self.scale)

    def recipe_id(self) -> str:
        return self.recipe.id


    def scale_for_min_rpm(self, product_quantities: ResourceQuantities):
        new_scale = self.scale
        products = self.scaled_components().products
        for target_product in product_quantities:
            p_id = target_product.resource.id
            if p_id in products:
                rpm_factor = target_product.quantity / products[p_id].quantity
                adj_scal = self.scale * rpm_factor
                if adj_scal > new_scale:
                    new_scale = adj_scal
        if new_scale - self.scale > 0.09:
            self.scale = new_scale

    def ceil_scale(self):
        if self.scale - int(self.scale) > 0.09:
            self.scale = math.ceil(self.scale)

    def __repr__(self):
        return f'ScaledRecipe[{self.scale:.2f}x "{self.recipe.name}"]'
