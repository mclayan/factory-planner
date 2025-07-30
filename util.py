import datetime
import io
import jinja2

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

