import tkinter as tk
import tkinter.ttk as ttk
import typing
from abc import ABC, abstractmethod

from data import Entity, Recipe, Resource

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


class EntitySelectController(Controller):

    def __init__(self, master, entities: dict[str, Entity], entity_type: type, label_text=None, show_info=False):
        self.entity_type = entity_type
        self.entity_source = entities
        self.var_entities = tk.StringVar()

        if label_text is None:
            label_text = 'Resource' if entity_type is Resource else 'Recipe'
        self.view = EntitySelect(master, self, label_text)
        self.items = ([], [])
        self.update_entities()

        if show_info:
            if issubclass(entity_type, Resource):
                self.info_controller = ResourceInfoController(self.view, self, False)
                self.view.init_info(self.info_controller.widget())
            elif issubclass(entity_type, Recipe):
                self.info_controller = RecipeInfoController(self.view, self, False)
                self.view.init_info(self.info_controller.widget())

    def update_entities(self):
        for e_id, entity in self.entity_source.items():
            self.items[0].append(e_id)
            self.items[1].append(entity.get_name())
        self.var_entities.set(self.items[1])

    def cb_select_entity(self, event):
        self.info_controller.update_entity()

    def selected(self) -> typing.Optional[Recipe | Resource]:
        sel_ind = self.view.lb_entities.curselection()
        if sel_ind is not None and len(sel_ind) > 0:
            entity_id = self.items[0][sel_ind[0]]
            return self.entity_source.get(entity_id, None)
        else:
            return None

    def widget(self):
        return self.view

    def value(self):
        return self.selected()


class EntitySelect(ttk.Labelframe):

    def __init__(self, master, controller: EntitySelectController, label_text: str):
        super().__init__(master=master, text=label_text, padding=(4,4))
        self.controller = controller
        self.lb_entities = tk.Listbox(self, listvariable=self.controller.var_entities)
        self.lb_entities.bind('<<ListboxSelect>>', self.controller.cb_select_entity)
        self.lb_entities.grid(row=0, column=0, sticky=tk.NSEW, padx=10, pady=10)
        self.info_view = None

    def init_info(self, info_view: tk.Frame):
        self.info_view = info_view
        self.info_view.grid(row=0, column=1, sticky=tk.NSEW, padx=10, pady=10)


class EntityInfo(Controller, ABC):

    def __init__(self, res_controller: Controller, is_readonly: bool):
        self.res_controller = res_controller
        self.read_only = is_readonly


class ResourceInfoController(EntityInfo):

    def __init__(self, master, res_controller: Controller, is_readonly: bool, label_text=None):
        super().__init__(res_controller, is_readonly)
        self.var_is_raw = tk.BooleanVar()
        self.var_name = tk.StringVar()
        self.var_id = tk.StringVar()
        self.entity = None
        self.res_controller = res_controller
        self.view = ResourceInfo(master, self, label_text)

    def update_entity(self):
        new_val = self.res_controller.value()
        if isinstance(new_val, Resource):
            self.entity = new_val
            self.var_is_raw.set(new_val.is_raw)
            self.var_name.set(new_val.name)
            self.var_id.set(new_val.id)
        else:
            print(f'WARN: {self}: invalid value for this type: {new_val}')

    def widget(self) -> tk.Frame:
        return self.view

    def value(self) -> Resource:
        return self.entity


class ResourceInfo(ttk.Labelframe):

    def __init__(self, master, controller: ResourceInfoController, label_text=None):
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


class RecipeInfoController(EntityInfo):

    def __init__(self, master, res_controller: Controller, is_readonly: bool, label_text=None):
        super().__init__(res_controller, is_readonly)
        self.var_name = tk.StringVar()
        self.var_id = tk.StringVar()
        self.var_products = tk.StringVar()
        self.var_resources = tk.StringVar()
        self.var_cycle_time = tk.DoubleVar()
        self.var_source_name = tk.StringVar()
        self.products = ([], [])
        self.resources = ([], [])
        self.entity = None
        self.view = RecipeInfo(master, self, label_text)

    def update_entity(self):
        new_val = self.res_controller.value()
        if isinstance(new_val, Recipe):
            self.entity = new_val
            self.var_name.set(new_val.name)
            self.var_id.set(new_val.id)
            self.var_cycle_time.set(new_val.cycle_time)
            self.var_source_name.set(new_val.source_name if new_val.source_name is not None else '')
            self.products = ([], [])
            self.resources = ([], [])
            for e_id, entity in new_val.products.pairs():
                self.products[0].append(e_id)
                self.products[1].append(entity.resource.name)

            self.var_products.set(self.products[1])
            for e_id, entity in new_val.resources.pairs():
                self.resources[0].append(e_id)
                self.resources[1].append(entity.resource.name)
            self.var_resources.set(self.resources[1])
            if len(self.resources[0]) > 0:
                self.view.en_source_name.configure(state='readonly')
            elif not self.read_only:
                self.view.en_source_name.configure(state='normal')
        else:
            print(f'WARN: {self}: invalid value for this type: {new_val}')

    def widget(self) -> tk.Frame:
        return self.view

    def value(self) -> Resource:
        return self.entity


class RecipeInfo(ttk.Labelframe):

    def __init__(self, master, controller: RecipeInfoController, label_text=None):
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

        self.lb_resources = tk.Listbox(self, listvariable=controller.var_resources)
        self.lb_resources.grid(row=row, column=0, sticky=tk.EW)

        self.lb_products = tk.Listbox(self, listvariable=controller.var_products)
        self.lb_products.grid(row=row, column=1, sticky=tk.EW)
        row += 1

        if controller.read_only:
            self.set_readonly(True)

    def set_readonly(self, ro: bool):
        self.en_res_name_val.configure(state='readonly' if ro else 'normal')
        self.en_rec_id.configure(state='readonly' if ro else 'normal')
        self.en_cycle_time.configure(state='readonly' if ro else 'normal')
        self.en_source_name.configure(state='readonly' if ro else 'normal')
