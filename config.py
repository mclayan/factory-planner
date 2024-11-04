import logging

from repository import RecipeRepository

# thank you, $so/q/6760685 !
class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class MainConfig(metaclass=Singleton):
    APP_VERSION = '2.1.0'

    __slots__ = ('resources_file', 'recipes_file', 'repository', 'theme', 'productivity_look', 'debug')

    def __init__(self, resources_file: str=None, recipes_file: str=None, repo: RecipeRepository=None, theme=None):
        self.resources_file = resources_file
        self.recipes_file = recipes_file
        self.repository = repo
        self.theme = theme
        self.productivity_look = False
        self.debug = False

    def log_level(self) -> int:
        if self.debug:
            return logging.DEBUG
        else:
            return logging.INFO