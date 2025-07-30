import datetime
import io

import jinja2

import util
from config import MainConfig

__all__ = ['generate_html_report', 'generate_text_report']

class PlanInfo:

    def __init__(self, recipe_name: str):
        self.date = datetime.date.today().isoformat()
        self.notes = []
        self.recipe_name = recipe_name


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


def generate_html_report(sink: io.TextIOBase, graph: util.ProductionGraphModel):
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader("data/templates"),
        autoescape=jinja2.select_autoescape()
    )
    template = env.get_template('production_plan.html.jinja2')

    recipe_list = []
    plan = PlanInfo(graph.graph.root_product.name)

    sp_tag_val = MainConfig().gui_config.special_resource_tag.tag_val
    sp_tag_desc = (MainConfig().gui_config.special_resource_tag.display_name or 'special product').upper()
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
            recipe.products.append(res)
        recipe_list.append(recipe)

    sink.write(template.render(plan=plan, recipes=recipe_list))

def generate_text_report(sink: io.TextIOBase, graph: util.ProductionGraphModel):
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