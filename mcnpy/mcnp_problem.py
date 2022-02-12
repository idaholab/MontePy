from mcnpy.cell import Cell
from mcnpy.surfaces import surface_builder
from mcnpy.data_cards import material, data_card, data_parser
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
        self.__input_file = file_name
        self.__original_inputs = []
        self.__cells = []
        self.__surfaces = []
        self.__data_cards = []
        self.__materials = []
        self.__title = None
        self.__message = None
        self.__mcnp_version = (6.2, 0)

    @property
    def original_inputs(self):
        """
        A list of the MCNP_Inputs read from the original file.

        This should not be mutated, and should be used a reference to maintain
        the structure

        :return: A list of the MCNP_Input objects representing the file as it was read
        :rtype: list
        """
        return self.__original_inputs

    @property
    def cells(self):
        """
        A list of the Cell objects in this problem.

        :return: a list of the Cell objects, ordered by the order they were in the input file.
        :rtype: list
        """
        return self.__cells

    @cells.setter
    def cells(self, cells):
        assert isinstance(cells, list)
        for cell in cells:
            assert isinstance(cell, Cell)
        self.__cells = cells

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

        The version is a tuple of the major and minor revisions combined.
        6.2.0 would be represented as (6.2, 0)
        :rtype: tuple
        """
        return self.__mcnp_version

    @mcnp_version.setter
    def mcnp_version(self, version):
        """
        :param version: the version tuple. Must be greater than 6.2.0
        :type version: tuple
        """
        assert version >= (6.2, 0)
        self.__mcnp_version = version

    @property
    def surfaces(self):
        """
        A list of the Surface objects in this problem.

        :return: a list of the Surface objects, ordered by the order they were in the input file.
        :rtype: list
        """
        return self.__surfaces

    @property
    def materials(self):
        """
        A list of the Material objects in this problem.

        :return: a list of the Material objects, ordered by the order they were in the input file.
        :rtype: list
        """
        return self.__materials

    @property
    def data_cards(self):
        """
        A list of the DataCard objects in this problem.

        :return: a list of the DataCard objects, ordered by the order they were in the input file.
        :rtype: list
        """
        return self.__data_cards

    @property
    def input_file(self):
        """
        The file name of the original file name this problem was read from.

        :rtype: str
        """
        return self.__input_file

    @property
    def message(self):
        """
        The Message object at the beginning of the problem if any.

        :rtype: Message
        """
        if hasattr(self, "_MCNP_Problem__message"):
            return self.__message

    @property
    def title(self):
        """
        The Title object for the title.

        :rtype: Title
        """
        return self.__title

    @title.setter
    def title(self, title):
        """
        :type title: The str for the title to be set to.
        """
        self.__title = mcnp_input.Title(title)

    def parse_input(self):
        """
        Semantically parses the MCNP file provided to the constructor.
        """
        comment_queue = None
        for i, input_card in enumerate(
            input_syntax_reader.read_input_syntax(self.__input_file)
        ):
            self.__original_inputs.append(input_card)
            if i == 0 and isinstance(input_card, mcnp_input.Message):
                self.__message = input_card

            elif isinstance(input_card, mcnp_input.Title) and self.title is None:
                self.__title = input_card

            elif isinstance(input_card, mcnp_input.Comment):
                comment_queue = input_card

            elif isinstance(input_card, mcnp_input.Card):
                if len(input_card.words) > 0:
                    if input_card.block_type == block_type.BlockType.CELL:
                        cell = Cell(input_card, comment_queue)
                        self.__cells.append(cell)
                    if input_card.block_type == block_type.BlockType.SURFACE:
                        surface = surface_builder.surface_builder(
                            input_card, comment_queue
                        )
                        self.__surfaces.append(surface)
                    if input_card.block_type == block_type.BlockType.DATA:
                        data = data_parser.parse_data(input_card, comment_queue)
                        self.__data_cards.append(data)
                        if isinstance(data, material.Material):
                            self.__materials.append(data)
                    comment_queue = None
        self.__update_internal_pointers()

    def __update_internal_pointers(self):
        """Updates the internal pointers between objects"""
        material_dict = {}
        surface_dict = {}
        cell_dict = {}
        for mat in self.__materials:
            material_dict[mat.old_material_number] = mat
        for surface in self.__surfaces:
            surface_dict[surface.old_surface_number] = surface
        for cell in self.__cells:
            cell_dict[cell.old_cell_number] = cell
        # update links
        for cell in self.__cells:
            cell.update_pointers(cell_dict, material_dict, surface_dict)
        for surface in self.__surfaces:
            surface.update_pointers(surface_dict, self.__data_cards)
        for card in self.__data_cards:
            card.update_pointers(self.__data_cards)

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
            self.__surfaces.remove(surface)

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
        self.__surfaces = surfaces
        self.__materials = materials
        self.__data_cards = list(set(self.__data_cards + materials))

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
            for cell in self.cells:
                for line in cell.format_for_mcnp_input(self.mcnp_version):
                    fh.write(line + "\n")
            # block terminator
            fh.write("\n")
            for surface in self.surfaces:
                for line in surface.format_for_mcnp_input(self.mcnp_version):
                    fh.write(line + "\n")
            fh.write("\n")

            for card in self.data_cards:
                for line in card.format_for_mcnp_input(self.mcnp_version):
                    fh.write(line + "\n")

            fh.write("\n")

    def __str__(self):
        ret = f"MCNP problem for: {self.__input_file}\n"
        if self.message:
            ret += str(self.__message) + "\n"
        ret += str(self.__title) + "\n"
        for cell in self.__cells:
            ret += str(cell) + "\n"
        for data_card in self.__data_cards:
            if not isinstance(data_card, material.Material):
                ret += str(data_card) + "\n"
        return ret
