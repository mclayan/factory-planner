import copy
import tkinter as tk
import tkinter.ttk as ttk
import typing
from abc import ABC, abstractmethod
from collections.abc import Callable
from tkinter import StringVar
from typing import Optional

from data import Entity, Recipe, Resource, ResourceQuantity, ResourceQuantities
from repository import RecipeRepository
from . import T, RootController, View

from .application import Controller

__all__ = ['EntitySelectController', 'EntitySelect', 'EntityMultiSelectController']


class ResourceInfoVars:

    def __init__(self):
        self.is_raw = tk.BooleanVar()


class RecipeInfoVars:

    def __init__(self):
        self.products = tk.StringVar()
        self.resources = tk.StringVar()
        self.source_name = tk.StringVar()


class EntitySelectController(RootController[Entity]):
    DUMMY_NAME = '<<new>>'
    DUMMY_ID = '<<dummy_id>>'

    def __init__(self, master, view_name: str, parent: typing.Optional[Controller], repository: RecipeRepository,
                 entity_type: type, label_text=None, show_info=False, is_readonly=True, id_filter: typing.Optional[list[str]]=None):
        super().__init__(view_name, parent, repository)
        self.id_filter = id_filter
        self.entity_type = entity_type
        self.entity_source = self.repository.resources if issubclass(self.entity_type,
                                                                     Resource) else self.repository.recipes
        self.dummy_entity: typing.Optional[Entity] = None
        self.var_entities = tk.StringVar()
        self.repository = repository
        self.listeners_attr_change = []
        self.listeners_sel_change = []

        if label_text is None:
            label_text = 'Resource' if entity_type is Resource else 'Recipe'

        self.view = EntitySelect(master, self, label_text)
        self.update_entities()
        self.entity_attr_controller = None

        if show_info:
            if issubclass(entity_type, Resource):
                self.entity_attr_controller = ResourceAttrController(self.view, 'resources', self, is_readonly)
                self.view.init_info(self.entity_attr_controller.widget())
            elif issubclass(entity_type, Recipe):
                self.entity_attr_controller = RecipeAttrController(self.view, 'recipes', self, is_readonly)
                self.view.init_info(self.entity_attr_controller.widget())

        self.register_entities_changed(self.update_entities, entity_type)

    def update_entities(self):
        self.clear_display()
        for e_id, entity in self.entity_source.items():
            if self.id_filter is not None:
                if not e_id in self.id_filter:
                    continue
            self.view.tv_entities.insert('', 'end', id=e_id, text=entity.name)
        if self.dummy_entity is not None:
            self.view.tv_entities.insert('', 'end', iid=self.dummy_entity.id, text=self.dummy_entity.name)

    def add_dummy(self, entity: Entity):
        if self.dummy_entity is None:
            self.dummy_entity = entity
            if self.dummy_entity.id in self.entity_source:
                self.dummy_entity.id = self.DUMMY_ID

    def remove_dummy(self) -> typing.Optional[Entity]:
        entity = None
        if self.dummy_entity is not None:
            entity = self.dummy_entity
            self.dummy_entity = None
        return entity

    def cb_select_entity(self, event):
        selected_entity = self.selected()
        if selected_entity is not None:
            if self.entity_attr_controller is not None:
                self.entity_attr_controller.update_entity(copy.copy(self.selected()))
        for listener in self.listeners_sel_change:
            listener(selected_entity)

    def cb_attr_change(self, is_mod):
        for listener in self.listeners_attr_change:
            listener(is_mod)

    def register_cb_attr_change(self, cb: Callable[[bool], []]):
        self.listeners_attr_change.append(cb)
        if self.entity_attr_controller is not None:
            self.entity_attr_controller.register_attr_change(cb)

    def register_cb_sel_change(self, cb: Callable[[Optional[Entity]], []]):
        self.listeners_sel_change.append(cb)

    def selected(self) -> typing.Optional[Recipe | Resource]:
        sel_id = self.view.tv_entities.selection()
        if len(sel_id) > 0:
            if sel_id[0] in self.entity_source:
                return self.entity_source.get(sel_id[0])
            elif self.dummy_entity is not None and self.dummy_entity.id == sel_id[0]:
                return self.dummy_entity

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
        items = self.view.tv_entities.get_children()
        self.view.tv_entities.delete(*items)

    def set_value(self, val: Optional[Entity | str]):
        if isinstance(val, str):
            sel_id = val
        elif val is None:
            self.view.tv_entities.selection_clear()
            return
        else:
            sel_id = None
            if type(val) != self.entity_type:
                print(f'WARN: set_value called with type={type(val)} but controller manages type={self.entity_type}!')
                return
            elif val.id in self.entity_source:
                sel_id = val.id
            elif self.dummy_entity is not None and self.dummy_entity.id == val.id:
                sel_id = self.dummy_entity.id
        if sel_id is None:
            print(f'WARN: requested item "{val}" is not in repository!')
        else:
            self.view.tv_entities.selection_set(sel_id)
            self.view.tv_entities.see(sel_id)

    def validate_id(self, entity_id: str) -> bool:
        try:
            if self.repository.validate_id_format(entity_id):
                if entity_id != self.entity_attr_controller.entity.id:
                    return entity_id not in self.entity_source
            else:
                return False
        except Exception as e:
            print(f'ERROR: {e}')
            raise e


class EntitySelect(ttk.Labelframe, View):
    def __init__(self, master, controller: EntitySelectController, label_text: str):
        View.__init__(self, controller)
        super().__init__(master=master, text=label_text, padding=(4, 4))
        self.tv_entities = ttk.Treeview(self)
        self.tv_entities.bind('<<TreeviewSelect>>', self.controller.cb_select_entity)
        self.tv_entities.grid(row=0, column=0, sticky=tk.NSEW, padx=10, pady=10)
        self.columnconfigure(0, weight=2)
        self.rowconfigure(0, weight=2)
        self.info_view = None

    def init_info(self, info_view: tk.Widget):
        self.info_view = info_view
        self.info_view.grid(row=0, column=1, sticky=tk.NSEW, padx=10, pady=10)
        self.columnconfigure(1, weight=1)



class EntityMultiSelectController(EntitySelectController):
    _NONE_ID = '__NONE_ID__'
    _NONE_NAME = '-----None-----'

    def __init__(self, master, view_name: str, parent: typing.Optional[Controller], repository: RecipeRepository,
                 entity_type: type, label_text=None, is_readonly=True,
                 id_filter: typing.Optional[list[str]] = None):

        super().__init__(master, view_name, parent, repository, entity_type, label_text, False, is_readonly, id_filter)
        self.view.tv_entities.configure(selectmode='extended')
        self.update_entities()
        self.view.tv_entities.selection_set((self._NONE_ID,))

    def update_entities(self):
        self.clear_display()
        self.view.tv_entities.insert('', 'end', id=self._NONE_ID, text=self._NONE_NAME)
        for e_id, entity in self.entity_source.items():
            if self.id_filter is not None:
                if not e_id in self.id_filter:
                    continue
            self.view.tv_entities.insert('', 'end', id=e_id, text=entity.name)

    def selected(self) -> list[Entity]:
        entities = []
        for selection in self.view.tv_entities.selection():
            if selection != self._NONE_ID:
                entities.append(self.entity_source.get(selection))
        return entities

    def value(self) -> list[Entity]:
        return self.selected()

class EntityInfo(Controller[T], ABC):

    def __init__(self, view_name: str, parent: typing.Optional[Controller], is_readonly: bool):
        super().__init__(view_name, parent)
        self.read_only = is_readonly
        self.listeners_attr_change = []
        self.var_entity_id = StringVar()

    def register_attr_change(self, cb: Callable[[bool], []]):
        self.listeners_attr_change.append(cb)

    def cb_attr_change(self, *args):
        #print(f'{self}: text changed: {args}')
        for listener in self.listeners_attr_change:
            listener()

    @abstractmethod
    def reset_flags(self):
        pass

    def value_updated(self) -> typing.Optional[T]:
        pass


class ResourceAttrController(EntityInfo[Resource]):

    def __init__(self, master, view_name: str, parent: typing.Optional[Controller], is_readonly: bool, label_text=None):
        super().__init__(view_name, parent, is_readonly)
        self.var_is_raw = tk.BooleanVar()
        self.var_name = tk.StringVar()
        self.entity: typing.Optional[Resource] = None
        self.view = ResourceAttrView(master, self, label_text)
        self.listeners_attr_change = []
        change_cb_id = master.register(lambda args: self.cb_attr_change('id', args))
        change_cb_name = master.register(lambda args: self.cb_attr_change('name', args))
        self.view.en_res_id.configure(validate='key', validatecommand=(change_cb_id, '%P'))
        self.view.en_res_name_val.configure(validate='key', validatecommand=(change_cb_name, '%P'))
        self.view.ckb_is_raw.configure(command=lambda: self.cb_attr_change('ir'))
        self.is_valid_id = True
        self.is_mod = False

    def update_entity(self, new_val: typing.Optional[Resource]):
        if isinstance(new_val, Resource):
            self.reset_flags()
            self.entity = new_val
            self.var_is_raw.set(new_val.is_raw)
            self.var_name.set(new_val.name)
            self.var_entity_id.set(new_val.id)
        elif new_val is None:
            self.reset_flags()
            self.entity = None
            self.var_name.set('')
            self.var_entity_id.set('')
            self.var_is_raw.set(False)
        else:
            print(f'WARN: {self}: invalid value for this type: {new_val}')

    def register_attr_change(self, cb: Callable):
        self.listeners_attr_change.append(cb)

    def cb_attr_change(self, src: typing.Literal['id', 'name', 'ir'], *args):
        if self.entity is not None:
            differs = False
            if src == 'id' and args[0] != self.entity.id:
                differs = self.cb_id_val_change(args[0])
                if differs != self.is_mod:
                    self.is_mod = differs or (self.entity.name != self.var_name.get() or self.entity.is_raw != self.var_is_raw.get())
            elif src == 'name':
                differs = self.entity.name != args[0]
                if differs != self.is_mod:
                    self.is_mod = differs or (self.entity.id != self.var_entity_id.get() or self.entity.is_raw != self.var_is_raw.get())
            elif src == 'ir':
                differs = self.entity.is_raw != self.var_is_raw.get()
                if differs != self.is_mod:
                    self.is_mod = differs or (self.entity.id != self.var_entity_id.get() or self.entity.name != self.var_name.get())
            for listener in self.listeners_attr_change:
                listener(self.is_mod)

        return True

    def cb_id_val_change(self, new_val) -> bool:
        if new_val != self.entity.id:
            if not RecipeRepository.validate_id_format(new_val):
                if self.is_valid_id:
                    self.view.en_res_id['bg'] = '#ff7777'
                    self.is_valid_id = False
            else:
                if not self.is_valid_id:
                    self.is_valid_id = True
                    self.view.en_res_id['bg'] = self.view.col_en_orig
            return True
        else:
            if not self.is_valid_id:
                self.is_valid_id = True
                self.view.en_res_id['bg'] = self.view.col_en_orig
            return False


    def widget(self) -> 'ResourceAttrView':
        return self.view

    def value(self) -> Resource:
        return self.entity

    def set_value(self, val: typing.Optional[Resource]):
        self.update_entity(val)

    def reset_flags(self):
        self.is_mod = False
        self.is_valid_id = True
        self.view.en_res_id['bg'] = self.view.col_en_orig

    def value_updated(self) -> typing.Optional[T]:
        if self.is_mod:
            updated = copy.copy(self.entity)
            updated.name = self.var_name.get()
            updated.id = self.var_entity_id.get()
            updated.is_raw = self.var_is_raw.get()
            return updated
        else:
            return None


class ResourceAttrView(ttk.Labelframe, View):

    def __init__(self, master, controller: ResourceAttrController, label_text=None):
        View.__init__(self, controller)
        super().__init__(master, text=label_text if label_text is not None else 'Resource Data')
        row = 0

        self.lbl_res_name = tk.Label(self, text='Name')
        self.lbl_res_name.grid(row=row, column=0, sticky=tk.W, padx=10)

        self.en_res_name_val = tk.Entry(self, textvariable=controller.var_name)
        self.en_res_name_val.grid(row=row, column=1, sticky=tk.EW, padx=10)
        row += 1

        self.lbl_res_id = tk.Label(self, text='Recipe ID')
        self.lbl_res_id.grid(row=row, column=0, sticky=tk.W, padx=10)

        self.en_res_id = tk.Entry(self, textvariable=controller.var_entity_id)
        self.en_res_id.grid(row=row, column=1, sticky=tk.EW, padx=10)
        row += 1

        self.ckb_is_raw = tk.Checkbutton(self, text='Raw Resource', variable=controller.var_is_raw)
        self.ckb_is_raw.grid(row=row, column=1, sticky=tk.W, padx=10)
        row += 1

        if controller.read_only:
            self.set_readonly(True)

        self.col_en_orig = self.en_res_id['bg']
        self.columnconfigure(1, weight=1)

    def set_readonly(self, ro: bool):
        self.en_res_name_val.configure(state='readonly' if ro else 'normal')
        self.en_res_id.configure(state='readonly' if ro else 'normal')
        self.ckb_is_raw.configure(state='disabled' if ro else 'normal')


class RecipeAttrController(EntityInfo[Recipe]):

    def __init__(self, master, name: str, parent: Controller, is_readonly: bool, label_text=None):
        super().__init__(name, parent, is_readonly)
        self.is_mod = False
        self.var_name = tk.StringVar()
        self.var_id = tk.StringVar()
        self.var_cycle_time = tk.DoubleVar()
        self.var_source_name = tk.StringVar()
        self.entity: typing.Optional[Recipe] = None
        self.entity_id: typing.Optional[str] = None
        self.view = RecipeInfo(master, self, label_text)
        validation_cb_id = master.register(lambda args: self.cb_attr_change('id', args))
        validation_cb_name = master.register(lambda args: self.cb_attr_change('name', args))
        validation_cb_src_name = master.register(lambda args: self.cb_attr_change('sname', args))
        validation_cb_ctime = master.register(lambda args: self.cb_attr_change('ctime', args))
        self.view.en_rec_id.configure(validate='key', validatecommand=(validation_cb_id, '%P'))
        self.view.en_res_name_val.configure(validate='key', validatecommand=(validation_cb_name, '%P'))
        self.view.en_source_name.configure(validate='key', validatecommand=(validation_cb_src_name, '%P'))
        self.view.en_cycle_time.configure(validate='key', validatecommand=(validation_cb_ctime, '%P'))
        self.is_valid_id = True

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

    def cb_attr_change(self, src: typing.Literal['id', 'name', 'sname', 'ctime'], *args):
        differs = False
        if src == 'id':
            differs = self.cb_id_val_change(args[0])
        elif src == 'name':
            differs = self.entity.name != args[0]
        elif src == 'sname':
            differs = self.entity.source_name != args[0]
        elif src == 'ctime':
            differs = self.entity.cycle_time != float(args[0])
        if not differs:
            differs = (self.entity.name == self.var_name.get()
                       and self.entity.id == self.var_entity_id.get()
                       and self.entity.source_name == self.var_source_name.get()
                       and self.entity.cycle_time == self.var_cycle_time.get())
        for listener in self.listeners_attr_change:
            listener(differs)

        return True

    def cb_id_val_change(self, new_val) -> bool:
        if new_val != self.entity.id:
            if not RecipeRepository.validate_id_format(new_val):
                if self.is_valid_id:
                    self.view.en_rec_id['bg'] = '#ff7777'
                    self.is_valid_id = False
            else:
                if not self.is_valid_id:
                    self.is_valid_id = True
                    self.view.en_rec_id['bg'] = self.view.col_en_orig
            return True
        else:
            if not self.is_valid_id:
                self.is_valid_id = True
                self.view.en_rec_id['bg'] = self.view.col_en_orig
            return False

    def widget(self) -> ttk.Labelframe:
        return self.view

    def value(self) -> Recipe:
        return self.entity

    def set_value(self, val: Recipe):
        self.update_entity(val)

    def reset_flags(self):
        self.is_valid_id = True


class RecipeInfo(ttk.Labelframe, View):

    def __init__(self, master, controller: RecipeAttrController, label_text=None):
        View.__init__(self, controller)
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

        self.col_en_orig = self.en_rec_id['bg']

    def set_readonly(self, ro: bool):
        self.en_res_name_val.configure(state='readonly' if ro else 'normal')
        self.en_rec_id.configure(state='readonly' if ro else 'normal')
        self.en_cycle_time.configure(state='readonly' if ro else 'normal')
        self.en_source_name.configure(state='readonly' if ro else 'normal')


class ResQtSelectController(Controller[tuple[ResourceQuantity, float]]):

    def __init__(self, master, view_name: str, parent: typing.Optional[Controller], c0_name: str):
        super().__init__(view_name, parent)
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
                                                   values=(
                                                       res_qt.resource.name, res_qt.quantity,
                                                       res_qt.quantity * rpm_factor))

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
        #print(f'{self}: selected changed to {self.view.tv_res_quantities.selection()} (event={event})')
        for listener in self.listeners_sel_change:
            listener(self.view.tv_res_quantities.selection())


class ResQtSelect(ttk.Frame, View):

    def __init__(self, master, controller: ResQtSelectController, c0_name: str):
        View.__init__(self, controller)
        super().__init__(master)

        row = 0
        self.tv_res_quantities = ttk.Treeview(self, columns=['res_name', 'quantity', 'rpm'], )
        self.tv_res_quantities.configure(show='headings')
        self.tv_res_quantities.heading('res_name', text=c0_name)
        self.tv_res_quantities.heading('quantity', text='Quantity')
        self.tv_res_quantities.heading('rpm', text='RPM')
        self.tv_res_quantities.grid(row=row, column=0, sticky=tk.NSEW)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
