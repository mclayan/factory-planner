import json
from datetime import timedelta
from typing import Self


class ResourceQuantity:
    pass


class Resource:

    def __init__(self, name: str, res_id: str, is_raw: bool=False):
        self.name = name
        self.id = res_id
        self.is_raw = is_raw

    def __str__(self):
        return self.name

    def n(self, n: float) -> ResourceQuantity:
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

    def as_dict(self) -> dict:
        return {
            'id': self.resource.id,
            'quantity': self.quantity
        }


class ProductionResources:

    def __init__(self, resources: list[ResourceQuantity], byproducts: list[ResourceQuantity]):
        self.resources = resources
        self.byproducts = byproducts


class Production:

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


class Recipe:

    def __init__(self, name: str, recipe_id: str, resources: list[ResourceQuantity], products: list[ResourceQuantity], cycle_time: timedelta):
        self.name = name
        self.id = recipe_id
        self.cycle_time = cycle_time.total_seconds()

        self.resources: dict[str, ResourceQuantity] = dict()
        for res_qt in resources:
            self.resources[res_qt.resource.id] = res_qt

        self.products: dict[str, ResourceQuantity] = dict()
        for res_qt in products:
            self.products[res_qt.resource.id] = res_qt

    def production(self, product: Resource) -> Production | None:
        if product.id not in self.products.keys():
            return None
        else:
            prod_qt = self.products[product.id]
            prod_factor = prod_qt.quantity
            byproducts = [prod.scale(prod_factor) for p_id, prod in self.products.items() if p_id != product.id]
            rpm = (60 / self.cycle_time) * prod_factor
            return Production(product, [res.scale(1 / prod_factor) for res in self.resources.values()], byproducts, rpm)

    def __str__(self) -> str:
        result = f'Recipe "{self.name}": ['
        r_count = 0
        for resource in self.resources.values():
            if r_count > 0:
                result += f' + {resource}'
            else:
                result += str(resource)
            r_count += 1
        result += f' -> '
        prod_count = 0
        for prod in self.products.values():
            if prod_count > 0:
                result += f' + {prod}'
            else:
                result += str(prod)
            prod_count += 1

        return result + ']'

    def nth_product(self, n: int) -> Resource|None:
        i = 0
        for product in self.products.values():
            if i == n:
                return product.resource
            i += 1
        return None

    def as_dict(self) -> dict:
        return {
            'name': self.name,
            'id': self.id,
            'cycle_secs': self.cycle_time,
            'products': [r.as_dict() for r in self.products.values()],
            'resources': [r.as_dict() for r in self.resources.values()],
        }

