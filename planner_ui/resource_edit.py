import typing
from copy import copy

from data import Resource
from planner_ui import RootController, View, T
from planner_ui.entity_select import EntitySelect, EntitySelectController, ResourceAttrController, ResourceAttrView
from repository import RecipeRepository, InvalidDataError, DuplicateKeyError
import tkinter as tk
import tkinter.ttk

class  ResourceEditController(RootController[Resource]):

    def __init__(self, master, v_id: str, parent: typing.Optional[typing.Self], repository: RecipeRepository):
        super().__init__(v_id, parent, repository)
        self.entity_tmp: typing.Optional[Resource] = None
        self.view = ResourceEditView(master, self)
        self.ctl_resource_sel = EntitySelectController(self.view, 'resource_sel', self, repository, Resource, show_info=False, is_readonly=False)
        self.ctl_resource_attr = ResourceAttrController(self.view, 'res_attributes', self, False, 'Attributes')
        self.view.init_components(self.ctl_resource_sel.widget(), self.ctl_resource_attr.widget())

        self.ctl_resource_sel.register_cb_sel_change(self.cb_res_sel_changed)
        self.ctl_resource_attr.register_attr_change(self.cb_attr_changed)

    def init_tmp(self):
        if self.entity_tmp is None:
            self.entity_tmp = Resource(EntitySelectController.DUMMY_NAME, EntitySelectController.DUMMY_ID, False)
            self.ctl_resource_sel.add_dummy(self.entity_tmp)
            self.ctl_resource_sel.update_entities()
            self.view.btn_add.configure(state='disabled')

    def end_tmp(self):
        if self.entity_tmp is not None:
            self.entity_tmp = None
            self.ctl_resource_sel.set_value(None)
            self.ctl_resource_sel.remove_dummy()
            self.ctl_resource_sel.update_entities()
            self.ctl_resource_attr.set_value(None)
            self.view.btn_add.configure(state='normal')


    def write_tmp(self):
        if self.entity_tmp is not None:
            tmp = self.entity_tmp
            tmp.name   = self.ctl_resource_attr.var_name.get()
            tmp.id     = self.ctl_resource_attr.var_entity_id.get()
            tmp.is_raw = self.ctl_resource_attr.var_is_raw.get()
            try:
                #print(f'writing tmp: {tmp}')
                if self.repository.add_resource(tmp, False):
                    self.notify_entities_changed(Resource)
                self.end_tmp()
            except InvalidDataError or DuplicateKeyError as e:
                if isinstance(e, DuplicateKeyError):
                    self.set_attr_invalid('id')
                elif isinstance(e, InvalidDataError):
                    self.set_attr_invalid(e.part)

    def update_resource(self, resource: Resource) -> bool:
        try:
            orig_id = self.ctl_resource_sel.value().id
            self.repository.update_entity(orig_id, resource)
            self.notify_entities_changed(Resource)
            return True
        except Exception as e:
            self.logger.error(f'failed to update resource {resource}:\n{e}')
            return False


    def set_attr_invalid(self, attr: str):
        compo = None
        if attr == 'name':
            compo = self.ctl_resource_attr.view.en_source_name
        elif attr == 'id':
            compo = self.ctl_resource_attr.view.en_res_id
        if compo is not None:
            compo.configure(state='invalid')

    def cb_btn_add(self):
        self.init_tmp()

    def cb_btn_save(self):
        if self.ctl_resource_attr.is_mod:
            entity = self.ctl_resource_sel.value()
            if isinstance(entity, Resource):
                if entity == self.entity_tmp:
                    self.entity_tmp = self.ctl_resource_attr.value_updated()
                    self.write_tmp()
                    self.ctl_resource_attr.set_value(None)
                else:
                    if self.update_resource(self.ctl_resource_attr.value_updated()):
                        self.view.btn_save.configure(state='disabled')
                        self.ctl_resource_attr.set_value(None)


    def cb_res_sel_changed(self, entity):
        #print(f'{self}: resource selection changed to {entity}')
        if isinstance(entity, Resource):
            if entity == self.entity_tmp and self.entity_tmp is not None:
                self.view.btn_save.configure(state='normal')
            else:
                self.view.btn_save.configure(state='disabled')
            self.ctl_resource_attr.set_value(copy(entity))
            self.view.btn_del.configure(state='normal')
        elif entity is None:
            self.view.btn_del.configure(state='disabled')
            self.view.btn_save.configure(state='disabled')
            self.ctl_resource_attr.set_value(None)

    def cb_btn_del(self):
        selected = self.ctl_resource_sel.value()
        #print(f'{self}: delete called for resource {selected}')
        if selected is not None:
            if selected == self.entity_tmp:
                self.end_tmp()
            elif selected.id in self.repository.resources:
                self.repository.delete_resource(selected.id)
                self.notify_entities_changed(Resource)

    def cb_attr_changed(self, is_mod: bool):
        if is_mod:
            self.view.btn_save.configure(state='normal')
            if self.ctl_resource_attr.entity == self.entity_tmp:
                self.entity_tmp.name = self.ctl_resource_attr.var_name.get()
                self.entity_tmp.id = self.ctl_resource_attr.var_entity_id.get()
                self.entity_tmp.is_raw = self.ctl_resource_attr.var_is_raw.get()
        else:
            self.view.btn_save.configure(state='disabled')


    def widget(self) -> 'ResourceEditView':
        return self.view

    def value(self) -> typing.Optional[Resource]:
        return None

    def set_value(self, val: T):
        pass



class ResourceEditView(tk.Frame, View):

    def __init__(self, master, controller: ResourceEditController):
        View.__init__(self, controller)
        super().__init__(master)

        self.vw_resource_select: typing.Optional[EntitySelect] = None
        self.vw_resource_attr: typing.Optional[ResourceAttrView] = None
        self.frm_buttons: typing.Optional[tk.Frame] = None

        self.btn_add  : typing.Optional[tk.Button]= None
        self.btn_del  : typing.Optional[tk.Button]= None
        self.btn_save : typing.Optional[tk.Button]= None
        self.rowconfigure(0, weight=2)
        self.columnconfigure(0, weight=2)
        self.columnconfigure(1, weight=1)

    def init_components(self, res_sel: EntitySelect, res_attr: ResourceAttrView):
        self.vw_resource_select = res_sel
        self.vw_resource_select.grid(row=0, column=0, sticky=tk.NSEW, padx=10, pady=10)

        self.frm_buttons = tk.Frame(res_sel)
        self.frm_buttons.grid(row=1, column=0, sticky=tk.NSEW, padx=10, pady=10)

        self.btn_add = tk.Button(self.frm_buttons, text='Add', command=self.controller.cb_btn_add)
        self.btn_add.grid(row=1, column=0)
        self.btn_del = tk.Button(self.frm_buttons, text='Delete', state='disabled', command=self.controller.cb_btn_del)
        self.btn_del.grid(row=1, column=1)
        self.btn_save = tk.Button(self.frm_buttons, text='Save', state='disabled', command=self.controller.cb_btn_save)
        self.btn_save.grid(row=1, column=2)

        self.vw_resource_attr = res_attr
        self.vw_resource_attr.grid(row=0, column=1, sticky=tk.NSEW, padx=10, pady=10)


