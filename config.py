import json
import logging

from repository import RecipeRepository

# thank you, $so/q/6760685 !
class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class GuiSpecialResourceTag:
    __slots__ = ('tag_val', 'display_name', 'col_bg', 'col_fg')


class GuiConfig:

    __slots__ = ('special_resource_tag',)

    def __init__(self):
        self.special_resource_tag = GuiSpecialResourceTag()

    @staticmethod
    def load_file(config_path: str):
        instance = GuiConfig()
        with open(config_path, 'r') as config_file:
            cfg_dict = json.load(config_file)
            res_tag_special = cfg_dict.get('resource_tag_special', dict())
            instance.special_resource_tag.tag_val = res_tag_special.get('tag', None)
            instance.special_resource_tag.display_name = res_tag_special.get('display_name', 'Special Resources')
            instance.special_resource_tag.col_bg = res_tag_special.get('bg', None)
            instance.special_resource_tag.col_fg = res_tag_special.get('fg', None)

        return instance

class MainConfig(metaclass=Singleton):
    APP_VERSION = '2.2.0'

    __slots__ = ('resources_file', 'recipes_file', 'repository', 'theme', 'productivity_look', 'debug', 'gui_config')

    def __init__(self, resources_file: str=None, recipes_file: str=None, repo: RecipeRepository=None, theme=None, gui_config_file=None):
        self.resources_file = resources_file
        self.recipes_file = recipes_file
        self.repository = repo
        self.theme = theme
        self.productivity_look = False
        self.debug = False
        if gui_config_file is not None:
            self.gui_config = GuiConfig.load_file(gui_config_file)
        else:
            self.gui_config = GuiConfig()

    def log_level(self) -> int:
        if self.debug:
            return logging.DEBUG
        else:
            return logging.INFO