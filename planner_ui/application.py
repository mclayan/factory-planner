import tkinter as tk
import tkinter.ttk as ttk
import typing

from data import Resource, Recipe
from main import MainConfig
from . import Controller
from .entity_select import EntitySelectController
from repository import RecipeRepository


class MainButtons(tk.Frame):

    def __init__(self, master):
        super().__init__(master)
        self.btn_quit = tk.Button(self, text='Quit', command=self.quit)
        self.btn_quit.grid(row=0, column=1)


class Application(tk.Frame):
    def __init__(self, repo: RecipeRepository, master=None):
        super().__init__(master)
        self.repository = repo
        self.nb_editor = ttk.Notebook(self)
        self.resource_select = EntitySelectController(self.nb_editor, repo.resources, entity_type=Resource,
                                                      show_info=True)
        self.recipe_select = EntitySelectController(self.nb_editor, repo.recipes, entity_type=Recipe, show_info=True)
        self.nb_editor.add(self.resource_select.widget(), text='Resources', padding=(10, 10), sticky=tk.NSEW)
        self.nb_editor.add(self.recipe_select.widget(), text='Recipes', padding=(10, 10))
        self.nb_editor.grid(row=0, column=0, padx=10, pady=10)
        self.grid()

        self.main_buttons = MainButtons(self)
        self.main_buttons.grid(row=1, column=0, columnspan=2, sticky=tk.NSEW)

        # self.pack()

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
    a = tk.Tk()
    app = Application(config.repository, master=a)
    app.master.title('Sample application')
    a.mainloop()
