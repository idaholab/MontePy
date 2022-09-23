import mcnpy
from mcnpy.numbered_object_collection import NumberedObjectCollection
from mcnpy.errors import MalformedInputError


class Cells(NumberedObjectCollection):
    """A collections of multiple :class:`mcnpy.cell.Cell` objects."""

    def __init__(self, cells=None):
        """
        :param cells: the list of cells to start with if needed
        :type cells: list
        """
        super().__init__(mcnpy.Cell, cells)

    def set_equal_importance(self, importance, vacuum_cells=tuple()):
        """
        Sets all cells except the vacuum cells to the same importance using importance.all.

        The vacuum cells will be set to 0.0. You can specify cell numbers or cell objects.

        :param importance: the importance to apply to all cells
        :type importance: float
        :param vacuum_cells: the cells that are the vacuum boundary with 0 importance
        :type vacuum_cells: list
        """
        if not isinstance(vacuum_cells, (list, tuple, set)):
            raise TypeError("vacuum_cells must be a list or set")
        cells_buff = set()
        for cell in vacuum_cells:
            if not isinstance(cell, (mcnpy.Cell, int)):
                raise TypeError("vacuum cell must be a Cell or a cell number")
            if isinstance(cell, int):
                cells_buff.add(self[cell])
            else:
                cells_buff.add(cell)
        vacuum_cells = cells_buff
        for cell in self:
            if cell not in vacuum_cells:
                cell.importance.all = importance
        for cell in vacuum_cells:
            cell.importance.all = 0.0

    @property
    def allow_mcnp_volume_calc(self):
        """
        Whether or not MCNP is allowed to automatically calculate cell volumes.

        :returns: true if MCNP will attempt to calculate cell volumes
        :rtype: bool
        """
        return self._volume.is_mcnp_calculated

    @allow_mcnp_volume_calc.setter
    def allow_mcnp_volume_calc(self, value):
        if not isinstance(value, bool):
            raise TypeError("allow_mcnp_volume_calc must be set to a bool")
        self._volume.is_mcnp_calculated = value

    def update_pointers(self, cells, materials, surfaces, data_cards, problem):
        cards_to_property = mcnpy.Cell._CARDS_TO_PROPERTY
        cards_to_always_update = {"_universe", "_fill"}
        cards_loaded = set()
        # make a copy of the list
        for card in list(data_cards):
            if type(card) in cards_to_property:
                card_class = type(card)
                attr, cant_repeat = cards_to_property[card_class]
                if cant_repeat and card_class in cards_loaded:
                    raise MalformedInputError(
                        card,
                        f"The card: {type(card)} is only allowed once in a problem",
                    )
                if not hasattr(self, attr):
                    setattr(self, attr, card)
                    problem.print_in_data_block[card.class_prefix] = True
                else:
                    getattr(self, attr).merge(card)
                    data_cards.remove(card)
                if cant_repeat:
                    cards_loaded.add(type(card))
        for cell in self:
            cell.update_pointers(cells, materials, surfaces)
        for attr, _ in cards_to_property.values():
            prop = getattr(self, attr, None)
            if prop is None:
                continue
            prop.push_to_cells()
            prop._clear_data()
        for card_class, (attr, _) in cards_to_property.items():
            if not hasattr(self, attr):
                card = card_class()
                card.link_to_problem(problem)
                if attr in cards_to_always_update:
                    card.push_to_cells()
                card._mutated = False
                setattr(self, attr, card)

    def _run_children_format_for_mcnp(self, data_cards, mcnp_version):
        ret = []
        for attr, _ in mcnpy.Cell._CARDS_TO_PROPERTY.values():
            if getattr(self, attr) not in data_cards:
                ret += getattr(self, attr).format_for_mcnp_input(mcnp_version)
        return ret
