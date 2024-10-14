import tkinter as tk
from abc import ABC, abstractmethod
import typing

__all__ = ['Controller', 'RootController', 'T']

from repository import RecipeRepository

T = typing.TypeVar('T')


class AppGlobals:
    __VALS = dict()

    @staticmethod
    def get(item):
        return AppGlobals.__VALS.__getitem__(item)

    @staticmethod
    def set(key, value):
        AppGlobals.__VALS.__setitem__(key, value)

class ViewIdException(Exception):

    def __init__(self, v_id: 'ViewId'):
        super().__init__()
        self.v_id = v_id


class ViewId:

    def __init__(self, parent: typing.Optional[typing.Self], name: str):
        self.parent = parent
        self.name = name

    def __str__(self):
        parent = self.parent if self.parent is not None else '<root>'
        return f'{parent}.{self.name}'

    def str_view(self) -> str:
        return f'{self}[v]'

    def str_ctl(self) -> str:
        return f'{self}[c]'


class Controller(typing.Generic[T], ABC):
    __INSTANCES = dict()


    def __init__(self, v_id: str, parent: typing.Optional[typing.Self]):
        view_id = ViewId(parent.view_id if parent is not None else None, v_id)
        id_str = str(view_id)
        if id_str in self.__INSTANCES:
            raise ViewIdException(view_id)
        self.__INSTANCES[id_str] = self
        self.view_id = view_id

    @abstractmethod
    def widget(self) -> tk.Widget:
        pass

    @abstractmethod
    def value(self) -> typing.Optional[T]:
        pass

    @abstractmethod
    def set_value(self, val: T):
        pass

    def __repr__(self):
        return f'{type(self).__name__}[{self.view_id.str_ctl()}]'


class RootController(Controller[T], ABC):

    def __init__(self, v_id: str, parent: typing.Optional[typing.Self], repository: RecipeRepository):
        super().__init__(v_id, parent)
        self.repository = repository


class View(ABC):

    def __init__(self, controller):
        self.controller = controller
        self.view_id = controller.view_id

    def __repr__(self):
        return f'{type(self).__name__}[{self.view_id.str_view()}]'

def add_unimplemented_label(master):
    lbl_warn_stub = tk.Label(master, text='Info: at the moment modifications will have no affect.')
    font_lbl = tk.font.Font(font=lbl_warn_stub['font'])
    font_lbl['slant'] = 'italic'
    font_lbl['size'] = int(font_lbl['size'] * 1.2)
    lbl_warn_stub.configure(font=font_lbl, background='#ffff98')
    lbl_warn_stub.grid(row=0, column=0, columnspan=2, sticky=tk.NSEW)