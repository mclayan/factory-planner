import tkinter as tk
import tkinter.ttk as ttk
import typing
from operator import index
from tkinter import StringVar
from typing import Optional
from tkinter.font import Font

import chaining
from chaining import ProductionGraph, ProductionTree
from data import Recipe, Resource
from . import Controller, RootController, T, View
from repository import RecipeRepository
from .entity_select import EntitySelectController, EntitySelect


class PlannerController(RootController):

    def __init__(self, master, v_id: str, parent: typing.Optional[typing.Self], repository: RecipeRepository):
        super().__init__(v_id, parent, repository)
        self.var_target_rpm = tk.DoubleVar()

        self.view = Planner(master, self)
        self.ctl_recipe_select = EntitySelectController(self.view, 'recipe_sel', self, repository, Recipe,
                                                        'End Product Recipe', False, True)

        self.ctl_product_select = EntitySelectController(self.view, 'product_sel', self, repository, Resource,
                                                         'Product', False, True, id_filter=[])
        self.ctl_station_plan = StationPlanViewController(self.view, 'stations', self)
        self.view.init_components(self.ctl_recipe_select.widget(), self.ctl_product_select.widget(),
                                  self.ctl_station_plan.widget())
        self.ctl_recipe_select.register_cb_sel_change(self.cb_recipe_sel_changed)
        self.ctl_product_select.register_cb_sel_change(self.cb_product_sel_changed)

    def generate_chain(self, recipe: Recipe, product: Resource, rpm: float):
        tree = ProductionTree(recipe, product, rpm)
        tree.build(self.repository)
        graph = chaining.convert_to_graph(tree)
        graph.integer_scales = True
        graph.update_scales()
        self.ctl_station_plan.set_value(graph)

    def cb_btn_generate(self, *args):
        self.ctl_station_plan.clear_display()
        rpm = self.var_target_rpm.get()
        recipe = self.ctl_recipe_select.value()
        if isinstance(recipe, Recipe):
            product = recipe.nth_product(0)
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
        self.vw_product_select: Optional[EntitySelect] = None
        self.vw_station_plan: Optional[StationPlanView] = None
        self.columnconfigure(index=0, weight=1)
        self.columnconfigure(index=1, weight=1)

    def init_components(self, recipe_sel: EntitySelect, product_select: EntitySelect, station_plan: 'StationPlanView'):
        row = self.row_components
        self.vw_recipe_select = recipe_sel
        self.vw_product_select = product_select
        self.vw_recipe_select.grid(row=row, column=0, sticky=tk.NSEW)
        self.vw_product_select.grid(row=row, column=1, sticky=tk.NSEW, padx=10)
        row += 1


        self.rpm_frame.grid(row=row, column=0, sticky=tk.EW, pady=10)
        self.btn_generate.grid(row=row, column=1, padx=10)
        row += 1

        self.vw_station_plan = station_plan
        self.vw_station_plan.grid(row=row, column=0, columnspan=2, sticky=tk.NSEW)
        self.rowconfigure(index=row, weight=1)


class StationPlanViewController(Controller):

    def __init__(self, master, v_id: str, parent: typing.Optional[Controller[T]]):
        super().__init__(v_id, parent)
        self.view = StationPlanView(master, self)
        self.graph: typing.Optional[ProductionGraph] = None

    def update_tree(self):
        tv = self.view.tv_stations
        for stage_node in self.graph.as_list():
            recipe = stage_node.recipe.recipe
            recipe_id = stage_node.recipe_id()
            id_in = f'{recipe_id}_in'
            id_out = f'{recipe_id}_out'
            tv.insert('', 'end', iid=stage_node.recipe.recipe_id(), values=(
                stage_node.recipe.scale, '', stage_node.recipe.recipe.name
            ))
            tv.insert(recipe_id, 'end', iid=id_in, values=('', 'IN'), open=True, tags=('row_io',))
            tv.insert(recipe_id, 'end', iid=id_out, values=('', 'OUT'), open=True, tags=('row_io',))
            recipe_components = stage_node.recipe.scaled_components()
            if len(recipe.resources) == 0:
                tv.insert(id_in, 'end', iid=f'{recipe_id}_raw', values=('', '', '', '', recipe.source_name))
            else:
                for resource in recipe_components.resources:
                    in_res_id = f'{recipe_id}_{resource.resource.id}_in'
                    res_id = resource.resource.id
                    base_qt = int(stage_node.recipe.recipe.resources[res_id].quantity)
                    rpm = resource.quantity
                    tv.insert(id_in, 'end', iid=in_res_id, values=('', '', '', base_qt, resource.resource.name, rpm))
            for resource in recipe_components.products:
                out_res_id = f'{recipe_id}_{resource.resource.id}_out'
                res_id = resource.resource.id
                base_qt = int(stage_node.recipe.recipe.products[res_id].quantity)
                rpm = resource.quantity
                tv.insert(id_out, 'end', iid=out_res_id, values=('', '', '', base_qt, resource.resource.name, rpm))

    def widget(self) -> 'StationPlanView':
        return self.view

    def value(self) -> typing.Optional[T]:
        return None

    def set_value(self, val: ProductionGraph):
        self.graph = val
        self.update_tree()

    def clear_display(self):
        items = self.view.tv_stations.get_children()
        self.view.tv_stations.delete(*items)


class StationPlanView(ttk.Frame, View):
    __HELP_TEXT = {
        'scale': 'Number of parallel executions of the recipe',
        'recipe': 'Name of the recipe',
        'io': 'Indicator if the row displays a resource or a product of the parent recipe',
        'res_qt': 'Base quantity of the resource/product (for one execution of the recipe)',
        'res_name': 'Name of the resource/product',
        'rpm': 'Demand or production of the resource or product per minute'
    }

    def __init__(self, master, controller: StationPlanViewController):
        View.__init__(self, controller)
        super().__init__(master)
        self.var_heading_help = StringVar()

        self.tv_stations = ttk.Treeview(self, columns=('scale', 'io', 'recipe', 'res_qt', 'res_name', 'rpm'))
        self.tv_stations.grid(row=0, column=0, sticky=tk.NSEW)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.tv_stations.column('#0', minwidth=50, width=50, stretch=False)

        self.tv_stations.column('scale', minwidth=50, width=50, stretch=False)
        self.tv_stations.heading('scale', text='F', command=lambda: self.set_help('scale'), anchor='w')

        self.tv_stations.heading('recipe', text='Recipe', command=lambda: self.set_help('recipe'))

        self.tv_stations.column('io', width=60, stretch=False)
        self.tv_stations.heading('io', text='I/O', command=lambda: self.set_help('io'))

        self.tv_stations.heading('res_qt', text='Quantity', command=lambda: self.set_help('res_qt'))
        self.tv_stations.column('res_qt', width=80, stretch=False)

        self.tv_stations.heading('res_name', text='Resource', command=lambda: self.set_help('res_name'))
        self.tv_stations.heading('rpm', text='RPM', command=lambda: self.set_help('rpm'))

        self.tv_stations.bind('<Leave>', self.hide_tooltip)
        self.tv_stations.tag_configure('row_io', background='#bcbcbc')

        self.frame_help = ttk.LabelFrame(self, text='Help')
        self.frame_help.grid(row=1, column=0, sticky=tk.NSEW)
        self.lbl_help_text = tk.Label(self.frame_help, textvariable=self.var_heading_help)
        font = Font(font=self.lbl_help_text['font'])
        font['slant'] = 'italic'
        self.lbl_help_text.configure(font=font)
        self.lbl_help_text.grid(row=0, column=0, sticky=tk.S + tk.EW)


    def set_help(self, col_id):
        self.var_heading_help.set(self.__HELP_TEXT.get(col_id, ''))

    def hide_tooltip(self, event):
        self.set_help('')
