import itertools
from mcnpy.data_inputs import mode, transform
from mcnpy._cell_data_control import CellDataPrintController
from mcnpy.cell import Cell
from mcnpy.cells import Cells
from mcnpy.errors import *
from mcnpy.constants import DEFAULT_VERSION
from mcnpy.materials import Materials
from mcnpy.surfaces import surface_builder
from mcnpy.surface_collection import Surfaces
from mcnpy.data_inputs import Material, parse_data
from mcnpy.input_parser import input_syntax_reader, block_type, mcnp_input
from mcnpy.universes import Universes
from mcnpy.transforms import Transforms


class MCNP_Problem:
    """
    A class to represent an entire MCNP problem in a semantic way.

    :param file_name: the path to the file that will be read.
    :type file_name: str
    """

    def __init__(self, file_name):
        self._input_file = file_name
        self._title = None
        self._message = None
        self._print_in_data_block = CellDataPrintController()
        self._original_inputs = []
        self._cells = Cells(problem=self)
        self._surfaces = Surfaces(problem=self)
        self._universes = Universes(problem=self)
        self._transforms = Transforms(problem=self)
        self._data_inputs = []
        self._materials = Materials(problem=self)
        self._mcnp_version = DEFAULT_VERSION
        self._mode = mode.Mode()

    @property
    def original_inputs(self):
        """
        A list of the MCNP_Inputs read from the original file.

        This should not be mutated, and should be used a reference to maintain
        the structure

        :return: A list of the MCNP_Object objects representing the file as it was read
        :rtype: list
        """
        return self._original_inputs

    @property
    def cells(self):
        """
        A collection of the Cell objects in this problem.

        :return: a collection of the Cell objects, ordered by the order they were in the input file.
        :rtype: Cells
        """
        return self._cells

    @cells.setter
    def cells(self, cells):
        if not isinstance(cells, (Cells, list)):
            raise TypeError("cells must be an instance of list or Cells")
        if isinstance(cells, list):
            cells = Cells(cells)
        self.cells.clear()
        self.cells.extend(cells)

    @property
    def mode(self):
        """
        The mode of particles being used for the problem.

        :rtype: Mode
        """
        return self._mode

    def set_mode(self, particles):
        """Sets the mode of problem to the given particles.

        For details see: :func:`mcnpy.data_cards.mode.Mode.set`.

        :param particles: the particles that the mode will be switched to.
        :type particles: list, str
        :raises ValueError: if string is not a valid particle shorthand.
        """
        self._mode.set(particles)

    @property
    def mcnp_version(self):
        """
        The version of MCNP that this is intended for.

        .. note::
            MCNP versions prior to 6.2 aren't fully supported to avoid
            Export Control Restrictions. Documentation for MCNP 6.2 is public in report:
            LA-UR-17-29981.
            All features are based on MCNP 6.2, and may cause other versions of MCNP to break.

        The version is a tuple of major, minor, revision.
        6.2.0 would be represented as (6, 2, 0)

        :rtype: tuple
        """
        return self._mcnp_version

    @mcnp_version.setter
    def mcnp_version(self, version):
        """
        :param version: the version tuple. Must be greater than 6.2.0
        :type version: tuple
        """
        if version < (5, 1, 60):
            raise ValueError(f"The mcnp_version {version} is not supported by MCNPy")
        self._mcnp_version = version

    @property
    def surfaces(self):
        """
        A collection of the Surface objects in this problem.

        :return: a collection of the Surface objects, ordered by the order they were in the input file.
        :rtype: Surfaces
        """
        return self._surfaces

    @property
    def materials(self):
        """
        A collection of the Material objects in this problem.

        :return: a colection of the Material objects, ordered by the order they were in the input file.
        :rtype: Materials
        """
        return self._materials

    @materials.setter
    def materials(self, mats):
        if not isinstance(mats, (list, Materials)):
            raise TypeError("materials must be of type list and Materials")
        if isinstance(mats, list):
            mats = Materials(mats)
        self._materials = mats

    @property
    def print_in_data_block(self):
        """
        Controls whether or not the specific input gets printed in the cell block or the data block.

        This acts like a dictionary. The key is the case insensitive name of the card.
        For example to enable printing importance data in the data block run:

        ``problem.print_in_data_block["Imp"] = True``

        :rtype: bool
        """
        return self._print_in_data_block

    @property
    def data_inputs(self):
        """
        A list of the DataInput objects in this problem.

        :return: a list of the :class:`~mcnpy.data_cards.data_card.DataCardAbstract` objects, ordered by the order they were in the input file.
        :rtype: list
        """
        return self._data_inputs

    @property
    def input_file(self):
        """
        The file name of the original file name this problem was read from.

        :rtype: str
        """
        return self._input_file

    @property
    def message(self):
        """
        The Message object at the beginning of the problem if any.

        :rtype: Message
        """
        return self._message

    @property
    def title(self):
        """
        The Title object for the title.

        :rtype: Title
        """
        return self._title

    @title.setter
    def title(self, title):
        """
        :type title: The str for the title to be set to.
        """
        self._title = mcnp_input.Title([title], title)

    @property
    def universes(self):
        """
        The Universes object holding all problem universes.
        """
        return self._universes

    @property
    def transforms(self):
        """
        The transform objects in this problem.
        """
        return self._transforms

    def parse_input(self):
        """
        Semantically parses the MCNP file provided to the constructor.
        """
        trailing_comment = None
        last_obj = None
        for i, input in enumerate(
            input_syntax_reader.read_input_syntax(self._input_file, self.mcnp_version)
        ):
            self._original_inputs.append(input)
            if i == 0 and isinstance(input, mcnp_input.Message):
                self._message = input

            elif isinstance(input, mcnp_input.Title) and self._title is None:
                self._title = input

            elif isinstance(input, mcnp_input.Input):
                if len(input.input_lines) > 0:
                    if input.block_type == block_type.BlockType.CELL:
                        obj = Cell(input)
                        obj.link_to_problem(self)
                        self._cells.append(obj)
                    if input.block_type == block_type.BlockType.SURFACE:
                        obj = surface_builder.surface_builder(input)
                        obj.link_to_problem(self)
                        self._surfaces.append(obj)
                    if input.block_type == block_type.BlockType.DATA:
                        obj = parse_data(input)
                        obj.link_to_problem(self)
                        if isinstance(obj, Material):
                            self._materials.append(obj)
                        if isinstance(obj, transform.Transform):
                            self._transforms.append(obj)
                        self._data_inputs.append(obj)
                if trailing_comment is not None and last_obj is not None:
                    obj._grab_beginning_comment(trailing_comment)
                    last_obj._delete_trailing_comment()
                trailing_comment = obj.trailing_comment
                last_obj = obj
        self.__update_internal_pointers()

    def __update_internal_pointers(self):
        """Updates the internal pointers between objects"""
        self.__load_data_inputs_to_object(self._data_inputs)
        self._cells.update_pointers(
            self.cells, self.materials, self.surfaces, self._data_inputs, self
        )
        for surface in self._surfaces:
            surface.update_pointers(self.surfaces, self._data_inputs)
        for input in self._data_inputs:
            input.update_pointers(self._data_inputs)

    def remove_duplicate_surfaces(self, tolerance):
        """Finds duplicate surfaces in the problem, and remove them.

        :param tolerance: The amount of relative error to consider two surfaces identical
        :type tolerance: float
        """
        to_delete = set()
        matching_map = {}
        for surface in self.surfaces:
            if surface not in to_delete:
                matches = surface.find_duplicate_surfaces(self.surfaces, tolerance)
                if matches:
                    for match in matches:
                        to_delete.add(match)
                        matching_map[match] = surface
        for cell in self.cells:
            cell.remove_duplicate_surfaces(matching_map)
        self.__update_internal_pointers()
        for surface in to_delete:
            self._surfaces.remove(surface)

    def add_cell_children_to_problem(self):
        """
        Adds the surfaces and materials of all cells in this problem to this problem to the
        internal lists to allow them to be written to file.

        .. warning::
            this does not move complement cells, and probably others.
        """
        surfaces = set(self.surfaces)
        materials = set(self.materials)
        transforms = set(self.transforms)
        for cell in self.cells:
            surfaces.update(set(cell.surfaces))
            for surf in cell.surfaces:
                if surf.transform:
                    transforms.add(surf.transform)
            if cell.material:
                materials.add(cell.material)
        surfaces = sorted(surfaces)
        materials = sorted(materials)
        transforms = sorted(transforms)
        self._surfaces = Surfaces(surfaces)
        self._materials = Materials(materials)
        self._transforms = Transforms(transforms)
        self._data_inputs = sorted(set(self._data_inputs + materials + transforms))

    def write_to_file(self, new_problem):
        """
        Writes the problem to a file.

        :param new_problem: the file name to write this problem to
        :type new_problem: str
        :raises IllegalState: if an object in the problem has not been fully initialized.
        """
        with open(new_problem, "w") as fh:
            if self.message:
                for line in self.message.format_for_mcnp_input(self.mcnp_version):
                    fh.write(line + "\n")
            lines = self.title.format_for_mcnp_input(self.mcnp_version)
            fh.write(lines[0] + "\n")
            for cell in self.cells:
                for line in cell.format_for_mcnp_input(self.mcnp_version):
                    fh.write(line + "\n")
            # block terminator
            fh.write("\n")
            for surface in self.surfaces:
                for line in surface.format_for_mcnp_input(self.mcnp_version):
                    fh.write(line + "\n")
            fh.write("\n")
            for input in self.data_inputs:
                for line in input.format_for_mcnp_input(self.mcnp_version):
                    fh.write(line + "\n")
            for line in self.cells._run_children_format_for_mcnp(
                self.data_inputs, self.mcnp_version
            ):
                fh.write(line + "\n")

            fh.write("\n")

    def __load_data_inputs_to_object(self, data_inputs):
        """
        Loads data input into their appropriate problem attribute.

        Problem-level input should be loaded this way like: mode and kcode.
        """
        inputs_to_property = {mode.Mode: "_mode"}
        inputs_loaded = set()
        for input in data_inputs:
            if type(input) in inputs_to_property:
                if type(input) in inputs_loaded:
                    raise MalformedInputError(
                        input,
                        f"The input: {type(input)} is only allowed once in a problem",
                    )
                setattr(self, inputs_to_property[type(input)], input)
                inputs_loaded.add(type(input))

    def __str__(self):
        ret = f"MCNP problem for: {self._input_file}\n"
        if self.message:
            ret += str(self._message) + "\n"
        ret += str(self._title) + "\n"
        for cell in self._cells:
            ret += str(cell) + "\n"
        for input in self._data_inputs:
            if not isinstance(input, Material):
                ret += str(input) + "\n"
        return ret
