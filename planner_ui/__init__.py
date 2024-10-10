import tkinter as tk
from abc import ABC, abstractmethod


__all__ = ['Controller']

class Controller(ABC):

    @abstractmethod
    def widget(self) -> tk.Frame:
        pass

    @abstractmethod
    def value(self):
        pass