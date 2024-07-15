# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from enum import Enum
import itertools
from montepy.data_inputs import mode, transform
from montepy._cell_data_control import CellDataPrintController
from montepy.cell import Cell
from montepy.cells import Cells
from montepy.errors import *
from montepy.constants import DEFAULT_VERSION
from montepy.materials import Materials
from montepy.surfaces import surface_builder
from montepy.surface_collection import Surfaces
from montepy.data_inputs import Material, parse_data
from montepy.input_parser import input_syntax_reader, block_type, mcnp_input
from montepy.input_parser.input_file import MCNP_InputFile
from montepy.universes import Universes
from montepy.transforms import Transforms
import warnings


class MCNP_Problem:
    """
    A class to represent an entire MCNP problem in a semantic way.

    :param file_name: the path to the file that will be read.
    :type file_name: str
    """

    def __init__(self, file_name):
        self._input_file = MCNP_InputFile(file_name)
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

        This should not be mutated, and should be used as a reference to maintain
        the structure

        .. deprecated:: 0.2.0
            This will likely be removed soon, and it's functionality will not be necessary to reproduce.

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
        if cells is self.cells:
            return
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

        For details see: :func:`montepy.data_cards.mode.Mode.set`.

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
            raise ValueError(f"The mcnp_version {version} is not supported by MontePy")
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

        :return: a list of the :class:`~montepy.data_cards.data_card.DataCardAbstract` objects, ordered by the order they were in the input file.
        :rtype: list
        """
        return self._data_inputs

    @property
    def input_file(self):
        """
        The file name of the original file name this problem was read from.

        :rtype: MCNP_InputFile
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

        :returns: a collection of universes in the problem.
        :rtype: Universes
        """
        return self._universes

    @property
    def transforms(self):
        """
        The collection of transform objects in this problem.

        :returns: a collection of transforms in the problem.
        :rtype: Transforms
        """
        return self._transforms

    def parse_input(self, check_input=False, replace=True):
        """
        Semantically parses the MCNP file provided to the constructor.

        :param check_input: If true, will try to find all errors with input and collect them as warnings to log.
        :type check_input: bool
        :param replace: replace all non-ASCII characters with a space (0x20)
        :type replace: bool
        """
        trailing_comment = None
        last_obj = None
        OBJ_MATCHER = {
            block_type.BlockType.CELL: (Cell, self._cells),
            block_type.BlockType.SURFACE: (
                surface_builder.surface_builder,
                self._surfaces,
            ),
            block_type.BlockType.DATA: (parse_data, self._data_inputs),
        }
        try:
            for i, input in enumerate(
                input_syntax_reader.read_input_syntax(
                    self._input_file, self.mcnp_version, replace=replace
                )
            ):
                self._original_inputs.append(input)
                if i == 0 and isinstance(input, mcnp_input.Message):
                    self._message = input

                elif isinstance(input, mcnp_input.Title) and self._title is None:
                    self._title = input

                elif isinstance(input, mcnp_input.Input):
                    obj_parser, obj_container = OBJ_MATCHER[input.block_type]
                    if len(input.input_lines) > 0:
                        try:
                            obj = obj_parser(input)
                            obj.link_to_problem(self)
                            obj_container.append(obj)
                        except (
                            MalformedInputError,
                            NumberConflictError,
                            ParsingError,
                            UnknownElement,
                        ) as e:
                            if check_input:
                                warnings.warn(
                                    f"{type(e).__name__}: {e.message}", stacklevel=2
                                )
                                continue
                            else:
                                raise e
                        if isinstance(obj, Material):
                            self._materials.append(obj)
                        if isinstance(obj, transform.Transform):
                            self._transforms.append(obj)
                    if trailing_comment is not None and last_obj is not None:
                        obj._grab_beginning_comment(trailing_comment)
                        last_obj._delete_trailing_comment()
                    trailing_comment = obj.trailing_comment
                    last_obj = obj
        except UnsupportedFeature as e:
            if check_input:
                warnings.warn(f"{type(e).__name__}: {e.message}", stacklevel=2)
            else:
                raise e
        self.__update_internal_pointers(check_input)

    def __update_internal_pointers(self, check_input=False):
        """Updates the internal pointers between objects

        :param check_input: If true, will try to find all errors with input and collect them as warnings to log.
        :type check_input: bool
        """

        def handle_error(e):
            if check_input:
                warnings.warn(f"{type(e).__name__}: {e.message}", stacklevel=3)
            else:
                raise e

        self.__load_data_inputs_to_object(self._data_inputs)
        self._cells.update_pointers(
            self.cells,
            self.materials,
            self.surfaces,
            self._data_inputs,
            self,
            check_input,
        )
        for surface in self._surfaces:
            try:
                surface.update_pointers(self.surfaces, self._data_inputs)
            except (
                BrokenObjectLinkError,
                ParticleTypeNotInProblem,
                ParticleTypeNotInCell,
            ) as e:
                handle_error(e)
        for input in self._data_inputs:
            try:
                input.update_pointers(self._data_inputs)
            except (
                BrokenObjectLinkError,
                MalformedInputError,
                ParticleTypeNotInProblem,
                ParticleTypeNotInCell,
            ) as e:
                handle_error(e)
                continue

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
        Adds the surfaces, materials, and transforms of all cells in this problem to this problem to the
        internal lists to allow them to be written to file.

        .. warning::
            this does not move complement cells, and probably other objects.
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

    def write_to_file(self, new_problem, overwrite=False):
        """
        Writes the problem to a file.

        .. versionchanged:: 0.3.0
            The overwrite parameter was added.

        :param new_problem: the file name to write this problem to
        :type new_problem: str
        :param overwrite: Whether to overwrite the file at 'new_problem' if it exists
        :type overwrite: bool
        :raises IllegalState: if an object in the problem has not been fully initialized.
        :raises FileExistsError: if a file already exists with the same path.
        :raises IsADirectoryError: if the path given is actually a directory.
        """
        new_file = MCNP_InputFile(new_problem, overwrite=overwrite)
        with new_file.open("w") as fh, warnings.catch_warnings(
            record=True
        ) as warning_catch:
            objects_list = []
            if self.message:
                objects_list.append(([self.message], False))
            objects_list += [
                ([self.title], False),
                (self.cells, True),
                (self.surfaces, True),
                (self.data_inputs, True),
            ]
            for objects, terminate in objects_list:
                for obj in objects:
                    lines = obj.format_for_mcnp_input(self.mcnp_version)
                    if warning_catch:
                        # handle ALL new warnings
                        for warning in warning_catch[::-1]:
                            if getattr(warning, "handled", None):
                                break
                            warning.lineno = fh.lineno
                            warning.path = fh.name
                            warning.obj = obj
                            warning.lines = lines
                            warning.handled = True
                    for line in lines:
                        fh.write(line + "\n")
                if terminate:
                    fh.write("\n")
            for line in self.cells._run_children_format_for_mcnp(
                self.data_inputs, self.mcnp_version
            ):
                fh.write(line + "\n")

            fh.write("\n")
        self._handle_warnings(warning_catch)

    def _handle_warnings(self, warning_queue):
        class WarningLevels(Enum):
            SUPRESS = 0
            MINIMAL = 1
            MAXIMAL = 5

        warning_level = WarningLevels.MAXIMAL

        for warning_message in warning_queue:
            warning = warning_message.message
            message = f"The input starting on Line {warning_message.lineno} of: {warning_message.path} expanded. "
            if warning_level == WarningLevels.SUPRESS:
                continue
            elif warning_level == WarningLevels.MINIMAL:
                if warning.cause == "value":
                    message += f"The new value is: {warning.new_value}"
                else:
                    message += f"The new lines are: {warning.new_value}"
            elif warning_level == WarningLevels.MAXIMAL:
                message += "\nThe new input is:\n"
                for i, line in enumerate(warning_message.lines):
                    message += f"     {warning_message.lineno + i:5g}| {line}\n"
                message += warning.message
            warning = LineExpansionWarning(message)
            warnings.warn(warning, stacklevel=3)

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
        return f"MCNP problem for: {self._input_file}, {self._title}"

    def __repr__(self):
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
