from repository import RecipeRepository


class MainConfig:
    APP_VERSION = '2.0.0'

    __slots__ = ('resources_file', 'recipes_file', 'repository', 'theme', 'productivity_look', 'debug')

    def __init__(self, resources_file: str, recipes_file: str, repo: RecipeRepository, theme):
        self.resources_file = resources_file
        self.recipes_file = recipes_file
        self.repository = repo
        self.theme = theme
        self.productivity_look = False
        self.debug = False
