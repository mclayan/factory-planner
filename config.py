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


class GuiWsInfo:

    def __init__(self, hostname: str = '', location_code: str = ''):
        self.hostname = hostname
        self.location_code = location_code


class GuiUserInfo:

    def __init__(self, name: str = '', user_id: str = '', department: str = ''):
        self.name = name
        self.user_id = user_id
        self.department = department


class GuiConfig:
    __slots__ = ('enable_login', 'enable_productivity_look', 'special_resource_tag', 'current_user', 'current_workstation', 'user_list', 'workstation_list')

    def __init__(self):
        self.enable_login = False
        self.enable_productivity_look = False
        self.special_resource_tag = GuiSpecialResourceTag()
        self.current_user = None
        self.current_workstation = None
        self.user_list: list[GuiUserInfo] = []
        self.workstation_list: list[GuiWsInfo] = []

    @staticmethod
    def load_file(config_path: str):
        instance = GuiConfig()
        with open(config_path, 'r') as config_file:
            cfg_dict: dict = json.load(config_file)
            res_tag_special = cfg_dict.get('resource_tag_special', dict())

            if 'enable_login' in cfg_dict:
                instance.enable_login = cfg_dict.get('enable_login')
            instance.enable_productivity_look = cfg_dict.get('enable_productivity_look', False)

            instance.special_resource_tag.tag_val = res_tag_special.get('tag', None)
            instance.special_resource_tag.display_name = res_tag_special.get('display_name', 'Special Resources')
            instance.special_resource_tag.col_bg = res_tag_special.get('bg', None)
            instance.special_resource_tag.col_fg = res_tag_special.get('fg', None)
            if 'users' in cfg_dict:
                user_list = cfg_dict.get('users', [])
                for user_dict in user_list:
                    user_info = GuiUserInfo(user_dict.get('name', ''), user_dict.get('id', ''),
                                            user_dict.get('department', ''))
                    instance.user_list.append(user_info)
            if 'workstations' in cfg_dict:
                ws_list = cfg_dict.get('workstations', [])
                for ws_dict in ws_list:
                    ws_info = GuiWsInfo(ws_dict.get('hostname', ''), ws_dict.get('location_code', ''))
                    instance.workstation_list.append(ws_info)

        return instance


class MainConfig(metaclass=Singleton):
    APP_VERSION = '2.2.0'
    APP_NAME = 'Factory Planner'

    __slots__ = ('resources_file', 'recipes_file', 'repository', 'theme', 'productivity_look', 'debug', 'gui_config')

    def __init__(self, resources_file: str = None, recipes_file: str = None, repo: RecipeRepository = None, theme=None,
                 gui_config_file=None):
        self.resources_file = resources_file
        self.recipes_file = recipes_file
        self.repository = repo
        self.theme = theme
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
