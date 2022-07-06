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

    def update_pointers(self, cells, materials, surfaces, data_cards, problem):
        cards_to_property = {importance.Importance: ("_importance", False)}
        cards_loaded = set()
        for card in data_cards:
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
                    card.link_to_problem(problem)
                else:
                    getattr(self, attr).merge(card)
                if cant_repeat:
                    cards_loaded.add(type(card))
        for cell in self:
            cell.update_pointers(cells, materials, surfaces)
        for attr, foo in cards_to_property.values():
            if hasattr(self, attr):
                getattr(self, attr).push_to_cells()
                getattr(self, attr)._clear_data()
