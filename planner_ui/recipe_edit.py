from copy import copy
import tkinter as tk
from tkinter import ttk
import typing
from typing import Optional, Callable

from config import MainConfig
from data import Recipe, Entity, ResourceQuantity, Resource, ResourceQuantities
from planner_ui import RootController, T, entity_select, Controller, add_unimplemented_label
from planner_ui.entity_select import ResQtSelectController, EntitySelect, EntitySelectController, ResQtSelect
from repository import RecipeRepository


class ResourceQuantityEditController(Controller[tuple[ResourceQuantities, float]]):

    def __init__(self, master, name: str, parent: typing.Optional[Controller], repository: RecipeRepository,
                 c0_name: str, label_text: str):
        super().__init__(name, parent)
        self.var_quantity = tk.StringVar()

        self.view = ResourceQuantityEdit(master, self, label_text)
        self.res_qt_select_ctl = ResQtSelectController(self.view, 'resource_qt_select', self, c0_name)
        self.resource_select_ctl = EntitySelectController(self.view, 'resource_select', self, repository,
                                                          entity_type=Resource, is_readonly=True)
        self.listeners_change = []
        self.view.init_components()

        self.view.sb_quantity.configure(command=lambda: self.cb_qt_attr_change(), from_=0.0, to=9999.9, increment=1.0)
        self.res_qt_select_ctl.register_selection_change(self.cb_res_qt_sel_change)

    def widget(self) -> tk.Widget:
        return self.view

    def value(self) -> typing.Optional[tuple[ResourceQuantities, float]]:
        res_qt = self.res_qt_select_ctl.res_qt
        cycle_time = self.res_qt_select_ctl.cycle_time
        if res_qt is not None and cycle_time is not None:
            return res_qt, cycle_time
        else:
            return None

    def set_value(self, val: tuple[ResourceQuantities, float]):
        self.res_qt_select_ctl.set_value(val)
        self.var_quantity.set('')

    def cb_qt_attr_change(self, *args):
        new_qt = float(self.var_quantity.get())
        selected_qt = self.res_qt_select_ctl.value()
        differs = selected_qt[0].quantity != new_qt
        for listener in self.listeners_change:
            listener(differs)
        return new_qt

    def cb_resource_change(self):
        self.resource_select_ctl.set_value(None)

    def cb_btn_add_resource(self):
        res_select_res = self.resource_select_ctl.value()
        if res_select_res is not None and isinstance(res_select_res, Resource):
            self.res_qt_select_ctl.res_qt.add(ResourceQuantity(res_select_res, 1))

    def cb_res_qt_sel_change(self, selection: tuple[str]):
        if len(selection) > 0:
            quantity = self.res_qt_select_ctl.res_qt[selection[0]]
            self.var_quantity.set(quantity.quantity)
            self.resource_select_ctl.set_value(quantity.resource)
        else:
            self.var_quantity.set('')

    def register_qt_attr_change(self, cb: Callable):
        self.listeners_change.append(cb)


class ResourceQuantityEdit(ttk.Labelframe):

    def __init__(self, master, controller: ResourceQuantityEditController, label_text: str):
        super().__init__(master, text=label_text)
        self.controller = controller

        self.frame_controls = tk.Frame(self)
        self.lbl_quantity = tk.Label(self.frame_controls, text='Quantity')
        self.lbl_quantity.grid(row=1, column=0)
        self.sb_quantity = ttk.Spinbox(self.frame_controls, increment=1, from_=1, textvariable=controller.var_quantity)
        self.sb_quantity.grid(row=1, column=1)

        self.res_qt_select: Optional[ResQtSelect] = None
        self.resource_select: Optional[EntitySelect] = None

    def init_components(self):
        if self.res_qt_select is None:
            self.res_qt_select = self.controller.res_qt_select_ctl.widget()
            self.res_qt_select.grid(row=0, column=0, sticky=tk.NSEW, padx=10, pady=10)
            self.rowconfigure(0, weight=1)
        if self.resource_select is None:
            self.resource_select = self.controller.resource_select_ctl.widget()
            self.resource_select.grid(row=0, column=1, sticky=tk.NSEW, padx=10, pady=10)
        self.frame_controls.grid(row=0, column=2)


class RecipeEditController(RootController[Recipe]):

    def __init__(self, master, name: str, parent: typing.Optional[Controller], repository: RecipeRepository):
        super().__init__(name, parent, repository)
        self.is_mod = False
        self.view = RecipeEditView(master, self)
        self.recipe_select_ctl = entity_select.EntitySelectController(self.view, 'recipe_select', self, repository,
                                                                      Recipe, 'Recipe', True, False)
        self.resources_ctl = ResourceQuantityEditController(self.view, 'resources_qt_edit', self, repository, 'Product',
                                                            'Resources')
        self.products_ctl = ResourceQuantityEditController(self.view, 'products_qt_edit', self, repository, 'Resource',
                                                           'Products')

        self.view.init_components()
        self.recipe_select_ctl.register_cb_sel_change(self.cb_recipe_sel_change)
        self.recipe_select_ctl.register_cb_attr_change(self.cb_attr_change)
        self.resources_ctl.register_qt_attr_change(self.cb_attr_change)
        self.products_ctl.register_qt_attr_change(self.cb_attr_change)
        self.view.btn_save.configure(command=lambda: self.cb_save())

    def widget(self) -> tk.Widget:
        return self.view

    def value(self) -> typing.Optional[T]:
        pass

    def set_value(self, val: T):
        pass

    def cb_attr_change(self, is_mod: bool):
        self.logger.debug(f'{self}: attributes changed: is_mod={is_mod}')
        if is_mod and not self.is_mod:
            self.view.btn_save.configure(state='normal')
        elif self.is_mod and not is_mod:
            self.view.btn_save.configure(state='disabled')
        self.is_mod = is_mod

    def cb_recipe_sel_change(self, entity: typing.Optional[Entity]):
        if self.is_mod:
            self.view.btn_save.configure(state='disabled')
            self.is_mod = False
        if entity is not None or isinstance(entity, Recipe):
            self.resources_ctl.set_value((copy(entity.resources), entity.cycle_time) if entity is not None else None)
            self.products_ctl.set_value((copy(entity.products), entity.cycle_time) if entity is not None else None)

    def cb_save(self):
        if self.is_mod:
            recipe = copy(self.recipe_select_ctl.value())
            if isinstance(recipe, Recipe):
                resource_quantities = self.resources_ctl.value()[0]
                product_quantities = self.products_ctl.value()[0]
                if not resource_quantities.is_equal(recipe.resources):
                    recipe.resources = resource_quantities
                if not product_quantities.is_equal(recipe.products):
                    recipe.products = product_quantities
                self.repository.update_recipe(recipe)
                #self.is_mod = False
                self.cb_attr_change(False)


class RecipeEditView(ttk.Frame):

    def __init__(self, master, controller: RecipeEditController):
        super().__init__(master)
        self.controller = controller
        self.recipe_select_view = None
        self.products_view = None
        self.resources_view = None
        add_unimplemented_label(self)

        self.btn_save = tk.Button(self, text='Save', state='disabled')
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

    def init_components(self):
        row = 1
        if self.recipe_select_view is None:
            self.recipe_select_view = self.controller.recipe_select_ctl.widget()
            self.recipe_select_view.grid(row=row, column=0, columnspan=2, sticky=tk.NSEW)
            self.rowconfigure(row, weight=1)
        row += 1

        if self.resources_view is None:
            self.resources_view = self.controller.resources_ctl.widget()
            self.resources_view.grid(row=row, column=0, sticky=tk.NSEW)
            self.rowconfigure(row, weight=1)
        row += 1

        if self.products_view is None:
            self.products_view = self.controller.products_ctl.widget()
            self.products_view.grid(row=row, column=0, sticky=tk.NSEW)
            self.rowconfigure(row, weight=1)
        row += 1

        self.btn_save.grid(row=row, column=0, columnspan=2, sticky=tk.NSEW, pady=10)
