import montepy

from constants import *


def create_surface():
    num = OBJ_NUMBER()
    surf_type = montepy.SurfaceType(SURF_TYPE())
    num_constants = NUM_CONSTANTS[surf_type]
    constants = []
    for _ in range(num_constants):
        constants.append(str(SURFACE_CONSTANT()))
    surf = montepy.surfaces.surface_builder.parse_surface(
        f"{num} {surf_type} {' '.join(constants)}"
    )
    return surf

def create_surfaces(problem, n_cells):
    n_cells = N_CELLS_NOISE(n_cells)
    if SURF_ABOVE_CURVE():
        n_surfs = SURF_TOP_CURVE(n_cells)
    else:
        n_surfs = SURF_BOT_CURVE(n_cells)
    for _ in range(int(n_surfs)):
        problem.surfaces.append_renumber(create_surface())

def create_materials(problem, n_cells):
    n_cells = N_CELLS_NOISE(n_cells)
    n_mats = int(MATERIAL_CURVE(n_cells))
    for _ in range(n_mats):
        problem.materials.append_renumber(create_material())

def create_material():
    return montepy.Material()

def create_cell(problem):
    pass


problem= montepy.MCNP_Problem("foo")
create_surfaces(problem, 100)
for surf in problem.surfaces:
    print(surf.mcnp_str())
