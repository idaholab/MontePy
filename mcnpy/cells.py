import mcnpy
from mcnpy.data_cards import importance
from mcnpy.numbered_object_collection import NumberedObjectCollection


class Cells(NumberedObjectCollection):
    """A collections of multiple :class:`mcnpy.cell.Cell` objects."""

    def __init__(self, cells=None):
        """
        :param cells: the list of cells to start with if needed
        :type cells: list
        """
        super().__init__(mcnpy.Cell, cells)

    def set_equal_importance(self, importance, vacuum_cells=[]):
        """
        Sets all cells except the vacuum cells to the same importance using importance.all.

        The vacuum cells will be set to 0.0. You can specify cell numbers or cell objects.

        :param importance: the importance to apply to all cells
        :type importance: float
        :param vacuum_cells: the cells that are the vacuum boundary with 0 importance
        :type vacuum_cells: list
        """
        if not isinstance(importance, float):
            raise TypeError("Importance must be a float")
        if importance <= 0.0:
            raise ValueError("Importance must be > 0.0")
        if not isinstance(vacuum_cells, (list, set)):
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
                cell.all = importance
        for cell in vacuum_cells:
            cell.all = 0.0

    def update_pointers(self, cells, materials, surfaces, data_cards):
        cards_to_property = {importance.Importance: ("_importance", False)}
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
                else:
                    getattr(self, attr).merge(card)
                    data_cards.remove(card)
                if cant_repeat:
                    cards_loaded.add(type(card))
        for cell in self:
            cell.update_pointers(cells, materials, surfaces)
        for attr, foo in cards_to_property.values():
            if hasattr(self, attr):
                getattr(self, attr).push_to_cells()
                getattr(self, attr)._clear_data()
