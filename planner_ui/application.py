import tkinter as tk
import tkinter.ttk as ttk
import typing

from data import Resource, Recipe
from configuration import MainConfig, GuiConfig
from . import Controller, AppGlobals, add_unimplemented_label
from .entity_select import EntitySelectController
from persistence import RecipeRepository
from .login import LoginController
from .planner import PlannerView, PlannerController
from .recipe_edit import RecipeEditController
from .resource_edit import ResourceEditController


class RootFrame(tk.Frame):

    def __init__(self, master, repository: RecipeRepository):
        super().__init__(master)
        self.repository = repository
        self.view = None
        self.controller = None
        master.title(f'{MainConfig.APP_NAME} {MainConfig.APP_VERSION}')
        self.grid(row=0, column=0, sticky=tk.NSEW)

    def init_login(self, config: GuiConfig):
        self.controller = LoginController(self, 'vw_login', None, config)
        self.view = self.controller.widget()

        self.view.grid(row=0, column=0, sticky=tk.NSEW)
        self.columnconfigure(index=0, weight=1)
        self.rowconfigure(index=0, weight=1)

        self.controller.notify_button_pressed = self.cb_login_pressed


    def init_main_app(self):
        self.controller = None
        self.view = Application(self.repository, master=self)
        self.view.grid(row=0, column=0, sticky=tk.NSEW)

    def cb_login_pressed(self):
        if isinstance(self.controller, LoginController):
            user, workstation = self.controller.value()
            cfg = MainConfig().gui_config
            for known_user in cfg.user_list:
                if known_user.user_id == user:
                    cfg.current_user = known_user
                    break

            for known_ws in cfg.workstation_list:
                if known_ws.hostname == workstation:
                    cfg.current_workstation = known_ws
                    break

            self.init_main_app()


class MainButtons(tk.Frame):

    def __init__(self, master):
        super().__init__(master)
        self.btn_quit = tk.Button(self, text='Quit', command=self.quit)
        self.btn_quit.grid(row=0, column=1)


class Application(tk.Frame):

    def __init__(self, repo: RecipeRepository, master=None):
        super().__init__(master)
        if master is not None:
            AppGlobals.set('validate_id_fmt', master.register(repo.validate_id_format))
        self.repository = repo
        self.nb_editor = ttk.Notebook(self)
        self.resource_edit = ResourceEditController(self.nb_editor, 'res_edit', None, repo)

        self.recipe_editor = RecipeEditController(self.nb_editor, 'recipe_edit', None, repo)
        self.planner = PlannerController(self.nb_editor, 'planner', None, repo)

        self.nb_editor.add(self.resource_edit.widget(), text='Resources', padding=(10, 10), sticky=tk.NSEW)
        self.nb_editor.add(self.recipe_editor.widget(), text='Recipes', padding=(10, 10))
        self.nb_editor.add(self.planner.widget(), text='Planner', padding=(10, 10))
        self.nb_editor.grid(row=0, column=0, padx=10, pady=10, sticky=tk.NSEW)
        self.grid(sticky=tk.NSEW)

        self.main_buttons = MainButtons(self)
        self.main_buttons.grid(row=1, column=0, columnspan=2, sticky=tk.NSEW, padx=10, pady=10)
        
        self.columnconfigure(index=0, weight=1)
        self.rowconfigure(index=0, weight=1)

    def select_entity(self):
        if self.sub_view is not None:
            print(f'SubView: {self.sub_view.value()}')
            self.sub_view.widget().destroy()
            del self.sub_view
            self.sub_view = None
        else:
            controller = EntitySelectController(self, self.repository.recipes)
            self.sub_view = controller
            self.sub_view.widget().grid(row=0, column=1)

def set_productivity_look(style: ttk.Style):
    tv_bg_name = 'LightGoldenrodYellow'
    style.configure("Treeview", background=tv_bg_name, fieldbackground=tv_bg_name)

def main(config: MainConfig):
    root = tk.Tk()
    style = ttk.Style(root)
    if config.theme in style.theme_names():
        style.theme_use(config.theme)

    if config.gui_config.enable_productivity_look:
        set_productivity_look(style)

    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    root_frame = RootFrame(style.master, config.repository)
    if config.gui_config.enable_login:
        root_frame.init_login(config.gui_config)
    else:
        root_frame.init_main_app()

    root.mainloop()
