import datetime
import io

import data
from chaining import ProductionGraph
from config import MainConfig


class ProductionGraphModel:

    def __init__(self, graph: ProductionGraph):
        self.nodes = graph.as_list()
        self.graph = graph
        self.total_resources = data.ResourceQuantities([])
        self.total_products = data.ResourceQuantities([])
        self.product_overflow = data.ResourceQuantities([])
        self.excess_products = data.ResourceQuantities([])
        self._update_totals()

    def _update_totals(self):
        self.total_resources = self.graph.get_total_resources()
        self.total_products = self.graph.get_total_products()

        for product in self.total_products:
            if not product.resource is self.graph.root_product:
                production = product.quantity
                demand = self.total_resources.get_quantity(product.resource, 0)
                if demand == 0:
                    self.excess_products.add(product)
                elif demand < production:
                    self.product_overflow.add(data.ResourceQuantity(product.resource, production - demand))

    def get_raw_totals(self) -> data.ResourceQuantities:
        result = data.ResourceQuantities([])
        for t in self.total_resources:
            if t.resource.is_raw:
                result.add(t)
        return result

def generate_report(sink: io.TextIOBase, graph: ProductionGraphModel):
    ilevel = 0
    date = datetime.date.today()
    plan_name = graph.graph.root.recipe.recipe.name
    part_0 = f'PRODUCTION PLAN || DATE: {date.isoformat()} || '
    filler = 80 - (len(plan_name) + len(part_0)) if (len(plan_name) + len(part_0)) <= 80 else 0
    header = f'{part_0}{" " * filler}{plan_name}'
    sink.write(header[:80])
    sink.write(f'\n{"=" * 80}\n')
    sink.write(f'**********************NOTES**********************\n')
    ilevel += 1

    sp_tag_val = MainConfig().gui_config.special_resource_tag.tag_val
    sp_tag_desc = (MainConfig().gui_config.special_resource_tag.display_name or 'special product').upper()
    for node in graph.nodes:
        recipe = node.recipe.recipe
        if sp_tag_val in recipe.tags:
            sink.write(f'{" " * 2 * ilevel}INCLUDED {sp_tag_desc}: {recipe.name}\n')
    sink.write(f'{" " * 2 * ilevel}TOTAL RAW RESOURCES:\n')
    ilevel += 1
    for resource in graph.total_resources:
        if resource.resource.is_raw:
            res_name = resource.resource.name.upper()
            res_qt = int(resource.quantity)
            sink.write(f'{" " * 2 * ilevel}{res_qt:04}x {res_name}\n')
    ilevel -= 1
    ilevel -= 1
    sink.write('\n')
    for node in graph.nodes:
        recipe_components = node.recipe.scaled_components()
        scale = node.recipe.scale
        consumers = []
        for consumer in node.consumers.values():
            consumers.append(consumer.recipe.recipe.get_name().upper())
        sink.write(f'PRODUCT NAME >> {node.recipe.recipe.name}\n')
        sink.write(f'  SCALE      >> {int(scale):03}\n')
        sink.write(f'  CONSUMERS  >> {", ".join(consumers)}\n')
        sink.write('     RECIPE:\n')
        ilevel += 1
        for resource in recipe_components.resources:
            resource_qt = resource.quantity
            sink.write(f'{" " * ilevel * 6} IN:  {int(resource_qt): 4} x {resource.resource.name}\n')
        sink.write(f'{" " * ilevel}{"-" * 50}\n')
        for product in recipe_components.products:
            resource_qt = product.quantity
            resource_id = product.resource.id
            if resource_id in graph.total_resources or resource_id == graph.graph.root_product.id:
                sink.write(f'{" " * ilevel * 6} OUT: {int(resource_qt): 4} x {product.resource.name}\n')
            else:
                sink.write(f'{" " * ilevel * 6} OUT: {int(resource_qt): 4} x {product.resource.name} **SIDE PRODUCT**\n')
        sink.write('\n')
        ilevel -= 1