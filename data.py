import json
from datetime import timedelta
from typing import Self


class ResourceQuantity:
    pass


class Resource:

    def __init__(self, name: str, res_id: str):
        self.name = name
        self.id = res_id

    def __str__(self):
        return self.name

    def n(self, n: float) -> ResourceQuantity:
        return ResourceQuantity(self, n)

    def as_dict(self) -> dict[str, str]:
        return {
            'name': self.name,
            'id': self.id,
        }


class ResourceQuantity:

    def __init__(self, resource: Resource, quantity: float):
        self.resource = resource
        self.quantity = quantity

    def scale(self, fac: float) -> Self:
        return ResourceQuantity(self.resource, self.quantity * fac)

    def __str__(self):
        return f'{self.quantity}x({self.resource.name})'

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
        if rpm == self.base_rpm:
            return ProductionResources(self.resources.copy(), self.byproducts.copy())
        else:
            fact = rpm / self.base_rpm
            return ProductionResources([res_qt.scale(fact) for res_qt in self.resources],
                                       [res_qt.scale(fact) for res_qt in self.byproducts])

    def __str__(self) -> str:
        result = f'Production "{self.product.name}": ['
        r_count = 0
        for resource in self.resources:
            if r_count > 0:
                result += f' + {resource.scale(self.base_rpm)}'
            else:
                result += str(resource.scale(self.base_rpm))
            r_count += 1
        result += f' -> {self.base_rpm}x({self.product})'
        for bp in self.byproducts:
            result += f' + {bp.scale(self.base_rpm)}'

        return result + ' p.m.]'


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
        if product.id not in self.products:
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

    def as_dict(self) -> dict:
        return {
            'name': self.name,
            'id': self.id,
            'cycle_secs': self.cycle_time,
            'products': [r.as_dict() for r in self.products.values()],
            'resources': [r.as_dict() for r in self.resources.values()],
        }


