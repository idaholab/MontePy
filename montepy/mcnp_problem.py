# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.

import copy
from enum import Enum
import itertools
import io
import os
import warnings

from montepy.data_inputs import mode, transform
from montepy._cell_data_control import CellDataPrintController
from montepy.utilities import *
from montepy.cell import Cell
from montepy.cells import Cells
from montepy.exceptions import *
from montepy.constants import DEFAULT_VERSION
from montepy.materials import Material, Materials
from montepy.surfaces import surface, surface_builder
from montepy.surface_collection import Surfaces
import montepy.types as ty

# weird way to avoid circular imports
from montepy.data_inputs import parse_data
from montepy.input_parser import input_syntax_reader, block_type, mcnp_input
from montepy.input_parser.input_file import MCNP_InputFile
from montepy.universes import Universe, Universes
from montepy.transforms import Transforms
import montepy


class MCNP_Problem:
    """A class to represent an entire MCNP problem in a semantic way.

    Notes
    -----
    If a stream is provided. It will not be closed by this function.

    Parameters
    ----------
    destination : io.TextIOBase, str, os.PathLike
        the path to the input file to read, or a readable stream.
    """

    _NUMBERED_OBJ_MAP = {
        Cell: Cells,
        surface.Surface: Surfaces,
        Material: Materials,
        transform.Transform: Transforms,
        Universe: Universes,
    }

    @args_checked
    def __init__(self, destination: str | os.PathLike | io.TextIOBase = None):
        self._input_file = None
        if hasattr(destination, "read") and callable(getattr(destination, "read")):
            self._input_file = MCNP_InputFile.from_open_stream(destination)
        elif isinstance(destination, (str, os.PathLike)):
            self._input_file = MCNP_InputFile(destination)
        self._title = None
        self._message = None
        self.__unpickled = False
        self._print_in_data_block = CellDataPrintController()
        self._original_inputs = []
        for collect_type in self._NUMBERED_OBJ_MAP.values():
            attr_name = f"_{collect_type.__name__.lower()}"
            setattr(self, attr_name, collect_type(problem=self))
        self._data_inputs = []
        self._mcnp_version = DEFAULT_VERSION
        self._mode = mode.Mode()

    def __setstate__(self, nom_nom):
        self.__dict__.update(nom_nom)
        self.__unpickled = True

    @staticmethod
    def __get_collect_attr_name(collect_type):
        return f"_{collect_type.__name__.lower()}"

    @property
    def original_inputs(self):
        """A list of the MCNP_Inputs read from the original file.

        This should not be mutated, and should be used as a reference to maintain
        the structure

        .. deprecated:: 0.2.0
            This will likely be removed soon, and it's functionality will not be necessary to reproduce.

        Returns
        -------
        list
            A list of the MCNP_Object objects representing the file as
            it was read
        """
        return self._original_inputs

    def __relink_objs(self):
        if self.__unpickled:
            for collection in set(self._NUMBERED_OBJ_MAP.values()) | {"_data_inputs"}:
                if not isinstance(collection, str):
                    collection = self.__get_collect_attr_name(collection)
                collection = getattr(self, collection)
                if isinstance(
                    collection,
                    montepy.numbered_object_collection.NumberedObjectCollection,
                ):
                    collection.link_to_problem(self)
                else:
                    for obj in collection:
                        obj.link_to_problem(self)
            self.__unpickled = False

    def __unlink_objs(self):
        for collection in set(self._NUMBERED_OBJ_MAP.values()) | {"_data_inputs"}:
            if not isinstance(collection, str):
                collection = self.__get_collect_attr_name(collection)
            collection = getattr(self, collection)
            if isinstance(
                collection,
                montepy.numbered_object_collection.NumberedObjectCollection,
            ):
                collection.link_to_problem(None)
            else:
                for obj in collection:
                    obj.link_to_problem(None)
        self.__unpickled = True
        self.__relink_objs()

    def __deepcopy__(self, memo):
        cls = type(self)
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, copy.deepcopy(v, memo))
        result.__unlink_objs()
        return result

    def clone(self):
        """Creates a complete independent copy of this problem.

        .. versionadded:: 0.5.0

        Returns
        -------
        MCNP_Problem
        """
        return copy.deepcopy(self)

    @property
    def cells(self):
        """A collection of the Cell objects in this problem.

        Returns
        -------
        Cells
            a collection of the Cell objects, ordered by the order they
            were in the input file.
        """
        self.__relink_objs()
        return self._cells

    @cells.setter
    @args_checked
    def cells(self, cells: ty.Iterable[montepy.Cell] | Cells):
        if not isinstance(cells, Cells):
            cells = Cells(cells)
        if cells is self.cells:
            return
        self.cells.clear()
        self.cells.extend(cells)

    @property
    def mode(self):
        """The mode of particles being used for the problem.

        Returns
        -------
        Mode
        """
        return self._mode

    def set_mode(self, particles: ty.Iterable[str] | str):
        """Sets the mode of problem to the given particles.

        For details see: :func:`montepy.data_cards.mode.Mode.set`.

        Parameters
        ----------
        particles : list, str
            the particles that the mode will be switched to.

        Raises
        ------
        ValueError
            if string is not a valid particle shorthand.
        """
        self._mode.set(particles)

    @property
    def mcnp_version(self):
        """The version of MCNP that this is intended for.

        Notes
        -----
        MCNP versions prior to 6.2 aren't fully supported to avoid
        Export Control Restrictions. Documentation for MCNP 6.2 is public in report:
        LA-UR-17-29981.
        All features are based on MCNP 6.2, and may cause other versions of MCNP to break.


        The version is a tuple of major, minor, revision.
        6.2.0 would be represented as (6, 2, 0)

        Returns
        -------
        tuple
        """
        return self._mcnp_version

    @mcnp_version.setter
    @args_checked
    def mcnp_version(self, version: ty.VersionType):
        """
        Parameters
        ----------
        version : tuple
            the version tuple. Must be greater than (5, 1, 60)
        """
        if version < (5, 1, 60):
            raise ValueError(f"The mcnp_version {version} is not supported by MontePy")
        self._mcnp_version = version

    @property
    def surfaces(self):
        """A collection of the Surface objects in this problem.

        Returns
        -------
        Surfaces
            a collection of the Surface objects, ordered by the order
            they were in the input file.
        """
        self.__relink_objs()
        return self._surfaces

    @surfaces.setter
    @args_checked
    def surfaces(self, surfs: ty.Iterable[montepy.Surface] | Surfaces):
        if not isinstance(surfs, Surfaces):
            surfs = Surfaces(surfs)
        surfs.link_to_problem(self)
        self._surfaces = surfs

    @property
    def materials(self):
        """A collection of the Material objects in this problem.

        Returns
        -------
        Materials
            a colection of the Material objects, ordered by the order
            they were in the input file.
        """
        self.__relink_objs()
        return self._materials

    @materials.setter
    @args_checked
    def materials(self, mats: ty.Iterable[montepy.Material] | Materials):
        if not isinstance(mats, Materials):
            mats = Materials(mats)
        mats.link_to_problem(self)
        self._materials = mats

    @property
    def print_in_data_block(self):
        """Controls whether or not the specific input gets printed in the cell block or the data block.

        This acts like a dictionary. The key is the case insensitive name of the card.
        For example to enable printing importance data in the data block run:

        ``problem.print_in_data_block["Imp"] = True``


        .. note::

           The default for this is ``False``,
           that is to print the data in the cell block if this was not set in the input file or by the user.

        .. versionchanged:: 1.0.0

            Default value changed to ``False``

        Returns
        -------
        dict[str, bool]
        """
        return self._print_in_data_block

    @property
    def data_inputs(self):
        """A list of the DataInput objects in this problem.

        Returns
        -------
        list
            a list of the
            :class:`~montepy.data_cards.data_card.DataCardAbstract`
            objects, ordered by the order they were in the input file.
        """
        self.__relink_objs()
        return self._data_inputs

    @property
    def input_file(self):
        """The file name of the original file name this problem was read from.

        Returns
        -------
        MCNP_InputFile
        """
        return self._input_file

    @property
    def message(self):
        """The Message object at the beginning of the problem if any.

        Returns
        -------
        Message
        """
        return self._message

    @property
    def title(self):
        """The Title object for the title.

        Returns
        -------
        Title
        """
        return self._title

    @title.setter
    @args_checked
    def title(self, title: str):
        """
        Parameters
        ----------
        title : The str for the title to be set to.
        """
        self._title = mcnp_input.Title([title], title)

    @property
    def universes(self):
        """The Universes object holding all problem universes.

        Returns
        -------
        Universes
            a collection of universes in the problem.
        """
        return self._universes

    @property
    def transforms(self):
        """The collection of transform objects in this problem.

        Returns
        -------
        Transforms
            a collection of transforms in the problem.
        """
        return self._transforms

    @args_checked
    def parse_input(
        self, check_input: bool = False, replace: bool = True, *, jit_parse: bool = True
    ):
        """Semantically parses the MCNP file provided to the constructor.

        .. versionchanged:: 1.2.0

            Added ``jit_parse`` argument

        Parameters
        ----------
        check_input : bool
            If true, will try to find all errors with input and collect
            them as warnings to log.
        replace : bool
            replace all non-ASCII characters with a space (0x20)
        jit_parse: bool
            Uses just-in-time (fast) parsing when True.
        """
        if self.input_file is None:
            return
        trailing_comment = None
        last_obj = None
        last_block = None
        OBJ_MATCHER = {
            block_type.BlockType.CELL: (Cell, self._cells),
            block_type.BlockType.SURFACE: (
                surface_builder.parse_surface,
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
                    if last_block != input.block_type:
                        trailing_comment = None
                        last_block = input.block_type
                    obj_parser, obj_container = OBJ_MATCHER[input.block_type]
                    if len(input.input_lines) > 0:
                        try:
                            obj = obj_parser(input, jit_parse=jit_parse)
                            obj.link_to_problem(self)
                            if isinstance(
                                obj_container,
                                montepy.numbered_object_collection.NumberedObjectCollection,
                            ):
                                obj_container.append(obj, initial_load=True)
                            else:
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
                            self._materials.append(obj, insert_in_data=False)
                        if isinstance(obj, transform.Transform):
                            self._transforms.append(obj, insert_in_data=False)
                    if not jit_parse:
                        if trailing_comment is not None and last_obj is not None:
                            obj._grab_beginning_comment(trailing_comment, last_obj)
                            last_obj._delete_trailing_comment()
                        trailing_comment = obj.trailing_comment
                        last_obj = obj
        except UnsupportedFeature as e:
            if check_input:
                warnings.warn(f"{type(e).__name__}: {e.message}", stacklevel=2)
            else:
                raise e
        self.__update_internal_pointers(check_input, jit_parse)

    def __update_internal_pointers(self, check_input=False, jit_parse=True):
        """Updates the internal pointers between objects

        Parameters
        ----------
        check_input : bool
            If true, will try to find all errors with input and collect
            them as warnings to log.
        """

        def handle_error(e):
            if check_input:
                warnings.warn(f"{type(e).__name__}: {e.message}", stacklevel=3)
            else:
                raise e

        self.__load_data_inputs_to_object(self._data_inputs)
        # TODO
        if jit_parse:
            return
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
            except (BrokenObjectLinkError,) as e:
                handle_error(e)
        to_delete = []
        for data_index, data_input in enumerate(self._data_inputs):
            try:
                if data_input.update_pointers(self._data_inputs):
                    to_delete.append(data_index)
            except (
                BrokenObjectLinkError,
                MalformedInputError,
            ) as e:
                handle_error(e)
                continue
        for delete_index in to_delete[::-1]:
            del self._data_inputs[delete_index]

    @args_checked
    def remove_duplicate_surfaces(self, tolerance: ty.PositiveReal):
        """Finds duplicate surfaces in the problem, and remove them.

        Parameters
        ----------
        tolerance : float
            The amount of relative error to consider two surfaces
            identical
        """
        to_delete = montepy.surface_collection.Surfaces()
        matching_map = {}
        for surface in self.surfaces:
            if surface not in to_delete:
                matches = surface.find_duplicate_surfaces(self.surfaces, tolerance)
                if matches:
                    for match in matches:
                        to_delete.add(match)
                        matching_map[match.number] = (match, surface)
        for cell in self.cells:
            cell.remove_duplicate_surfaces(matching_map)
        self.__update_internal_pointers()
        for surface in to_delete:
            self._surfaces.remove(surface)

    def add_cell_children_to_problem(self):  # pragma: no cover
        """Deprecated: Adds the surfaces, materials, and transforms of all cells in this problem to this problem to the
           internal lists to allow them to be written to file.

        .. deprecated:: 1.0.0

            This function is no longer needed. When cells are added to problem.cells these children are added as well.

        Raises
        ------
        DeprecationWarning
        """
        raise DeprecationWarning(
            "add_cell_children_to_problem has been removed,"
            " as the children are automatically added with the cell."
        )

    @args_checked
    def write_problem(
        self, destination: str | os.PathLike | io.TextIOBase, overwrite: bool = False
    ):
        """Write the problem to a file or writeable object.

        Parameters
        ----------
        destination : io.TextIOBase, str, os.PathLike
            File path or writable object
        overwrite : bool
            Whether to overwrite 'destination' if it is an existing file
        """
        if hasattr(destination, "write") and callable(getattr(destination, "write")):
            new_file = MCNP_InputFile.from_open_stream(destination)
            self._write_to_stream(new_file)
        elif isinstance(destination, (str, os.PathLike)):
            new_file = MCNP_InputFile(destination, overwrite=overwrite)
            with new_file.open("w") as fh:
                self._write_to_stream(fh)
        else:
            raise TypeError(
                f"destination f{destination} is not a file path or writable object"
            )

    @args_checked
    def write_to_file(self, file_path: str | os.PathLike, overwrite: bool = False):
        """Writes the problem to a file.

        .. versionchanged:: 0.3.0
            The overwrite parameter was added.

        Parameters
        ----------
        file_path : str, os.PathLike
            the file path to write this problem to
        overwrite : bool
            Whether to overwrite the file at 'new_problem' if it exists

        Raises
        ------
        IllegalState
            if an object in the problem has not been fully initialized.
        FileExistsError
            if a file already exists with the same path.
        IsADirectoryError
            if the path given is actually a directory.
        """
        return self.write_problem(file_path, overwrite)

    def _write_to_stream(self, inp):
        """Writes the problem to a writeable stream.

        Parameters
        ----------
        inp : MCNP_InputFile
            Writable input file
        """
        with warnings.catch_warnings(record=True) as warning_catch:
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
                            warning.lineno = inp.lineno
                            warning.path = inp.name
                            warning.obj = obj
                            warning.lines = lines
                            warning.handled = True
                    for line in lines:
                        inp.write(line + "\n")

                # writing cell data in DATA BLOCK if the last written object inherits DataInputAbstract and there is cell data to write
                if objects is self.data_inputs:
                    for line in self.cells._run_children_format_for_mcnp(
                        self.data_inputs, self.mcnp_version
                    ):
                        inp.write(line + "\n")
                elif terminate:
                    inp.write("\n")

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
            elif warning_level == WarningLevels.MAXIMAL:
                message += "\nThe new input is:\n"
                width = 15
                for i, line in enumerate(warning_message.lines):
                    message += f"     {warning_message.lineno + i:5g}| {line}\n"
                if hasattr(warning, "olds"):
                    message += (
                        f"\n    {'old values': ^{width}s} {'new values': ^{width}s}"
                    )
                    message += f"\n    {'':-^{width}s} {'':-^{width}s}\n"
                    for old, new in zip(warning.olds, warning.news):
                        formatter = f"    {{old: >{width}}} {{new: >{width}}}\n"
                        message += formatter.format(old=old, new=new)

            warning = LineExpansionWarning(message)
            warnings.warn(warning, stacklevel=3)

    def _get_leading_comment(self, obj):
        if isinstance(obj, Cell):
            return self.cells._get_leading_comment(obj)
        if isinstance(obj, surface.Surface):
            return self.surfaces._get_leading_comment(obj)
        # data inputs now
        try:
            idx = self.data_inputs.index(obj)
            if idx <= 0:
                return None
            comment = self.data_inputs[idx - 1].trailing_comment
            self.data_inputs[idx - 1]._delete_trailing_comment()
            return comment
        except ValueError as e:
            raise ValueError(f"Object: {obj} is not part of this problem.") from e

    def __load_data_inputs_to_object(self, data_inputs):
        """Loads data input into their appropriate problem attribute.

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
        for collection in [self.cells, self.surfaces, self.data_inputs]:
            for obj in collection:
                ret += f"{obj}\n"
            ret += "\n"
        return ret

    @args_checked
    def parse(self, input: str, append: bool = True) -> montepy.mcnp_object.MCNP_Object:
        """Parses the MCNP object given by the string, and links it adds it to this problem.

        This attempts to identify the input type by trying to parse it in the following order:

        #. Data Input
        #. Surface
        #. Cell

        This is done mostly for optimization to go from easiest parsing to hardest.
        This will:

        #. Parse the input
        #. Link it to other objects in the problem. Note: this will raise an error if those objects don't exist.
        #. Append it to the appropriate collection

        Parameters
        ----------
        input : str
            the string describing the input. New lines are allowed but
            this does not need to meet MCNP line length rules.
        append : bool
            Whether to append this parsed object to this problem.

        Returns
        -------
        MCNP_Object
            the parsed object.

        Raises
        ------
        TypeError
            If a str is not given
        ParsingError
            If this is not a valid input.
        BrokenObjectLinkError
            if the dependent objects are not already in the problem.
        NumberConflictError
            if the object's number is already taken
        """
        try:
            obj = montepy.parse_data(input)
        except ParsingError:
            try:
                obj = montepy.parse_surface(input)
            except ParsingError:
                obj = montepy.Cell(input)
                # let final parsing error bubble up
        obj.link_to_problem(self)
        if isinstance(obj, montepy.Cell):
            obj.update_pointers(self.cells, self.materials, self.surfaces)
            if append:
                self.cells.append(obj)
        elif isinstance(obj, montepy.surfaces.surface.Surface):
            obj.update_pointers(self.surfaces, self.data_inputs)
            if append:
                self.surfaces.append(obj)
        else:
            obj.update_pointers(self.data_inputs)
            if append:
                self.data_inputs.append(obj)
                if isinstance(obj, Material):
                    self._materials.append(obj, insert_in_data=False)
                if isinstance(obj, transform.Transform):
                    self._transforms.append(obj, insert_in_data=False)
        return obj

    def full_parse(self):
        for collection in [self.cells, self.surfaces, self.data_inputs]:
            for obj in collection:
                obj.full_parse()
        self.cells.update_pointers(
            self.cells, self.materials, self.surfaces, self.data_inputs, self
        )
