import logging
import tkinter as tk
import typing
from tkinter import ttk as ttk
from warnings import deprecated

import chaining
import configuration
import data
import persistence
from planner_ui import RootController, View, T, Controller
from persistence import RecipeRepository, ProdAssocRepository


class AltSelections:

    def __init__(self, sel: typing.Iterable[data.ProductionAssoc]):
        self.selections: dict[data.Resource, data.Recipe] = dict(map(lambda s: (s.product, s.recipe), sel))


class _AltSelModel:

    def __init__(self, recipe: data.Recipe):
        self.recipe = recipe
        self.alternatives: dict[data.Resource, set[data.Recipe]] = dict()
        self.selections = dict(map(lambda r: r.products, recipe.products))

    def get_selections(self) -> AltSelections:
        pass


def _generate_alternatives(repository: persistence.RecipeRepository, recipe: data.Recipe) -> set[data.ProductionAssoc]:
    max_tree_depth = configuration.MainConfig().prod_tree_max_recursion_depth
    root_product = list(recipe.products.values())[0]  # doesn't matter which one
    tree = chaining.ProductionTree(recipe, root_product.resource, root_product.quantity)
    tree.build(repository, max_tree_depth)

    return tree.find_alternatives()


def _product_id(assoc: data.ProductionAssoc) -> str:
    return f'res_{assoc.product.get_id()}'


def _recipe_id(assoc: data.ProductionAssoc) -> str:
    return f'rec_{assoc.product.get_id()}_{assoc.recipe.get_id()}'


class ProducerSelectController(RootController):
    _TAG_PRODUCT_ROW = 'row_product'
    _TAG_RECIPE_ROW = 'row_recipe'
    TAG_INVALID_SEL = 'invalid_sel'

    def __init__(self, master, v_id: str, parent: typing.Optional[Controller], repository: RecipeRepository):
        super().__init__(v_id, parent, repository)
        self.assoc_cache = ProdAssocRepository()
        self.current_recipe: typing.Optional[data.Recipe] = None
        self.is_valid = True
        self.view = ProducerSelectView(master, self)
        self.listeners: list[typing.Callable[[], None]] = list()

    def widget(self) -> 'ProducerSelectView':
        return self.view

    def value(self) -> typing.Optional[tuple[data.Recipe, set[data.ProductionAssoc]]]:
        if self.current_recipe is not None:
            avs = self.view.get_active()

            product_selections: dict[data.Resource, data.Recipe] = dict()
            recipe_assocs = self.assoc_cache.get_associations_raw(self.current_recipe)

            for product_frame in avs.product_frames:
                product_id = product_frame.product_id
                recipes: list[data.Recipe] = list()
                product: typing.Optional[data.Resource] = None
                for prd, recs in recipe_assocs.items():
                    if prd.get_id() == product_id:
                        recipes = list(recs)
                        recipes.sort(key=lambda r: r.get_name())
                        product = prd
                        break
                if len(recipes) == 0 or product is None:
                    raise Exception(f'failed to match selections to data!')
                sel_idx = product_frame.cbx_recipe.current()
                product_selections[product] = recipes[sel_idx]
            return self.current_recipe, set(
                map(lambda kv: data.ProductionAssoc(kv[0], kv[1]), product_selections.items()))
        else:
            return None

    @deprecated('')
    def set_value(self, val: T):
        logging.warning(f'called set_value() without support by this controller type')

    def load_associations(self, recipe: data.Recipe):
        existed = True
        if recipe not in self.assoc_cache:
            existed = False
            alts = _generate_alternatives(self.repository, recipe)
            self.assoc_cache.add_associations(recipe, alts)
        self.view.set_active(recipe.get_id())
        self.current_recipe = recipe
        self.check_valid_of_current()
        if not existed:
            self.init_view()

    def init_view(self):
        active_asv = self.view.get_active()

        recipe_selectables = list()
        for resource, recipes in self.assoc_cache.get_associations_raw(self.current_recipe).items():
            recipe_names = list(map(lambda r: r.get_name(), recipes))
            recipe_names.sort()
            recipe_selectables.append((resource.get_id(), resource.get_name(), recipe_names))

        active_asv.init_selections(recipe_selectables)

    def check_valid_of_current(self):
        invalid_count = 0
        recipe_view = self.view.get_active()
        for view in recipe_view.product_frames:
            selected = view.cbx_recipe.get()
            if selected == '':
                invalid_count += 1
        self.is_valid = invalid_count == 0

    def cb_producer_change(self):
        self.check_valid_of_current()
        for listener in self.listeners:
            listener()


class ProducerSelectView(ttk.Frame, View):
    __DUMMY_KEY = '__dummy__'

    def __init__(self, master, controller: 'ProducerSelectController'):
        View.__init__(self, controller)
        super().__init__(master)

        self.asv_mapping = {self.__DUMMY_KEY: AltSelectView(self, controller)}
        self.active_asv = self.__DUMMY_KEY
        self.set_active(self.__DUMMY_KEY)

    def _init_asv(self, asv_key: str):
        view = AltSelectView(self, self.controller)
        self.asv_mapping[asv_key] = view

    def set_active(self, asv_key: str):
        if self.active_asv != self.__DUMMY_KEY:
            self.get_active().grid_remove()
        if asv_key not in self.asv_mapping:
            self._init_asv(asv_key)
        self.active_asv = asv_key
        self.asv_mapping[asv_key].grid(row=0, column=0, sticky=tk.NSEW)
        self.asv_mapping[asv_key].focus_set()

    def get_active(self) -> typing.Optional['AltSelectView']:
        asv_key = self.active_asv
        return self.asv_mapping[self.active_asv] if asv_key != self.__DUMMY_KEY else None


class AltSelectView(ttk.Frame, View):

    def __init__(self, master, controller: ProducerSelectController):
        View.__init__(self, controller)
        super().__init__(master)
        self.product_frames: list[AltSelectCbxView] = list()

    def init_selections(self, selectables: list[tuple[str, str, list[str]]]):
        for frame in self.product_frames:
            frame.destroy()
        if len(self.product_frames) > 0:
            self.product_frames = list()
        row = 0
        for p_id, p_name, recipes in selectables:
            frame = AltSelectCbxView(self, self.controller, p_id, p_name, recipes)
            frame.grid(row=row, column=0, sticky=tk.NSEW)
            self.product_frames.append(frame)
            row += 1


class AltSelectCbxView(ttk.Frame, View):

    def __init__(self, master, controller: ProducerSelectController, product_id: str, product_name: str,
                 select_opts: list[str]):
        View.__init__(self, controller)
        super().__init__(master)
        self.product_id = product_id
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=1)
        row = 0

        self.lbl_product = ttk.Label(self, text=product_name)
        self.lbl_product.grid(row=row, column=0, sticky=tk.NW, padx=5)
        self.cbx_recipe = ttk.Combobox(self, values=select_opts, state='readonly')
        self.cbx_recipe.grid(row=0, column=1, sticky=tk.NE, padx=5)
        self.cbx_recipe.bind('<<ComboboxSelected>>', lambda e: controller.cb_producer_change())
        row += 1


class AltSelectionPopup:

    def __init__(self, alternatives: list[data.ProductionAssoc]):
        self.alternatives = alternatives
        self.win = tk.Toplevel()
        self.win.wm_title('Please select the alternatives')
        self.tv_alts = ttk.Treeview(self.win, columns=('Resource', 'Recipe'))
        self.tv_alts.grid(row=0, column=0, sticky=tk.NSEW)

        self.win.columnconfigure(0, weight=1)

        for alt in alternatives:
            self.tv_alts.insert('', 'end', values=(alt.product.name, str(alt.recipe)))

    def get_alts(self):
        pass
