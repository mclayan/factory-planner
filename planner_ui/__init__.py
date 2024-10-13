import tkinter as tk
from abc import ABC, abstractmethod
import typing

__all__ = ['Controller', 'RootController', 'T']

from repository import RecipeRepository

T = typing.TypeVar('T')


class Controller(typing.Generic[T], ABC):

    @abstractmethod
    def widget(self) -> tk.Widget:
        pass

    @abstractmethod
    def value(self) -> typing.Optional[T]:
        pass

    @abstractmethod
    def set_value(self, val: T):
        pass


class RootController(Controller[T], ABC):

    def __init__(self, repository: RecipeRepository):
        self.repository = repository
