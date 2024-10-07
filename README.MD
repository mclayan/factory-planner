## Usage

```sh
$ python main.py [-h] [-r NAME] [-c NAME] [DATA_DIR]
```

Where `DATA_DIR` is the directory containing `resources.json` and `recipes.json`. This parameter defaults to `./data`, 
so it is optional if the default data directory is within the current working dir.

## Preface: Entity Selector (`ENTITY_SEL`)
Whenever specifying an existing resource or recipe it is possible to select the right entity either by name or by id.
In these cases, the command requires a value `ENTITY_SEL`, which represent either based on its form:
  * `@<ENTITY_ID>` means the entity is selected by matching its ID with the value after `@`
  * `<ENTITY_NAME>` means the entity is selected by matching its name with the full string

#### Examples

Selecting the resource "Iron Rod" by its ID `"iron_rod"`:
```text
=> <some_command> -r @iron_rod
```

Selecting the recipe "Smart Plating" by its name `"Smart Plating"`. The `"` are required because of the space in the name.
```text
=> <some_command> -p "Smart Plating"
```

## Adding Resources: `add-resource`

```sh
usage: add-resource [-h] [-i NAME] [-r] NAME

positional arguments:
  NAME                Name of the resource

options:
  -h, --help          show this help message and exit
  -i NAME, --id NAME  Set resource id.
  -r, --raw           Make resource a raw base resource.
```

Resources must be added manually by using the command `add-resource` and consist of:
  * the resource `name`, which is used for displaying
  * the resource `id`, which must be unique
  * `is_raw`, which is `true` for raw resources like Iron Ore and `false` for everything else

Only the resource name is required. The resource ID will be generated from the name if not specified.

#### Examples:

Adding a non-raw resource:
```sh
=> add-resource "Iron Ingot"
```

To add a raw resource:
```sh
=> add-resource "Iron Ore" -r
```

## Adding Recipes: `add-recipe`

```sh
usage: add-recipe [-h] [-i NAME] -t DURATION [-p PRODUCTS [PRODUCTS ...]]
                  [-r RESOURCES [RESOURCES ...]]
                  NAME

positional arguments:
  NAME                  Name of the recipe.

options:
  -h, --help            show this help message and exit
  -i NAME, --id NAME    Set recipe id.
  -t DURATION, --time DURATION
                        Time in seconds one cycle takes.
  -p PRODUCTS [PRODUCTS ...], --product PRODUCTS [PRODUCTS ...]
                        Resource produced by executing the recipe.
  -r RESOURCES [RESOURCES ...], --resource RESOURCES [RESOURCES ...]
                        Resource produced by executing the recipe.
```

Adding recipes is only possible if all resources (products and requirements) are already registered. Like resources,
recipes have a name and a unique ID. In addition, the following must be specified for each recipe:

  * `RESOURCES`: the resources consumed as input when executing this recipe. Each resource argument must be in the format 
    `<ENTITY_SEL> <QUANTITY>`
  * `PRODUCTS`: the resources produced as output when executing this recipe. Each product argument must be in the format 
    `<ENTITY_SEL> <QUANTITY>`
  * `DURATION`: the time to complete one production cycle. Not to be confused with _Production per Minute_. The duration
    format is `[[HH:]MM:]SS`.

As with resources, the recipe ID will be generated from the name if not set.

#### Examples:

Adding a recipe for Iron Plates with `3x Iron Ingot --[6s]--> 2x Iron Plate` (output: 20x Iron Plate / min)
```sh
=> add-recipe "Iron Plate" -r "Iron Ingot" 3 -p "Iron Plate" 2 -t 6
```

The same recipe using the full duration format:
```sh
=> add-recipe "Iron Plate" -r "Iron Ingot" 3 -p "Iron Plate" 2 -t "00:00:06"
```

A more complex recipe with multiple products and resources:
```sh
=> add-recipe "Alumina Solution" -r "Bauxite" 12 -r "Water" 18 -p "Alumina Solution" 12 -p "Silica" 5 -t "00:00:06"
```

## Calculating Dependency Trees: `tree`

To calculate a dependency tree and the total quantity of base resources, use the `tree` command. It is possible to either
select a specific recipe for the end product or specify the end product and automatically select a recipe. All intermediate
recipes will be selected automatically. If more than one recipe was found for a specific intermediate product, the one
with the highest output will be selected (more configuration options to be implemented).

```text
usage: tree [-h] [-l LIMIT] [-p PRODUCT] [-r RPM] RECIPE

positional arguments:
  RECIPE

options:
  -h, --help            show this help message and exit
  -l LIMIT, --limit LIMIT
                        Maximum tree depth (recursion)
  -p PRODUCT, --product PRODUCT
                        Product to select from recipe. Optional if recipe
                        produces only one product.
  -r RPM, --rpm RPM     Target RPM of the selected product. If not set, the
                        default RPM for the product in the recipe will be
                        used.
```

The dependency tree displays production chains for each requirement of the selected end product recipe. Each node of the
tree is a recipe combined with the target RPM adjusted to the requirements of the parent node. The tree is built
recursively until either a raw base resource is reached or no recipe was found for a non-raw resource. Alternative
recipes are handled as a second dimension on each recipe node and hidden when displayed. By default, all applicable 
recipes are determined for a non-raw resource and ordered by output RPM in descending order. Only the first recipe in
this order will be used for displaying and building the aggregated view.


In addition to the dependency tree, the total number of base resources and intermediate products are listed in the format
```text
<"Recipe"|"Resource">  <RECIPE_NAME>  (<COUNT>) => 1.0x <PRODUCT>: [<FORMULA>] ==> <TOTAL_RPM>
```
where each line represents a product:
  * `"Recipe"|"Resource"` indicates if this line suggests a number of executions of a recipe or the input of a resource
  * `RECIPE_NAME` is the name of the recipe or the resource
  * `COUNT` is how many parallel executions of the recipe are required to reach the target RPM of the end product
  * `PRODUCT` is the desired product of the recipe
  * `FORMULA` is the formula of the product from the perspective of the desired product
  * `TOTAL_RPM` is the total products per minute to be produced by this line

Example:
```text
=> tree Screw -r 180
Dependency tree:
<...>

Aggregated resources:
Recipe: Screw (3.0) => 1.0x "Screw": [10.0x(Iron Rod) -> 60.0x(Screw) p.m.]  ==> 180.0 p.m.
Recipe: Iron Rod (2.0) => 1.0x "Iron Rod": [15.0x(Iron Ingot) -> 15.0x(Iron Rod) p.m.]  ==> 30.0 p.m.
Recipe: Iron Ingot (1.0) => 1.0x "Iron Ingot": [30.0x(Iron Ore) -> 30.0x(Iron Ingot) p.m.]  ==> 30.0 p.m.
Resource: Iron Ore (30.0) => 1.0x "Iron Ore": [ -> 1.0x(Iron Ore) p.m.]  ==> 30.0 p.m.
```

This aggregated view can be read as:
> To produce 180 products of "Screw" per minute, we need 4 different types of productions: Screw, Iron Rod, Iron Ingot and Iron Ore.
> The stations to build are:
>  * 3 stations with recipe "Screw"
>  * 2 stations with recipe "Iron Rod"
>  * 1 station with recipe "Iron Ingot"
>  * An input of 30 iron ore per minute


#### Examples

Analysing the dependencies for producing "Screw" with the default recipe:
```text
=> tree Screw -r 180
Dependency tree:
3.0x "Screw": [30.0x(Iron Rod) -> 180.0x(Screw) p.m.]
└── [0] 2.0x "Iron Rod": [30.0x(Iron Ingot) -> 30.0x(Iron Rod) p.m.]
    └── [0] 1.0x "Iron Ingot": [30.0x(Iron Ore) -> 30.0x(Iron Ingot) p.m.]
        └── Iron Ore: 30.0

Aggregated resources:
Recipe: Screw (3.0) => 1.0x "Screw": [10.0x(Iron Rod) -> 60.0x(Screw) p.m.]  ==> 180.0 p.m.
Recipe: Iron Rod (2.0) => 1.0x "Iron Rod": [15.0x(Iron Ingot) -> 15.0x(Iron Rod) p.m.]  ==> 30.0 p.m.
Recipe: Iron Ingot (1.0) => 1.0x "Iron Ingot": [30.0x(Iron Ore) -> 30.0x(Iron Ingot) p.m.]  ==> 30.0 p.m.
Resource: Iron Ore (30.0) => 1.0x "Iron Ore": [ -> 1.0x(Iron Ore) p.m.]  ==> 30.0 p.m.
```

We can see that for the recipe "Screw" we need 30 iron rod per minute, which can be produced by two executions of the
recipe "Iron Rod". This recipe again can be satisfied by one execution of "Iron Ingot", which requires an input of
30 iron ore per minute.

A dependency tree for a recipe with multiple requirements:
```text
=> tree "Reinforced Iron Plate"
Dependency tree:
1.0x "Reinforced Iron Plate": [30.0x(Iron Plate) + 60.0x(Screw) -> 5.0x(Reinforced Iron Plate) p.m.]
├── [0] 1.5x "Iron Plate": [45.0x(Iron Ingot) -> 30.0x(Iron Plate) p.m.]
│   └── [0] 1.5x "Iron Ingot": [45.0x(Iron Ore) -> 45.0x(Iron Ingot) p.m.]
│       └── Iron Ore: 45.0
└── [0] 1.0x "Screw": [10.0x(Iron Rod) -> 60.0x(Screw) p.m.]
    └── [0] 0.7x "Iron Rod": [10.0x(Iron Ingot) -> 10.0x(Iron Rod) p.m.]
        └── [0] 0.3x "Iron Ingot": [10.0x(Iron Ore) -> 10.0x(Iron Ingot) p.m.]
            └── Iron Ore: 10.0

Aggregated resources:
Recipe: Reinforced Iron Plate (1.0) => 1.0x "Reinforced Iron Plate": [30.0x(Iron Plate) + 60.0x(Screw) -> 5.0x(Reinforced Iron Plate) p.m.]  ==> 5.0 p.m.
Recipe: Iron Plate (1.5) => 1.0x "Iron Plate": [30.0x(Iron Ingot) -> 20.0x(Iron Plate) p.m.]  ==> 30.0 p.m.
Recipe: Iron Ingot (1.8) => 1.0x "Iron Ingot": [30.0x(Iron Ore) -> 30.0x(Iron Ingot) p.m.]  ==> 55.0 p.m.
Recipe: Screw (1.0) => 1.0x "Screw": [10.0x(Iron Rod) -> 60.0x(Screw) p.m.]  ==> 60.0 p.m.
Recipe: Iron Rod (0.7) => 1.0x "Iron Rod": [15.0x(Iron Ingot) -> 15.0x(Iron Rod) p.m.]  ==> 10.0 p.m.
Resource: Iron Ore (55.0) => 1.0x "Iron Ore": [ -> 1.0x(Iron Ore) p.m.]  ==> 55.0 p.m.
```

## Listing Registered Entities: `ls`

```text
usage: ls [-h] [-p PRODUCT] [-r RECIPE] [TYPE]

positional arguments:
  TYPE

options:
  -h, --help            show this help message and exit
  -p PRODUCT, --product PRODUCT
                        Display specific resource/product.
  -r RECIPE, --recipe RECIPE
                        Display specific recipe.
```

To list registered resources or recipes, the `ls` command can be used. It can be used to view either a single resource
or recipe or to list all registered entities of a specific type:

  * Use `-p / --product ENTITY_SEL` to show a specific resource
  * Use `-r / --recipe ENTITY_SEL` to show a specific recipe
  * Use the positional parameter `TYPE` with either:
    * `r` or `recipes` to list all recipes
    * `R` or `resources` to list all resources

When using `resources` for `TYPE`, the output format is always `<ENTITY_ID> -> "<ENTITY_NAME>"`.
#### Examples

Listing all registered resources:
```sh
=> ls R
limestone -> "Limestone"
concrete -> "Concrete"
```

Showing a single recipe selected by its ID:
```sh
=> ls -r @iron_rod
Recipe "Iron Rod": [1.0x(Iron Ingot) -> 1.0x(Iron Rod)]
```

The same by recipe name:
```sh
=> ls -r "Iron Rod"
Recipe "Iron Rod": [1.0x(Iron Ingot) -> 1.0x(Iron Rod)]
```