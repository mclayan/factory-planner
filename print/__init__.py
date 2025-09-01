import datetime
import io
from typing import Optional

import jinja2

import configuration
import chaining
import data

__all__ = ['generate_html_report', 'generate_text_report', 'ProductionGraphModel']

class ProductionGraphModel:

    def __init__(self, graph: chaining.ProductionGraph):
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

class TemplateConfig:

    def __init__(self):
        self.notes_indicator = '>>'


class PlanInfo:

    def __init__(self, recipe_name: str, recipe_scale: int):
        self.date = datetime.date.today().isoformat()
        self.notes = []
        self.recipe_name = recipe_name
        self.recipe_scale = recipe_scale
        self.count_recipes = 0
        self.count_stations = 0

        main_cfg = configuration.MainConfig()
        self.operator_name = main_cfg.gui_config.current_user.name
        self.operator_department = main_cfg.gui_config.current_user.department
        self.operator_user = main_cfg.gui_config.current_user.user_id
        self.operator_workstation = main_cfg.gui_config.current_workstation.hostname


class GeneratorInfo:

    def __init__(self):
        main_cfg = configuration.MainConfig()
        self.name = main_cfg.APP_NAME
        self.version = main_cfg.APP_VERSION


class RenderRecipe:

    def __init__(self, name: str, scale):
        self.name = name
        self.scale = scale
        self.consumers: list[str] = []
        self.resources: list[RenderResource] = []
        self.products: list[RenderResource] = []


class RenderResource:

    def __init__(self, name: str, quantity: int):
        self.name = name
        self.quantity = quantity
        self.is_excess = False
        self.overflow = None


def default_notes() -> list[tuple[str, str, Optional[str]]]:
    return [
        ('s', '**NO RESOURCE/PRODUCTION CIRCLE DETECTED**', None)
    ]


def generate_html_report(sink: io.TextIOBase, graph: ProductionGraphModel):
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader("data/templates"),
        autoescape=jinja2.select_autoescape()
    )
    template = env.get_template('production_plan.html.jinja2')

    recipe_list = []
    plan = PlanInfo(graph.graph.root_product.name, int(graph.graph.root.recipe.scale))
    plan.notes.extend(default_notes())

    sp_tag_val = configuration.MainConfig().gui_config.special_resource_tag.tag_val
    sp_tag_desc = (configuration.MainConfig().gui_config.special_resource_tag.display_name or 'special product').upper()
    for node in graph.nodes:
        recipe = node.recipe.recipe
        if sp_tag_val in recipe.tags and recipe.id != graph.graph.root.recipe_id():
            plan.notes.append(('kv', f'INCLUDES {sp_tag_desc}:', recipe.get_name()))

    raw_res_note_list = []
    for resource in graph.total_resources:
        if resource.resource.is_raw:
            res_name = resource.resource.name.upper()
            res_qt = f'{int(resource.quantity):05} x'
            raw_res_note_list.append((res_qt, res_name))
    if len(raw_res_note_list) > 0:
        note_raw_res = ('l', 'TOTAL RAW RESOURCES:', raw_res_note_list)
        plan.notes.append(note_raw_res)

    notes_overflow = []
    for resource in graph.product_overflow:
        res_name = resource.resource.name.upper()
        res_qt = f'{int(resource.quantity):05} x'
        notes_overflow.append((res_qt, res_name))
    if len(notes_overflow) > 0:
        note_overflow = ('l', 'OVERFLOW OF PRODUCTS:', notes_overflow)
        plan.notes.append(note_overflow)
    else:
        plan.notes.append(('s', '**NO PRODUCT OVERFLOW**'))

    for node in graph.nodes:
        recipe_components = node.recipe.scaled_components()
        scale = int(node.recipe.scale)
        recipe = RenderRecipe(node.recipe.recipe.name, scale)

        for consumer in node.consumers.values():
            recipe.consumers.append(consumer.recipe.recipe.get_name().upper())

        for resource in recipe_components.resources:
            resource_qt = int(resource.quantity)
            recipe.resources.append(RenderResource(resource.resource.get_name(), resource_qt))

        for product in recipe_components.products:
            resource_qt = int(product.quantity)
            resource_id = product.resource.id
            res = RenderResource(product.resource.get_name(), resource_qt)
            if resource_id in graph.total_resources or resource_id == graph.graph.root_product.id:
                res.is_excess = False
            else:
                res.is_excess = True
            if resource_id in graph.product_overflow:
                res.overflow = graph.product_overflow[resource_id].quantity
            recipe.products.append(res)
        recipe_list.append(recipe)
        plan.count_recipes += 1
        plan.count_stations += int(node.recipe.scale)

    sink.write(
        template.render(plan=plan, recipes=recipe_list, style_config=TemplateConfig(), generator=GeneratorInfo()))


def generate_text_report(sink: io.TextIOBase, graph: ProductionGraphModel):
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

    sp_tag_val = configuration.MainConfig().gui_config.special_resource_tag.tag_val
    sp_tag_desc = (configuration.MainConfig().gui_config.special_resource_tag.display_name or 'special product').upper()
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
                sink.write(
                    f'{" " * ilevel * 6} OUT: {int(resource_qt): 4} x {product.resource.name} **SIDE PRODUCT**\n')
        sink.write('\n')
        ilevel -= 1
