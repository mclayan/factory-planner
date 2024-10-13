import copy
import tkinter as tk
import tkinter.ttk as ttk
import typing
from abc import ABC
from collections.abc import Callable
from typing import Optional

from data import Entity, Recipe, Resource, ResourceQuantity, ResourceQuantities
from repository import RecipeRepository
from . import T, RootController

from .application import Controller

__all__ = ['EntitySelectController', 'EntitySelect']


class ResourceInfoVars:

    def __init__(self):
        self.is_raw = tk.BooleanVar()


class RecipeInfoVars:

    def __init__(self):
        self.products = tk.StringVar()
        self.resources = tk.StringVar()
        self.source_name = tk.StringVar()


class EntitySelectController(RootController[Entity]):

    def __init__(self, master, repository: RecipeRepository, entity_type: type, label_text=None, show_info=False, is_readonly=True):
        super().__init__(repository)
        self.entity_type = entity_type
        self.entity_source = self.repository.resources if issubclass(self.entity_type, Resource) else self.repository.recipes
        self.var_entities = tk.StringVar()
        self.repository = repository
        self.listeners_attr_change = []
        self.listeners_sel_change = []

        if label_text is None:
            label_text = 'Resource' if entity_type is Resource else 'Recipe'

        self.view = EntitySelect(master, self, label_text)
        self.items = ([], [])
        self.update_entities()
        self.entity_attr_controller = None
        if show_info:
            if issubclass(entity_type, Resource):
                self.entity_attr_controller = ResourceAttrController(self.view, is_readonly)
                self.view.init_info(self.entity_attr_controller.widget())
            elif issubclass(entity_type, Recipe):
                self.entity_attr_controller = RecipeAttrController(self.view, is_readonly)
                self.view.init_info(self.entity_attr_controller.widget())

    def update_entities(self):
        self.items = ([], [])
        for e_id, entity in self.entity_source.items():
            self.items[0].append(e_id)
            if isinstance(entity, Entity):
                self.items[1].append(entity.get_name())
            else:
                self.items[1].append(str(entity))
        self.var_entities.set(self.items[1])

    def cb_select_entity(self, event):
        selected_entity = self.selected()
        if selected_entity is not None:
            if self.entity_attr_controller is not None:
                self.entity_attr_controller.update_entity(copy.copy(self.selected()))
            for listener in self.listeners_sel_change:
                listener(self.selected())

    def register_cb_attr_change(self, cb: Callable):
        self.listeners_attr_change.append(cb)

    def register_cb_sel_change(self, cb: Callable[[Optional[Entity]], []]):
        self.listeners_sel_change.append(cb)


    def selected(self) -> typing.Optional[Recipe | Resource]:
        sel_ind = self.view.lb_entities.curselection()
        if sel_ind is not None and len(sel_ind) > 0:
            entity_id = self.items[0][sel_ind[0]]
            return self.entity_source.get(entity_id, None)
        else:
            return None

    def write_entity(self, entity: Entity):
        orig_entity = self.selected()
        if orig_entity is None:
            print(f'WARN: can\'t update entity if none is selected!')
            return

        if type(entity) != self.entity_type:
            print(f'WARN: write_entity called with type={type(entity)} but controller manages type={self.entity_type}!')
            return

        if self.repository is None:
            print(f'ERROR: cannot update entity because repository is None!')
            return
        result = self.repository.update_entity(orig_entity.id, entity)
        if result:
            self.update_entities()


    def widget(self) -> 'EntitySelect':
        return self.view

    def value(self) -> typing.Optional[Entity]:
        return self.selected()

    def clear_display(self):
        self.var_entities.set('')

    def set_value(self, val: Optional[Entity|int]):
        if isinstance(val, int):
            sel_index = val
        elif val is None:
            self.view.lb_entities.select_clear(0, len(self.items) - 1)
            return
        else:
            sel_index = None
            if type(val) != self.entity_type:
                print(f'WARN: set_value called with type={type(val)} but controller manages type={self.entity_type}!')
                return
            else:
                entity_id = val.id
                i = 0
                for e_id in self.items[0]:
                    if e_id == entity_id:
                        sel_index = i
                        break
                    i += 1
        if sel_index is None:
            print(f'WARN: requested item "{val}" is not in repository!')
        else:
            self.view.lb_entities.select_clear(0, len(self.items) - 1)
            self.view.lb_entities.selection_set(sel_index)
            self.view.lb_entities.see(sel_index)


class EntitySelect(ttk.Labelframe):
    #TODO: change ListBox to TreeView
    def __init__(self, master, controller: EntitySelectController, label_text: str):
        super().__init__(master=master, text=label_text, padding=(4, 4))
        self.controller = controller
        self.lb_entities = tk.Listbox(self, listvariable=self.controller.var_entities)
        self.lb_entities.bind('<<ListboxSelect>>', self.controller.cb_select_entity)
        self.lb_entities.grid(row=0, column=0, sticky=tk.NSEW, padx=10, pady=10)
        self.info_view = None

    def init_info(self, info_view: tk.Widget):
        self.info_view = info_view
        self.info_view.grid(row=0, column=1, sticky=tk.NSEW, padx=10, pady=10)


class EntityInfo(Controller[T], ABC):

    def __init__(self, is_readonly: bool):
        self.read_only = is_readonly


class ResourceAttrController(EntityInfo[Resource]):

    def __init__(self, master,is_readonly: bool, label_text=None):
        super().__init__(is_readonly)
        self.var_is_raw = tk.BooleanVar()
        self.var_name = tk.StringVar()
        self.var_id = tk.StringVar()
        self.entity = None
        self.view = ResourceInfo(master, self, label_text)

    def update_entity(self, new_val: Resource):
        if isinstance(new_val, Resource):
            self.entity = new_val
            self.var_is_raw.set(new_val.is_raw)
            self.var_name.set(new_val.name)
            self.var_id.set(new_val.id)
        else:
            print(f'WARN: {self}: invalid value for this type: {new_val}')

    def widget(self) -> tk.Widget:
        return self.view

    def value(self) -> Resource:
        return self.entity

    def set_value(self, val: Resource):
        self.update_entity(val)


class ResourceInfo(ttk.Labelframe):

    def __init__(self, master, controller: ResourceAttrController, label_text=None):
        super().__init__(master, text=label_text if label_text is not None else 'Resource Data')
        row = 0

        self.lbl_res_name = tk.Label(self, text='Name')
        self.lbl_res_name.grid(row=row, column=0, sticky=tk.W)

        self.en_res_name_val = tk.Entry(self, textvariable=controller.var_name)
        self.en_res_name_val.grid(row=row, column=1, sticky=tk.EW)
        row += 1

        self.lbl_res_id = tk.Label(self, text='Recipe ID')
        self.lbl_res_id.grid(row=row, column=0, sticky=tk.W)

        self.en_res_id = tk.Entry(self, textvariable=controller.var_id)
        self.en_res_id.grid(row=row, column=1, sticky=tk.EW)
        row += 1

        self.ckb_is_raw = tk.Checkbutton(self, text='Raw Resource', variable=controller.var_is_raw)
        self.ckb_is_raw.grid(row=row, column=1, sticky=tk.W)
        row += 1

        if controller.read_only:
            self.set_readonly(True)

    def set_readonly(self, ro: bool):
        self.en_res_name_val.configure(state='readonly' if ro else 'normal')
        self.en_res_id.configure(state='readonly' if ro else 'normal')
        self.ckb_is_raw.configure(state='disabled' if ro else 'normal')


class RecipeAttrController(EntityInfo[Recipe]):

    def __init__(self, master, is_readonly: bool, label_text=None):
        super().__init__(is_readonly)
        self.is_mod = False
        self.var_name = tk.StringVar()
        self.var_id = tk.StringVar()
        self.var_cycle_time = tk.DoubleVar()
        self.var_source_name = tk.StringVar()
        self.entity: typing.Optional[Recipe] = None
        self.entity_id: typing.Optional[str] = None
        self.view = RecipeInfo(master, self, label_text)

    def update_entity(self, new_val: Recipe):
        if isinstance(new_val, Recipe):
            self.entity = new_val
            self.var_name.set(new_val.name)
            self.var_id.set(new_val.id)
            self.var_cycle_time.set(new_val.cycle_time)
            self.var_source_name.set(new_val.source_name if new_val.source_name is not None else '')

            products = dict()
            resources = dict()
            for e_id, entity in new_val.products.pairs():
                products[e_id] = f'{int(entity.quantity):3} {entity.resource.name}'
            for e_id, entity in new_val.resources.pairs():
                resources[e_id] = f'{int(entity.quantity):3} {entity.resource.name}'

            if len(resources) > 0:
                self.view.en_source_name.configure(state='readonly')
            elif not self.read_only:
                self.view.en_source_name.configure(state='normal')
        else:
            print(f'WARN: {self}: invalid value for this type: {new_val}')

    def cb_edit_cycle_time(self):
        ct_new = self.var_cycle_time.get()
        if ct_new != self.entity.cycle_time:
            self.entity.cycle_time = ct_new
            self.is_mod = True

    def widget(self) -> ttk.Labelframe:
        return self.view

    def value(self) -> Recipe:
        return self.entity

    def set_value(self, val: Recipe):
        self.update_entity(val)


class RecipeInfo(ttk.Labelframe):

    def __init__(self, master, controller: RecipeAttrController, label_text=None):
        super().__init__(master, text=label_text if label_text is not None else 'Recipe Data')
        row = 0

        self.lbl_res_name = tk.Label(self, text='Name')
        self.lbl_res_name.grid(row=row, column=0, sticky=tk.W)

        self.en_res_name_val = tk.Entry(self, textvariable=controller.var_name)
        self.en_res_name_val.grid(row=row, column=1, sticky=tk.W)
        row += 1

        self.lbl_rec_id = tk.Label(self, text='Recipe ID')
        self.lbl_rec_id.grid(row=row, column=0, sticky=tk.W)

        self.en_rec_id = tk.Entry(self, textvariable=controller.var_id)
        self.en_rec_id.grid(row=row, column=1, sticky=tk.EW)
        row += 1

        self.lbl_source_name = tk.Label(self, text='Source (name)')
        self.lbl_source_name.grid(row=row, column=0, sticky=tk.W)

        self.en_source_name = tk.Entry(self, textvariable=controller.var_source_name)
        self.en_source_name.grid(row=row, column=1, sticky=tk.EW)
        row += 1

        self.lbl_cycle_time = tk.Label(self, text='Cycle time (seconds)')
        self.lbl_cycle_time.grid(row=row, column=0, sticky=tk.W)

        self.en_cycle_time = tk.Entry(self, textvariable=controller.var_cycle_time)
        self.en_cycle_time.grid(row=row, column=1, sticky=tk.EW)
        row += 1


        if controller.read_only:
            self.set_readonly(True)

    def set_readonly(self, ro: bool):
        self.en_res_name_val.configure(state='readonly' if ro else 'normal')
        self.en_rec_id.configure(state='readonly' if ro else 'normal')
        self.en_cycle_time.configure(state='readonly' if ro else 'normal')
        self.en_source_name.configure(state='readonly' if ro else 'normal')


class ResQtSelectController(Controller[tuple[ResourceQuantity, float]]):

    def __init__(self, master, c0_name: str):
        self.res_qt: Optional[ResourceQuantities] = None
        self.cycle_time = None
        self.view = ResQtSelect(master, self, c0_name)
        self.listeners_sel_change = []
        self.view.tv_res_quantities.bind('<<TreeviewSelect>>', self.cb_selection_change)

    def update_items(self):
        self.view.tv_res_quantities.delete(*self.view.tv_res_quantities.get_children())

        if self.res_qt is not None:
            rpm_factor = 60.0 / self.cycle_time
            for res_qt in self.res_qt.values():
                self.view.tv_res_quantities.insert('', 'end', iid=res_qt.resource.id,
                                                   values=(res_qt.resource.name, res_qt.quantity, res_qt.quantity * rpm_factor))

    def widget(self) -> tk.Widget:
        return self.view

    def value(self) -> Optional[tuple[ResourceQuantity, float]]:
        selection = self.view.tv_res_quantities.selection()
        if len(selection) > 0 and self.res_qt is not None:
            return self.res_qt[selection[0]], self.cycle_time
        return None

    def set_value(self, val: Optional[tuple[ResourceQuantities, float]]):
        self.res_qt = val[0]
        self.cycle_time = val[1]
        self.update_items()

    def register_selection_change(self, cb: Callable[[tuple[str]], []]):
        self.listeners_sel_change.append(cb)

    def cb_selection_change(self, event):
        print(f'{self}: selected changed to {self.view.tv_res_quantities.selection()} (event={event})')
        for listener in self.listeners_sel_change:
            listener(self.view.tv_res_quantities.selection())

class ResQtSelect(ttk.Frame):

    def __init__(self, master, controller: ResQtSelectController, c0_name: str):
        super().__init__(master)

        row = 0
        self.tv_res_quantities = ttk.Treeview(self, columns=['res_name', 'quantity', 'rpm'], )
        self.tv_res_quantities.configure(show='headings')
        self.tv_res_quantities.heading('res_name', text=c0_name)
        self.tv_res_quantities.heading('quantity', text='Quantity')
        self.tv_res_quantities.heading('rpm', text='RPM')
        self.tv_res_quantities.grid(row=row, column=0)
