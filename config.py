class MainConfig:
    APP_VERSION = '2.0.0'

    __slots__=('resources_file','recipes_file','repository','theme','productivity_look')

    def __init__(self, resources_file, recipes_file, repo, theme):
        self.resources_file = resources_file
        self.recipes_file = recipes_file
        self.repository = repo
        self.theme = theme
        self.productivity_look = False
