from mcnpy.cell import Cell
from mcnpy.cells import Cells
from mcnpy.errors import NumberConflictError
from mcnpy.materials import Materials
from mcnpy.surfaces import surface_builder
from mcnpy.surface_collection import Surfaces
from mcnpy.data_cards import Material, parse_data
from mcnpy.input_parser import input_syntax_reader, block_type, mcnp_input


class MCNP_Problem:
    """
    A class to represent an entire MCNP problem in a semantic way.
    """

    def __init__(self, file_name):
        """
        :param file_name: the path to the file that will be read.
        :type file_name: str
        """
        self._input_file = file_name
        self._title = None
        self._message = None
        self._original_inputs = []
        self._cells = Cells()
        self._surfaces = Surfaces()
        self._data_cards = []
        self._materials = Materials()
        self._mcnp_version = (6, 2, 0)

    @property
    def original_inputs(self):
        """
        A list of the MCNP_Inputs read from the original file.

        This should not be mutated, and should be used a reference to maintain
        the structure

        :return: A list of the MCNP_Input objects representing the file as it was read
        :rtype: list
        """
        return self._original_inputs

    @property
    def cells(self):
        """
        A list of the Cell objects in this problem.

        :return: a list of the Cell objects, ordered by the order they were in the input file.
        :rtype: list
        """
        return self._cells

    @cells.setter
    def cells(self, cells):
        assert type(cells) in [Cells, list]
        if isinstance(cells, list):
            for cell in cells:
                assert isinstance(cell, Cell)
            cells = Cells(cells)
        self._cells = cells

    def add_cells(self, cells):
        """
        Adds the given cells to the problem and all owned surfaces and materials as well.

        This will guarantee there are no naming collisions. If a collison is detected an exception is thrown.
        :param cells: The list of Cell objects to add to this problem.
        :type cells: list
        """
        pass

    @property
    def mcnp_version(self):
        """
        The version of MCNP that this is intended for.

        MCNP versions prior to 6.2 aren't officially supported to avoid
        Export Control Restrictions. Documentation for MCNP 6.2 is public in report:
            LA-UR-17-29981

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
        assert version >= (6, 2, 0)
        self._mcnp_version = version

    @property
    def surfaces(self):
        """
        A list of the Surface objects in this problem.

        :return: a list of the Surface objects, ordered by the order they were in the input file.
        :rtype: list
        """
        return self._surfaces

    @property
    def materials(self):
        """
        A list of the Material objects in this problem.

        :return: a list of the Material objects, ordered by the order they were in the input file.
        :rtype: list
        """
        return self._materials

    @materials.setter
    def materials(self, mats):
        assert type(mats) in [list, Materials]
        for mat in mats:
            assert isinstance(mat, Material)
        if isinstance(mats, list):
            mats = Materials(mats)
        self._materials = mats

    @property
    def data_cards(self):
        """
        A list of the DataCard objects in this problem.

        :return: a list of the DataCard objects, ordered by the order they were in the input file.
        :rtype: list
        """
        return self._data_cards

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

    def parse_input(self):
        """
        Semantically parses the MCNP file provided to the constructor.
        """
        comment_queue = None
        for i, input_card in enumerate(
            input_syntax_reader.read_input_syntax(self._input_file)
        ):
            self._original_inputs.append(input_card)
            if i == 0 and isinstance(input_card, mcnp_input.Message):
                self._message = input_card

            elif isinstance(input_card, mcnp_input.Title) and self._title is None:
                self._title = input_card

            elif isinstance(input_card, mcnp_input.Comment):
                comment_queue = input_card

            elif isinstance(input_card, mcnp_input.Card):
                if len(input_card.words) > 0:
                    if input_card.block_type == block_type.BlockType.CELL:
                        cell = Cell(input_card, comment_queue)
                        cell.link_to_problem(self)
                        self._cells.append(cell)
                    if input_card.block_type == block_type.BlockType.SURFACE:
                        surface = surface_builder.surface_builder(
                            input_card, comment_queue
                        )
                        surface.link_to_problem(self)
                        self._surfaces.append(surface)
                    if input_card.block_type == block_type.BlockType.DATA:
                        data = parse_data(input_card, comment_queue)
                        data.link_to_problem(self)
                        self._data_cards.append(data)
                        if isinstance(data, Material):
                            self._materials.append(data)
                    comment_queue = None
        self.__update_internal_pointers()

    def __update_internal_pointers(self):
        """Updates the internal pointers between objects"""
        for cell in self._cells:
            cell.update_pointers(self.cells, self.materials, self.surfaces)
        for surface in self._surfaces:
            surface.update_pointers(self.surfaces, self._data_cards)
        for card in self._data_cards:
            card.update_pointers(self._data_cards)

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
        Adds the surfaces and materials added to this problem to the
        internal lists to allow them to be written to file.

        WARNING: this does not move transforms and complement cells, and probably others.
        """
        surfaces = set(self.surfaces)
        materials = set(self.materials)
        for cell in self.cells:
            surfaces.update(set(cell.surfaces))
            if cell.material:
                materials.add(cell.material)
        surfaces = sorted(list(surfaces))
        materials = sorted(list(materials))
        self._surfaces = Surfaces(surfaces)
        self._materials = Materials(materials)
        self._data_cards = sorted(list(set(self._data_cards + materials)))

    def write_to_file(self, new_problem):
        """
        Writes the problem to a file.

        :param new_problem: the file name to write this problem to
        :type new_problem: str
        """
        with open(new_problem, "w") as fh:
            if self.message:
                for line in self.message.format_for_mcnp_input(self.mcnp_version):
                    fh.write(line + "\n")
            lines = self.title.format_for_mcnp_input(self.mcnp_version)
            fh.write(lines[0] + "\n")
            cell_numbers = {}
            if self.cells.check_redundant_numbers():
                # find the problem cells
                for cell in self.cells:
                    if cell.number in cell_numbers:
                        raise NumberConflictError(
                            f"The cells {cell}, and {cell_numbers[cell.number]}"
                            " have the same cell number"
                        )
                    cell_numbers[cell.number] = cell
            for cell in self.cells:
                for line in cell.format_for_mcnp_input(self.mcnp_version):
                    fh.write(line + "\n")
            # block terminator
            fh.write("\n")
            surf_numbers = {}
            if self.surfaces.check_redundant_numbers():
                for surface in self.surfaces:
                    if surface.number in surf_numbers:
                        raise NumberConflictError(
                            f"The surfaces {surface}, and {surf_numbers[surface.number]}"
                            " have the same surface number"
                        )
                    surf_numbers[surface.number] = surface
            for surface in self.surfaces:
                for line in surface.format_for_mcnp_input(self.mcnp_version):
                    fh.write(line + "\n")
            fh.write("\n")
            mat_numbers = {}
            if self.materials.check_redundant_numbers():
                for mat in self.materials:
                    if mat.number in mat_numbers:
                        raise NumberConflictError(
                            f"The Materials {mat}, and {mat_numbers[mat.number]}"
                            " have the same material number"
                        )
                    mat_numbers[mat.number] = mat
            for card in self.data_cards:
                for line in card.format_for_mcnp_input(self.mcnp_version):
                    fh.write(line + "\n")

            fh.write("\n")

    def __str__(self):
        ret = f"MCNP problem for: {self._input_file}\n"
        if self.message:
            ret += str(self._message) + "\n"
        ret += str(self._title) + "\n"
        for cell in self._cells:
            ret += str(cell) + "\n"
        for data_card in self._data_cards:
            if not isinstance(data_card, Material):
                ret += str(data_card) + "\n"
        return ret
