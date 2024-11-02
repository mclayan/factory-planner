import tkinter as tk
import tkinter.ttk as ttk
import typing
from tkinter import StringVar, Label
from typing import Optional
from tkinter.font import Font

import chaining
from chaining import ProductionGraph, ProductionTree
from data import Recipe, Resource
from . import Controller, RootController, T, View
from repository import RecipeRepository
from .entity_select import EntitySelectController, EntitySelect, EntityMultiSelectController


class PlannerController(RootController):

    def __init__(self, master, v_id: str, parent: typing.Optional[typing.Self], repository: RecipeRepository):
        super().__init__(v_id, parent, repository)
        self.var_target_rpm = tk.DoubleVar()

        self.view = Planner(master, self)
        self.ctl_recipe_select = EntitySelectController(self.view, 'recipe_sel', self, repository, Recipe,
                                                        'End Product Recipe', False, True)

        self.ctl_product_select = EntitySelectController(self.view, 'product_sel', self, repository, Resource,
                                                         'Product', False, True, id_filter=[])
        self.ctl_recipe_blacklist = EntityMultiSelectController(self.view, 'recipe_blacklist', self, repository, Recipe, 'Excluded Recipes', True, id_filter=None)
        self.ctl_station_plan = StationPlanViewController(self.view, 'stations', self)
        self.view.init_components(self.ctl_recipe_select.widget(), self.ctl_product_select.widget(),
                                  self.ctl_recipe_blacklist.widget(),
                                  self.ctl_station_plan.widget())
        self.ctl_recipe_select.register_cb_sel_change(self.cb_recipe_sel_changed)
        self.ctl_product_select.register_cb_sel_change(self.cb_product_sel_changed)

    def generate_chain(self, recipe: Recipe, product: Resource, rpm: float):
        excluded_recipes = set(r.id for r in self.ctl_recipe_blacklist.value())
        tree = ProductionTree(recipe, product, rpm)
        tree.build(self.repository, excluded_recipes=excluded_recipes)
        graph = chaining.convert_to_graph(tree, product)
        graph.integer_scales = True
        graph.update_scales()
        self.ctl_station_plan.set_value(graph)

    def cb_btn_generate(self, *args):
        self.ctl_station_plan.clear_display()
        rpm = self.var_target_rpm.get()
        recipe = self.ctl_recipe_select.value()
        if isinstance(recipe, Recipe):
            product = self.ctl_product_select.selected()
            self.generate_chain(recipe, product, rpm)

    def cb_recipe_sel_changed(self, recipe):
        if isinstance(recipe, Recipe):
            self.view.btn_generate.configure(state='disabled')
            self.ctl_product_select.clear_display()
            self.ctl_product_select.id_filter = [p_id for p_id in recipe.products.keys()]
            self.ctl_product_select.update_entities()
            if len(recipe.products) == 1:
                self.ctl_product_select.set_value(recipe.nth_product(0))
            else:
                self.var_target_rpm.set(1.0)

    def cb_product_sel_changed(self, product):
        recipe = self.ctl_recipe_select.value()
        if isinstance(product, Resource) and isinstance(recipe, Recipe):
            self.var_target_rpm.set(recipe.scaled(1).products[product.id].quantity)
            self.view.btn_generate.configure(state='normal')

    def widget(self) -> tk.Widget:
        return self.view

    def value(self) -> typing.Optional[T]:
        return None

    def set_value(self, val: T):
        pass


class Planner(ttk.Frame, View):
    _HELP_TEXTS = {
        'recipe_select': 'Use this recipe as the root from which to build the production plan:',
        'product_select': 'Root output product of the recipe:',
        'recipe_blacklist': 'Exclude the following recipes from the calculation:'
    }

    def __init__(self, master, controller: PlannerController):
        View.__init__(self, controller)
        super().__init__(master)
        row = 0

        self.rpm_frame = tk.LabelFrame(self, text='Scaling')
        self.lbl_target_rpm = tk.Label(self.rpm_frame, text='Target RPM')
        self.lbl_target_rpm.grid(row=0, column=0, sticky=tk.W, padx=10, pady=10)
        self.sb_target_rpm = ttk.Spinbox(self.rpm_frame, textvariable=controller.var_target_rpm, from_=0, increment=0.1)
        self.sb_target_rpm.grid(row=0, column=1, sticky=tk.W)
        self.btn_generate = tk.Button(self, text='Generate', command=controller.cb_btn_generate, state='disabled')

        self.row_components = row
        self.vw_recipe_select: Optional[EntitySelect] = None
        self.lbl_recipe_select: Optional[Label] = None
        self.lbl_product_select: Optional[Label] = None
        self.lbl_recipe_blacklist: Optional[Label] = None

        self.vw_product_select: Optional[EntitySelect] = None
        self.vw_blacklist_select: Optional[EntitySelect] = None
        self.vw_station_plan: Optional[StationPlanView] = None
        self.columnconfigure(index=0, weight=1)
        self.columnconfigure(index=1, weight=1)

    def init_components(self, recipe_sel: EntitySelect, product_select: EntitySelect, blacklist_select: EntitySelect, station_plan: 'StationPlanView'):
        row = self.row_components
        self.vw_recipe_select = recipe_sel
        # hacky but avoids extending EntitySelect
        recipe_sel.tv_entities.grid(row=1)
        self.lbl_recipe_select = Label(recipe_sel, text=self._HELP_TEXTS['recipe_select'])
        self.lbl_recipe_select.grid(row=0, column=0)

        self.vw_product_select = product_select
        product_select.tv_entities.grid(row=1)
        self.lbl_product_select = Label(product_select, text=self._HELP_TEXTS['product_select'])
        self.lbl_product_select.grid(row=0)

        self.vw_blacklist_select = blacklist_select
        blacklist_select.tv_entities.grid(row=1)
        self.lbl_recipe_blacklist = Label(blacklist_select, text=self._HELP_TEXTS['recipe_blacklist'])
        self.lbl_recipe_blacklist.grid(row=0)

        self.vw_recipe_select.grid(row=row, column=0, sticky=tk.NSEW)
        self.vw_product_select.grid(row=row, column=1, sticky=tk.NSEW, padx=10)
        self.vw_blacklist_select.grid(row=row, column=2, sticky=tk.NSEW, padx=10)
        row += 1

        self.rpm_frame.grid(row=row, column=0, sticky=tk.EW, pady=10)
        self.btn_generate.grid(row=row, column=1, padx=10)
        row += 1

        self.vw_station_plan = station_plan
        self.vw_station_plan.grid(row=row, column=0, columnspan=3, sticky=tk.NSEW)
        self.rowconfigure(index=row, weight=1)


class StationPlanViewController(Controller):

    def __init__(self, master, v_id: str, parent: typing.Optional[Controller[T]]):
        super().__init__(v_id, parent)
        self.view = StationPlanView(master, self)
        self.graph: typing.Optional[ProductionGraph] = None

    def update_tree(self):
        tv = self.view.tv_recipe_stages
        for stage_node in self.graph.as_list():
            recipe = stage_node.recipe.recipe
            recipe_id = stage_node.recipe_id()
            id_in = f'{recipe_id}_in'
            id_out = f'{recipe_id}_out'
            recipe_consumer_count = len(stage_node.consumers.values())
            tv.insert('', 'end', iid=stage_node.recipe.recipe_id(), values=(
                f'{int(stage_node.recipe.scale)}', '', stage_node.recipe.recipe.name, '', '', '', '', recipe_consumer_count
            ), tags=('row_recipe',))
            tv.insert(recipe_id, 'end', iid=id_in, values=('', 'IN'), open=True, tags=('row_io',))
            tv.insert(recipe_id, 'end', iid=id_out, values=('', 'OUT'), open=True, tags=('row_io',))
            recipe_components = stage_node.recipe.scaled_components()
            recipe_demands = stage_node.resource_demand()

            if len(recipe.resources) == 0:
                tv.insert(id_in, 'end', iid=f'{recipe_id}_raw', values=('', '', '', '', recipe.source_name))
            else:
                for resource in recipe_components.resources:
                    in_res_id = f'{recipe_id}_{resource.resource.id}_in'
                    res_id = resource.resource.id
                    base_qt = int(stage_node.recipe.recipe.resources[res_id].quantity)
                    rpm = resource.quantity
                    tv.insert(id_in, 'end', iid=in_res_id, values=('', '', '', base_qt, resource.resource.name, f'{rpm:.1f}'),
                              tags=('row_resource',))
            for resource in recipe_components.products:
                out_res_id = f'{recipe_id}_{resource.resource.id}_out'
                res_id = resource.resource.id
                base_qt = int(stage_node.recipe.recipe.products[res_id].quantity)
                rpm = resource.quantity
                overflow = 0
                res_consumers = []
                is_excess = False
                if res_id in recipe_demands:
                    overflow = rpm - recipe_demands[res_id].quantity
                    for consumer in stage_node.consumers.values():
                        if res_id in consumer.recipe.recipe.resources:
                            res_consumers.append(consumer.recipe.recipe.name)
                elif res_id != self.graph.root_product.id:
                    res_consumers.append("<EXCESS PRODUCT>")
                    is_excess = True
                consumers = ", ".join(res_consumers)
                tv.insert(id_out, 'end', iid=out_res_id,
                          values=('', '', '',
                                  base_qt, resource.resource.name,
                                  f'{rpm:.1f}', f'{overflow:.1f}', consumers),
                          tags=('row_product' if not is_excess else 'row_product_excess',))

    def widget(self) -> 'StationPlanView':
        return self.view

    def value(self) -> typing.Optional[T]:
        return None

    def set_value(self, val: ProductionGraph):
        self.graph = val
        self.update_tree()

    def clear_display(self):
        items = self.view.tv_recipe_stages.get_children()
        self.view.tv_recipe_stages.delete(*items)


class StationPlanView(ttk.Frame, View):
    __HELP_TEXT = {
        'scale': 'Number of parallel executions of the recipe',
        'recipe': 'Name of the recipe',
        'io': 'Indicator if the row displays a resource or a product of the parent recipe',
        'res_qt': 'Base quantity of the resource/product (for one execution of the recipe)',
        'res_name': 'Name of the resource/product',
        'rpm': 'Demand or production of the resource or product per minute',
        'overflow': 'Difference between total output rate and actual demand. Assuming integer scales of a recipe, this will be a positive number for intermediate recipe executions if dependant recipes do not consume 100% of the output.',
        'c_count': 'Number of production steps (recipes) consuming products of this recipe.'
    }

    def __init__(self, master, controller: StationPlanViewController):
        View.__init__(self, controller)
        super().__init__(master)
        self.var_heading_help = StringVar()

        self.tv_recipe_stages = ttk.Treeview(self, columns=(
        'scale', 'io', 'recipe', 'res_qt', 'res_name', 'rpm', 'overflow', 'c_count'))
        self.tv_recipe_stages.grid(row=0, column=0, sticky=tk.NSEW)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.tv_recipe_stages.column('#0', minwidth=50, width=50, stretch=False)

        self.tv_recipe_stages.column('scale', minwidth=50, width=50, stretch=False)
        self.tv_recipe_stages.heading('scale', text='F', command=lambda: self.set_help('scale'), anchor='w')

        self.tv_recipe_stages.heading('recipe', text='Recipe', command=lambda: self.set_help('recipe'))

        self.tv_recipe_stages.column('io', width=60, stretch=False)
        self.tv_recipe_stages.heading('io', text='I/O', command=lambda: self.set_help('io'))

        self.tv_recipe_stages.heading('res_qt', text='B.Qt.', command=lambda: self.set_help('res_qt'))
        self.tv_recipe_stages.column('res_qt', width=60, stretch=False)
        self.tv_recipe_stages.column('rpm', width=80, stretch=False)

        self.tv_recipe_stages.heading('res_name', text='Resource', command=lambda: self.set_help('res_name'))
        self.tv_recipe_stages.heading('rpm', text='RPM', command=lambda: self.set_help('rpm'))
        self.tv_recipe_stages.heading('overflow', text='Overflow', command=lambda: self.set_help('overflow'))
        self.tv_recipe_stages.heading('c_count', text='Consumers', command=lambda: self.set_help('c_count'))

        self.tv_recipe_stages.bind('<Leave>', self.hide_tooltip)
        self.tv_recipe_stages.tag_configure('row_io', background='#bebebe')
        self.tv_recipe_stages.tag_configure('row_resource', background='#95a3c5')
        self.tv_recipe_stages.tag_configure('row_product', background='#88cf8e')
        self.tv_recipe_stages.tag_configure('row_product_excess', background='#ff6b6b')

        style = ttk.Style()
        row_font = Font(font=tk.font.nametofont(style.configure('.','font')))
        row_font['weight'] = 'bold'
        self.tv_recipe_stages.tag_configure('row_recipe', font=row_font)


        self.frame_help = ttk.LabelFrame(self, text='Help')
        self.frame_help.grid(row=1, column=0, sticky=tk.NSEW)
        self.lbl_help_text = tk.Label(self.frame_help, textvariable=self.var_heading_help)
        lbl_font = Font(font=self.lbl_help_text['font'])
        lbl_font['slant'] = 'italic'
        self.lbl_help_text.configure(font=lbl_font, wraplength=1000, justify="left")
        self.lbl_help_text.grid(row=0, column=0, sticky=tk.S + tk.EW)

    def set_help(self, col_id):
        self.var_heading_help.set(self.__HELP_TEXT.get(col_id, ''))

    def hide_tooltip(self, event):
        self.set_help('')
