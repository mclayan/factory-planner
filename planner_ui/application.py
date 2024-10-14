import tkinter as tk
import tkinter.ttk as ttk
import typing

from data import Resource, Recipe
from main import MainConfig
from . import Controller, AppGlobals, add_unimplemented_label
from .entity_select import EntitySelectController
from repository import RecipeRepository
from .planner import Planner, PlannerController
from .recipe_edit import RecipeEditController


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
        frame_res_edit = tk.Frame(self)
        self.resource_select = EntitySelectController(frame_res_edit, 'resource_edit', None, repo, entity_type=Resource,
                                                      show_info=True, is_readonly=False)
        add_unimplemented_label(frame_res_edit)
        self.resource_select.widget().grid(row=1, column=0, sticky=tk.NSEW)
        frame_res_edit.rowconfigure(1, weight=1)
        frame_res_edit.columnconfigure(0, weight=1)

        self.recipe_editor = RecipeEditController(self.nb_editor, 'recipe_edit', None, repo)
        self.planner = PlannerController(self.nb_editor, 'planner', None, repo)

        self.nb_editor.add(frame_res_edit, text='Resources', padding=(10, 10), sticky=tk.NSEW)
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


def main(config: MainConfig):
    root = tk.Tk()
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    app = Application(config.repository, master=root)
    app.master.title(f'Factory Planner {MainConfig.APP_VERSION}')
    root.mainloop()
