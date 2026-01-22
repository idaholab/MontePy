# Copyright 2024-2025, Battelle Energy Alliance, LLC All Rights Reserved.
import montepy
from montepy.numbered_object_collection import NumberedObjectCollection
from montepy.exceptions import *
import warnings
from numbers import Integral


class Cells(NumberedObjectCollection):
    """A collections of multiple :class:`montepy.cell.Cell` objects.

    This collection can be sliced to get a subset of the cells.
    Slicing is done based on the cell numbers, not their order in the input.
    For example, ``problem.cells[1:3]`` will return a new `Cells` collection
    containing cells with numbers from 1 to 3, inclusive.

    See also
    --------
    :class:`~montepy.numbered_object_collection.NumberedObjectCollection`


    Notes
    -----

    For examples see the ``NumberedObjectCollection`` :ref:`collect ex`.

    Parameters
    ----------
    cells : list
        the list of cells to start with if needed
    problem : MCNP_Problem
        the problem to link this collection to.
    """

    def __init__(self, cells=None, problem=None):
        self.__blank_modifiers = set()
        super().__init__(montepy.Cell, cells, problem)
        self.__setup_blank_cell_modifiers()

    def __setup_blank_cell_modifiers(self, problem=None, check_input=False):
        inputs_to_always_update = {"_universe", "_fill"}
        inputs_to_property = montepy.Cell._INPUTS_TO_PROPERTY
        for card_class, (attr, _) in inputs_to_property.items():
            try:
                if not hasattr(self, attr):
                    card = card_class()
                    self.__blank_modifiers.add(attr)
                    setattr(self, attr, card)
                else:
                    card = getattr(self, attr)
                if problem is not None:
                    card.link_to_problem(problem)
                    if (
                        attr not in self.__blank_modifiers
                        or attr in inputs_to_always_update
                    ):
                        card.push_to_cells()
                        card._clear_data()
            except MalformedInputError as e:
                if check_input:
                    warnings.warn(f"{type(e).__name__}: {e.message}", stacklevel=3)
                    continue
                else:
                    raise e

    def set_equal_importance(self, importance, vacuum_cells=tuple()):
        """Sets all cells except the vacuum cells to the same importance using :func:`montepy.data_cards.importance.Importance.all`.

        The "vacuum" cells are those on the outside of a vacuum boundary condition, i.e., the "graveyard".
        That is to say, their importance will be set to 0.0. You can specify cell numbers or cell objects.

        Parameters
        ----------
        importance : float
            the importance to apply to all cells
        vacuum_cells : list
            the list of cells or cell numbers with 0 importance
        """
        if not isinstance(vacuum_cells, (list, tuple, set)):
            raise TypeError("vacuum_cells must be a list or set")
        cells_buff = set()
        for cell in vacuum_cells:
            if not isinstance(cell, (montepy.Cell, Integral)):
                raise TypeError("vacuum cell must be a Cell or a cell number")
            if isinstance(cell, Integral):
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
        """Whether or not MCNP is allowed to automatically calculate cell volumes.

        Returns
        -------
        bool
            true if MCNP will attempt to calculate cell volumes
        """
        return self._volume.is_mcnp_calculated

    @allow_mcnp_volume_calc.setter
    def allow_mcnp_volume_calc(self, value):
        if not isinstance(value, bool):
            raise TypeError("allow_mcnp_volume_calc must be set to a bool")
        self._volume.is_mcnp_calculated = value

    def link_to_problem(self, problem):
        """Links the input to the parent problem for this input.

        This is done so that inputs can find links to other objects.

        Parameters
        ----------
        problem : MCNP_Problem
            The problem to link this input to.
        """
        super().link_to_problem(problem)
        inputs_to_property = montepy.Cell._INPUTS_TO_PROPERTY
        for attr, _ in inputs_to_property.values():
            getattr(self, attr).link_to_problem(problem)

    def update_pointers(
        self, cells, materials, surfaces, data_inputs, problem, check_input=False
    ):
        """Attaches this object to the appropriate objects for surfaces and materials.

        This will also update each cell with data from the data block,
        for instance with cell volume from the data block.

        Parameters
        ----------
        cells : Cells
            a Cells collection of the cells in the problem.
        materials : Materials
            a materials collection of the materials in the problem
        surfaces : Surfaces
            a surfaces collection of the surfaces in the problem
        problem : MCNP_Problem
            The MCNP_Problem these cells are associated with
        check_input : bool
            If true, will try to find all errors with input and collect
            them as warnings to log.
        """

        def handle_error(e):
            if check_input:
                warnings.warn(f"{type(e).__name__}: {e.message}", stacklevel=3)
            else:
                raise e

        inputs_to_property = montepy.Cell._INPUTS_TO_PROPERTY
        inputs_to_always_update = {"_universe", "_fill"}
        inputs_loaded = set()
        # start fresh for loading cell modifiers
        for attr in self.__blank_modifiers:
            delattr(self, attr)
        self.__blank_modifiers = set()
        # make a copy of the list
        for input in list(data_inputs):
            if type(input) in inputs_to_property:
                input_class = type(input)
                attr, cant_repeat = inputs_to_property[input_class]
                if cant_repeat and input_class in inputs_loaded:
                    try:
                        raise MalformedInputError(
                            input,
                            f"The input: {type(input)} is only allowed once in a problem",
                        )
                    except MalformedInputError as e:
                        handle_error(e)
                if not hasattr(self, attr):
                    setattr(self, attr, input)
                    problem.print_in_data_block[input._class_prefix()] = True
                else:
                    try:
                        getattr(self, attr).merge(input)
                        data_inputs.remove(input)
                    except MalformedInputError as e:
                        handle_error(e)
                if cant_repeat:
                    inputs_loaded.add(type(input))
        for cell in self:
            try:
                cell.update_pointers(cells, materials, surfaces)
            except (
                BrokenObjectLinkError,
                MalformedInputError,
            ) as e:
                handle_error(e)
                continue
        self.__setup_blank_cell_modifiers(problem, check_input)

    def _run_children_format_for_mcnp(self, data_inputs, mcnp_version):
        ret = []
        for attr, _ in montepy.Cell._INPUTS_TO_PROPERTY.values():
            if getattr(self, attr) not in data_inputs:
                if buf := getattr(self, attr).format_for_mcnp_input(mcnp_version):
                    ret += buf
        return ret

    def clone(
        self, clone_material=False, clone_region=False, starting_number=None, step=None
    ):
        """Create a new instance of this collection, with all new independent
        objects with new numbers.

        This relies mostly on ``copy.deepcopy``.

        Notes
        -----
        If starting_number, or step are not specified :func:`starting_number`,
        and :func:`step` are used as default values.


        .. versionadded:: 0.5.0

        .. versionchanged:: 1.0.0

            Added ``clone_material`` and ``clone_region``.

        Parameters
        ----------
        clone_material : bool
            Whether to create a new clone of the materials for the
            cells.
        clone_region : bool
            Whether to clone the underlying objects (Surfaces, Cells) of
            these cells' region.
        starting_number : int
            The starting number to request for a new object numbers.
        step : int
            the step size to use to find a new valid number.

        Returns
        -------
        type(self)
            a cloned copy of this object.
        """
        if not isinstance(starting_number, (Integral, type(None))):
            raise TypeError(
                f"Starting_number must be an int. {type(starting_number)} given."
            )
        if not isinstance(step, (Integral, type(None))):
            raise TypeError(f"step must be an int. {type(step)} given.")
        if starting_number is not None and starting_number <= 0:
            raise ValueError(f"starting_number must be >= 1. {starting_number} given.")
        if step is not None and step <= 0:
            raise ValueError(f"step must be >= 1. {step} given.")
        if starting_number is None:
            starting_number = self.starting_number
        if step is None:
            step = self.step
        objs = []
        for obj in list(self):
            new_obj = obj.clone(
                clone_material, clone_region, starting_number, step, add_collect=False
            )
            starting_number = new_obj.number
            objs.append(new_obj)
            starting_number = new_obj.number + step
        return type(self)(objs)
