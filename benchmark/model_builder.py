import montepy
import warnings

from constants import *

warnings.filterwarnings("ignore", category=montepy.exceptions.LineExpansionWarning)


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
    num_nuclides = NUM_NUCLIDES()
    library = LIBRARIES()
    mat = montepy.Material(number=OBJ_NUMBER())
    for _ in range(int(np.ceil(num_nuclides))):
        mat.add_nuclide(f"{ISOTOPE()}.{library}", np.random.rand())
    return mat


def create_cells(problem, n_cells):
    for _ in range(n_cells):
        problem.cells.append_renumber(create_cell(problem))


def create_cell(problem):
    cell = montepy.Cell(number=OBJ_NUMBER())
    cell.material = np.random.choice(np.fromiter(problem.materials, dtype="O"))
    if ATOM_MASS_DENSITY():
        cell.atom_density = ATOM_DENSITY()
    else:
        cell.mass_density = MASS_DENSITY()
    num_surfaces = np.ceil(NUM_SURFS_IN_CELL())
    cell_selector = lambda: np.random.choice(np.fromiter(problem.cells, dtype="O"))
    surf_selector = lambda: np.random.choice(np.fromiter(problem._surfaces, dtype="O"))
    for _ in range(int(num_surfaces)):
        # if cell complement
        if CELL_GEOM_COMP():
            halfspace = ~cell_selector()
        else:
            surf = surf_selector()
            if CELL_GEOM_SIDE():
                halfspace = +surf
            else:
                halfspace = -surf
        if cell.geometry is None:
            cell.geometry = halfspace
        else:
            if CELL_GEOM_INTERSECT():
                cell.geometry &= halfspace
            else:
                cell.geometry |= halfspace
    return cell


# TODO open issue report for exporting from scratch
def create_problem(num_cells):
    problem = montepy.read_input("../tests/inputs/test.imcnp")
    problem.cells.clear()
    problem.surfaces.clear()
    problem.materials.clear()
    problem.data_inputs.clear()
    problem.title = f"Randomly Generated problem with {num_cells} cells"
    create_surfaces(problem, num_cells)
    create_materials(problem, num_cells)
    create_cells(problem, num_cells)
    return problem


problem = create_problem(10)
problem.write_problem("foo.imcnp", overwrite=True)
