# Copyright 2024-2026, Battelle Energy Alliance, LLC All Rights Reserved.
"""Builds an :class:`~montepy.MCNP_Problem` from an OpenMC ``model.xml`` file.

Only the geometry and the materials are converted.
OpenMC is not needed: the XML file is read directly.
"""

from __future__ import annotations

import math
import os
import re
import warnings
import xml.etree.ElementTree as ET

import numpy as np

import montepy
from montepy._check_value import args_checked
from montepy.constants import BLANK_SPACE_CONTINUE
from montepy.exceptions import UnsupportedFeature
from montepy.geometry_operators import Operator
from montepy.input_parser.syntax_node import CommentNode, PaddingNode
from montepy.surfaces.half_space import UnitHalfSpace

DEFAULT_SAB_REGISTER = {
    "c_Al27": "al27.22t",
    "c_Be": "be.20t",
    "c_Be_in_BeO": "be-o.20t",
    "c_C6H6": "benz.20t",
    "c_D_in_D2O": "hwtr.20t",
    "c_Fe56": "fe56.22t",
    "c_Graphite": "grph.20t",
    "c_H_in_CH2": "poly.20t",
    "c_H_in_CH4_liquid": "lmeth.20t",
    "c_H_in_CH4_solid": "smeth.20t",
    "c_H_in_H2O": "lwtr.20t",
    "c_H_in_ZrH": "h-zr.20t",
    "c_O_in_BeO": "o-be.20t",
    "c_O_in_UO2": "o2-u.20t",
    "c_SiO2_alpha": "sio2.30t",
    "c_U_in_UO2": "u-o2.30t",
    "c_Zr_in_ZrH": "zr-h.30t",
    "c_ortho_D": "dortho.20t",
    "c_ortho_H": "hortho.20t",
    "c_para_D": "dpara.20t",
    "c_para_H": "hpara.20t",
}
"""The default thermal scattering (:math:`S(\\alpha,\\beta)`) tables to use for the OpenMC tables.

The keys are the names of the tables in OpenMC (e.g., ``c_H_in_H2O``),
and the values are the identifiers for the ``MT`` input in MCNP (e.g., ``lwtr.20t``).

These are the tables of the ``ENDF71SaB`` library, as listed in Table 7 of
"Listing of Available ACE Data Tables" (LA-UR-17-20709), which was Appendix G of the MCNP manual.
For each material this is the table at 293.6 K,
or the only table that there is for the cold moderators (methane, and ortho/para hydrogen and deuterium).
The temperature of the OpenMC material is not used.

.. versionadded:: 1.6.0
"""

_THERMAL_LAW = re.compile(r"[a-z][a-z\d/-]+\.\d+[a-z]", re.I)
"""What an identifier of a thermal scattering table has to look like, e.g., ``lwtr.20t``."""

_MAX_COMMENT_LENGTH = 75

_GEOMETRY_WIDTH = 80
"""The column that a new cell's geometry is wrapped at.

This is the line length that all versions of MCNP accept. It also leaves room on the last line for the
cell's parameters.
"""

_REGION_TOKEN = re.compile(r"[()|~]|[+-]?\d+")

_NUCLIDE_NAME = re.compile(r"(?P<symbol>[A-Za-z]{1,2})(?P<A>\d+)(_m(?P<meta>\d+))?")

_AXES = "xyz"


@args_checked
def from_model_xml(
    path: str | os.PathLike,
    library: str | montepy.Library = None,
    sab_register: dict[str, str] = None,
    graveyard: bool = True,
) -> montepy.MCNP_Problem:
    """Creates an MCNP problem from an OpenMC ``model.xml`` file.

    Only the geometry and the materials are converted;
    the ``settings``, ``tallies``, and ``plots`` are ignored.
    OpenMC does not need to be installed.

    The objects keep their OpenMC IDs as their MCNP numbers:
    cell ``5`` is ``problem.cells[5]``, and so on for surfaces, materials, and universes.
    The names of the OpenMC objects are kept as comments.

    Examples
    --------

    .. code-block:: python

        import montepy

        problem = montepy.from_model_xml("model.xml")
        problem.write_problem("model.imcnp")

    OpenMC's XML does not say which nuclear data library to use.
    All of the nuclides can be given a library, so ``92235`` becomes ``92235.80c``:

    .. code-block:: python

        problem = montepy.from_model_xml("model.xml", library=".80c")

    The thermal scattering tables are found in a register: a dictionary of the name
    of each OpenMC table, and the MCNP table to use for it.
    To change the default register, e.g., to use light water at 600 K:

    .. code-block:: python

        from montepy.input_parser.openmc_reader import DEFAULT_SAB_REGISTER

        register = DEFAULT_SAB_REGISTER | {"c_H_in_H2O": "lwtr.26t"}
        problem = montepy.from_model_xml("model.xml", sab_register=register)

    Notes
    -----

    OpenMC and MCNP do not describe a model in exactly the same way,
    so the following choices are made:

    * The root universe becomes universe 0, which is the "real world" in MCNP.
    * A graveyard cell with a neutron importance of 0 is added. It is the complement of all
      of the cells of the root universe, and has the next free cell number.
      This plays the role of the ``vacuum`` boundary condition in OpenMC, which is not
      a property of a surface in MCNP.
      Set ``graveyard`` to False to not add this cell, and then add one yourself.
      Without one the problem can not be run in MCNP.
    * ``reflective``, ``white``, and ``periodic`` boundary conditions are set on the surfaces.
    * The density of an OpenMC material is set on each cell that is filled with that material.
    * Nuclides only have a library (e.g., ``92235.80c``) if ``library`` is given.
      See also :func:`~montepy.Material.change_libraries` and :attr:`~montepy.Materials.default_libraries`.
    * A thermal scattering (:math:`S(\\alpha,\\beta)`) table of a material becomes an ``MT`` input, with the MCNP
      table from ``sab_register``. A table that is not in the register is not converted, and a warning is given.
      The default register, :data:`DEFAULT_SAB_REGISTER`, uses the tables for 293.6 K
      no matter what the temperature of the material is.
    * The ``translation`` and ``rotation`` of a filled cell becomes a fill transform: ``FILL=1 (1 0 0)``.
    * A cell complement (``~``) is expanded with De Morgan's laws, so no ``#`` is used.
    * A cell with no region is given both sides of one new plane (e.g., ``12 : -12``),
      because an MCNP cell must have a geometry. So it is still all of space.
    * A rectangular lattice becomes a ``LAT=1`` cell in a new universe.
      That universe then fills the universe with the lattice's ID with a translation,
      so that the lattice elements are where they are in OpenMC.
      An ``outer`` universe becomes a second lattice, that is used around the first one.

    These are not converted, and are silently ignored: temperatures and volumes.

    These are not supported for now, and an :class:`~montepy.exceptions.UnsupportedFeature` error is raised:
    hexagonal lattices, DAGMC universes, distributed materials, and multi-group (macroscopic) materials.

    See Also
    --------

    * Materials (``M``): :manual63:`5.6.1`, :manual62:`106`
    * Thermal scattering (``MT``): :manual63:`5.6.2`, :manual62:`110`
    * Universes (``U``): :manual63sub:`5.5.5.1`, :manual62:`82`
    * Fills (``FILL``): :manual63sub:`5.5.5.3`, :manual62:`86`

    .. versionadded:: 1.6.0

    Parameters
    ----------
    path : str, os.PathLike
        The path to the ``model.xml`` file made by OpenMC.
    library : str, Library
        The nuclear data library to use for all of the nuclides, e.g., ``"80c"``.
        A leading period is allowed: ``".80c"``. If None the nuclides have no library.
    sab_register : dict[str, str]
        The MCNP thermal scattering table (e.g., ``"lwtr.20t"``) to use for each
        OpenMC thermal scattering table (e.g., ``"c_H_in_H2O"``).
        This is used in the place of :data:`DEFAULT_SAB_REGISTER`, and not on top of it.
    graveyard : bool
        Whether to add a graveyard cell: a cell with an importance of 0
        that is everything outside of the cells of the root universe.

    Returns
    -------
    MCNP_Problem
        The new problem with the cells, surfaces, and materials of the model.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    TypeError
        If an argument is of the wrong type.
    ValueError
        If the file is not a valid OpenMC model, or if ``library`` or a table in ``sab_register`` is not valid.
    UnsupportedFeature
        If the model uses an OpenMC feature that can not be converted.
    """
    if isinstance(library, str):
        library = montepy.Library(library.removeprefix("."))
    if sab_register is None:
        sab_register = DEFAULT_SAB_REGISTER
    for name, law in sab_register.items():
        if not _THERMAL_LAW.fullmatch(law):
            raise ValueError(
                f"{law!r} is not a valid thermal scattering table for {name!r}. "
                'It must be like: "lwtr.20t".'
            )
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as e:
        raise ValueError(f"{path} is not a valid XML file: {e}") from e
    if root.tag != "model":
        raise ValueError(
            f"{path} is not an OpenMC model.xml file. "
            f"The root element is <{root.tag}> and not <model>."
        )
    geometry = root.find("geometry")
    if geometry is None:
        raise ValueError(f"{path} has no <geometry> element.")
    problem = montepy.MCNP_Problem()
    title = f"Converted from the OpenMC model: {os.path.basename(os.fspath(path))}"
    problem.title = _clean_text(title)
    converter = _ModelConverter(
        problem, root.find("materials"), geometry, library, sab_register
    )
    converter.convert(graveyard)
    return problem


def _get(elem: ET.Element, name: str, default: str = None) -> str | None:
    """Gets a value that can be either an attribute or a sub-element, as OpenMC does."""
    value = elem.get(name)
    if value is None:
        child = elem.find(name)
        if child is not None:
            value = child.text
    if value is None:
        return default
    return value.strip()


def _get_id(elem: ET.Element) -> int:
    value = _get(elem, "id")
    if value is None:
        raise ValueError(f"A <{elem.tag}> element has no id.")
    return int(value)


def _floats(text: str) -> list[float]:
    return [float(value) for value in text.split()]


def _clean_text(text: str) -> str:
    """Makes text safe to be on a single line of an MCNP input."""
    text = " ".join(text.split())
    text = text.encode("ascii", errors="replace").decode("ascii")
    return text[:_MAX_COMMENT_LENGTH]


def _set_comment(obj: montepy.mcnp_object.MCNP_Object, text: str):
    """Sets the leading comment of the object, if there is any text."""
    if text:
        text = _clean_text(text)
    if text:
        obj.leading_comments = [CommentNode(f"c {text}")]


def _load_float(node, value: float, negative: bool = False):
    """Loads a value into a new node, as though it had been read from an input file.

    A new float is otherwise written with up to 18 digits (e.g., ``12.699999999999999``),
    or for a transform with only 6 digits.
    This way the shortest text that is exactly this value (e.g., ``12.7``) is written.

    Parameters
    ----------
    node : ValueNode
        the node to load the value into.
    value : float
        the value.
    negative : bool
        whether the value is written as a negative number, for a node that stores its sign apart
        (e.g., a mass density).
    """
    value = float(value)
    written = -value if negative else value
    if node.is_negatable_float:
        node.is_negative = negative
    node._token = repr(written)
    node._value = value
    node._og_value = written
    node._is_reversed = False


def _clean_float(value: float) -> float:
    """Removes the floating point noise from a value that was calculated: 0.0012050000000000001 -> 0.001205."""
    return float(f"{value:.15g}")


def _forget_placeholder(node):
    """Forgets the placeholder (e.g., a jump: ``J``) that a new node was made with.

    Otherwise writing the real value is reported as a line expansion (``J`` -> ``10``).
    """
    node._token = None


def _wrap_geometry(cell: montepy.Cell):
    """Puts new lines in a new cell's geometry so no line is too long.

    A new geometry is otherwise all on one line. MontePy splits a line that is too long when it is
    written, but warns about every line that it splits.
    The lines are broken between the parentheses when possible.
    """
    indent = BLANK_SPACE_CONTINUE
    geometry = cell.geometry
    # make the syntax tree (and the parentheses) for the geometry
    geometry._update_values()
    operator_lengths = {Operator.INTERSECTION: 1, Operator.UNION: 3}
    lengths = {}

    def length(half_space) -> int:
        """The number of characters that this will be written with."""
        key = id(half_space)
        if key not in lengths:
            if isinstance(half_space, UnitHalfSpace):
                lengths[key] = len(half_space.node.format())
            elif half_space.operator == Operator.GROUP:
                lengths[key] = length(half_space.left) + 2
            else:
                lengths[key] = (
                    length(half_space.left)
                    + operator_lengths[half_space.operator]
                    + length(half_space.right)
                )
        return lengths[key]

    def unbroken_length(half_space) -> int:
        """The number of characters at the start of this that have to be kept on one line.

        A surface is never broken up, nor are parentheses that fit on one line.
        """
        if isinstance(half_space, UnitHalfSpace):
            return length(half_space)
        if half_space.operator == Operator.GROUP:
            if length(half_space) <= _GEOMETRY_WIDTH - indent:
                return length(half_space)
            return unbroken_length(half_space.left) + 1
        return unbroken_length(half_space.left)

    # where the geometry starts: after the cell number, and the material
    column = len(str(cell.number)) + 1
    if cell.material is None:
        column += len("0 ")
    else:
        column += len(str(cell.material.number)) + 1
        column += len(cell._density_node.format())

    def wrap(half_space):
        nonlocal column
        if isinstance(half_space, UnitHalfSpace):
            column += length(half_space)
        elif half_space.operator == Operator.GROUP:
            column += 1
            wrap(half_space.left)
            column += 1
        else:
            wrap(half_space.left)
            is_union = half_space.operator == Operator.UNION
            # leave room for the " :" of a union that could be next
            needed = unbroken_length(half_space.right) + 2
            operator_length = operator_lengths[half_space.operator]
            if column + operator_length + needed > _GEOMETRY_WIDTH:
                new_line = "\n" + " " * indent
                operator = PaddingNode(" :" + new_line if is_union else new_line)
                half_space.node.nodes["operator"] = operator
                column = indent
            else:
                column += operator_length
            wrap(half_space.right)

    if column + length(geometry) > _GEOMETRY_WIDTH:
        wrap(geometry)


def _break_before_parameters(cell: montepy.Cell):
    """Puts the parameters of a new cell (e.g., ``imp:n=1.0 U=5``) on a new line, if a line is too long.

    This is for a geometry that fits on its last line, but not with the parameters after it.
    Nothing is changed if no line of the cell is too long.
    """
    lines = cell.mcnp_str().split("\n")
    lines = [line for line in lines if not line.lower().startswith("c ")]
    if all(len(line.rstrip()) <= _GEOMETRY_WIDTH for line in lines):
        return
    new_line = "\n" + " " * BLANK_SPACE_CONTINUE
    # the last thing that is written for the geometry
    half_space = cell.geometry
    while not isinstance(half_space, UnitHalfSpace):
        if half_space.operator == Operator.GROUP:
            half_space.node.nodes["end_pad"] = PaddingNode(")" + new_line)
            return
        half_space = half_space.right
    half_space.node.padding = PaddingNode(new_line)


def _wrap_lattice_fill(cell: montepy.Cell):
    """Puts new lines in the universes of a new lattice's fill so no line is too long.

    The universes are otherwise all on one line, which is split (with a warning) when it is written,
    and can still be left longer than what MCNP 6.2 accepts.
    Each row of the lattice (the elements along x) is put on its own line, after the line with the indices.
    These are in the order of MCNP: the first row is the one with the lowest y (and z).
    Nothing is changed if the cell already fits on its lines.
    """
    fill = cell.fill
    if not fill.multiple_universes:
        return
    # makes the nodes for the indices, and the universes
    lines = cell.mcnp_str().split("\n")
    if max(len(line) for line in lines) <= _GEOMETRY_WIDTH:
        return
    new_line = "\n" + " " * BLANK_SPACE_CONTINUE
    data = fill._tree["data"]
    data["indices"].nodes[-1].padding = PaddingNode(new_line)
    nodes = [node for node in data["universes"] if hasattr(node, "value")]
    row_length = fill.universes.shape[0]
    column = BLANK_SPACE_CONTINUE
    for i, node in enumerate(nodes[:-1]):
        column += len(str(node.value)) + 1
        is_row_end = (i + 1) % row_length == 0
        next_length = len(str(nodes[i + 1].value)) + 1
        if is_row_end or column + next_length > _GEOMETRY_WIDTH:
            node.padding = PaddingNode(new_line)
            column = BLANK_SPACE_CONTINUE
        else:
            node.padding = PaddingNode(" ")


def _parse_region(text: str):
    """Parses an OpenMC region into a tree.

    A node of the tree is one of:

    * ``("surf", number, is_positive)``
    * ``("and", [nodes])``
    * ``("or", [nodes])``

    Complements are expanded with De Morgan's laws.
    """
    tokens = _REGION_TOKEN.findall(text)
    if _REGION_TOKEN.sub("", text).strip():
        raise ValueError(f"The region could not be parsed: {text!r}")
    position = 0

    def peek():
        return tokens[position] if position < len(tokens) else None

    def union():
        nonlocal position
        terms = [intersection()]
        while peek() == "|":
            position += 1
            terms.append(intersection())
        return terms[0] if len(terms) == 1 else ("or", terms)

    def intersection():
        factors = [factor()]
        while peek() not in {None, "|", ")"}:
            factors.append(factor())
        return factors[0] if len(factors) == 1 else ("and", factors)

    def factor():
        nonlocal position
        token = peek()
        if token is None or token in {"|", ")"}:
            raise ValueError(f"The region could not be parsed: {text!r}")
        position += 1
        if token == "~":
            return _complement(factor())
        if token == "(":
            ret = union()
            if peek() != ")":
                raise ValueError(f"The region has unbalanced parentheses: {text!r}")
            position += 1
            return ret
        number = int(token)
        if number == 0:
            raise ValueError(f"The region uses a surface with an ID of 0: {text!r}")
        return ("surf", abs(number), number > 0)

    ret = union()
    if position != len(tokens):
        raise ValueError(f"The region has unbalanced parentheses: {text!r}")
    return ret


def _complement(node):
    """Gets the complement of a region tree, with De Morgan's laws."""
    kind = node[0]
    if kind == "surf":
        return ("surf", node[1], not node[2])
    new_kind = "or" if kind == "and" else "and"
    return (new_kind, [_complement(child) for child in node[1]])


def _rotation_matrix(rotation: list[float]) -> np.ndarray:
    """Gets the rotation matrix for the ``rotation`` of an OpenMC cell.

    This is the same matrix that OpenMC uses: :math:`\\vec{r}' = R (\\vec{r} - \\vec{t})`,
    where :math:`\\vec{r}'` is in the filling universe. Its rows are then the axes of
    the filling universe, which is what MCNP uses for a transform.
    """
    if len(rotation) == 9:
        matrix = np.array(rotation, dtype=float).reshape((3, 3))
    elif len(rotation) == 3:
        phi, theta, psi = (-math.radians(angle) for angle in rotation)
        c3, s3 = math.cos(phi), math.sin(phi)
        c2, s2 = math.cos(theta), math.sin(theta)
        c1, s1 = math.cos(psi), math.sin(psi)
        matrix = np.array(
            [
                [c1 * c2, c1 * s2 * s3 - c3 * s1, s1 * s3 + c1 * c3 * s2],
                [c2 * s1, c1 * c3 + s1 * s2 * s3, c3 * s1 * s2 - c1 * s3],
                [-s2, c2 * s3, c2 * c3],
            ]
        )
    else:
        raise ValueError(
            f"A cell rotation must have 3 or 9 values. {len(rotation)} given."
        )
    # remove the noise from the trigonometry (e.g., cos(90) = 6e-17)
    matrix[np.abs(matrix) < 1e-15] = 0.0
    return matrix


class _ModelConverter:
    """Converts the materials and the geometry of an OpenMC model into an MCNP problem.

    Parameters
    ----------
    problem : MCNP_Problem
        the (empty) problem to add the objects to.
    materials : xml.etree.ElementTree.Element
        the ``<materials>`` element. May be None.
    geometry : xml.etree.ElementTree.Element
        the ``<geometry>`` element.
    library : Library
        the library for all of the nuclides. May be None.
    sab_register : dict[str, str]
        the MCNP thermal scattering table for each OpenMC table.
    """

    # OpenMC type: (MCNP type, MCNP type if on the axis/origin, indices of coefficients that must be 0 for that)
    _SURFACE_TYPES = {
        "x-plane": ("PX", None, ()),
        "y-plane": ("PY", None, ()),
        "z-plane": ("PZ", None, ()),
        "plane": ("P", None, ()),
        "x-cylinder": ("C/X", "CX", (0, 1)),
        "y-cylinder": ("C/Y", "CY", (0, 1)),
        "z-cylinder": ("C/Z", "CZ", (0, 1)),
        "sphere": ("S", "SO", (0, 1, 2)),
        "x-cone": ("K/X", "KX", (1, 2)),
        "y-cone": ("K/Y", "KY", (0, 2)),
        "z-cone": ("K/Z", "KZ", (0, 1)),
        "quadric": ("GQ", None, ()),
        "x-torus": ("TX", None, ()),
        "y-torus": ("TY", None, ()),
        "z-torus": ("TZ", None, ()),
    }

    def __init__(self, problem, materials, geometry, library, sab_register):
        self._problem = problem
        self._library = library
        self._sab_register = sab_register
        self._materials_elem = materials
        self._geometry = geometry
        self._cell_elems = geometry.findall("cell")
        self._lattice_elems = geometry.findall("lattice")
        # material ID: (density, is_atom_density)
        self._densities = {}
        # OpenMC universe (or lattice) ID: Universe
        self._universes = {}
        self._root_id = None
        self._all_space_surface = None
        self._check_supported()
        get_ids = lambda tag: [_get_id(elem) for elem in geometry.findall(tag)]
        universe_ids = {int(_get(e, "universe", "0")) for e in self._cell_elems}
        self._universe_ids = universe_ids
        self._lattice_ids = set(get_ids("lattice"))
        self._next_cell = max(get_ids("cell"), default=0) + 1
        self._next_surface = max(get_ids("surface"), default=0) + 1
        self._next_universe = max(universe_ids | self._lattice_ids, default=0) + 1

    def _check_supported(self):
        unsupported = {
            "hex_lattice": "Hexagonal lattices",
            "dagmc_universe": "DAGMC universes",
        }
        for tag, name in unsupported.items():
            if self._geometry.find(tag) is not None:
                raise UnsupportedFeature(
                    f"{name} (<{tag}>) can not be converted from OpenMC."
                )

    def convert(self, graveyard: bool = True):
        """Converts the model, and adds all of the objects to the problem.

        Parameters
        ----------
        graveyard : bool
            whether to add the graveyard cell.
        """
        self._convert_materials()
        self._convert_surfaces()
        self._make_universes()
        for elem in self._cell_elems:
            self._convert_cell(elem)
        for elem in self._lattice_elems:
            self._convert_lattice(elem)
        if graveyard:
            self._add_graveyard()

    # ------------------------------------------------------------------
    # Number generators
    # ------------------------------------------------------------------

    @staticmethod
    def _make_cell(number: int, comment: str) -> montepy.Cell:
        """Makes a cell with a neutron importance of 1.

        The importance is set explicitly, as an importance that is only the default is not written,
        and MCNP needs an importance for every cell.
        """
        cell = montepy.Cell(number=number)
        _set_comment(cell, comment)
        cell.importance.neutron = 1.0
        return cell

    def _new_cell(self, comment: str) -> montepy.Cell:
        cell = self._make_cell(self._next_cell, comment)
        self._next_cell += 1
        return cell

    def _new_surface(
        self, surface_type: str, constants: list[float], comment: str = None
    ) -> montepy.Surface:
        surface = self._make_surface(self._next_surface, surface_type, constants)
        self._next_surface += 1
        _set_comment(surface, comment)
        self._problem.surfaces.append(surface)
        return surface

    def _new_universe(self) -> montepy.Universe:
        universe = montepy.Universe(self._next_universe)
        self._next_universe += 1
        self._problem.universes.append(universe)
        return universe

    # ------------------------------------------------------------------
    # Materials
    # ------------------------------------------------------------------

    def _convert_materials(self):
        if self._materials_elem is None:
            return
        for elem in self._materials_elem.findall("material"):
            self._convert_material(elem)
        # Put every MT input right after its material. They are not left there as they are added,
        # because the next material is inserted in the data inputs before the last MT input.
        materials = self._problem.materials
        data_inputs = self._problem.data_inputs
        laws = {id(mat.thermal_scattering) for mat in materials} - {id(None)}
        ordered = []
        for data_input in data_inputs:
            if id(data_input) in laws:
                continue
            ordered.append(data_input)
            if (
                isinstance(data_input, montepy.Material)
                and data_input.thermal_scattering
            ):
                ordered.append(data_input.thermal_scattering)
        data_inputs[:] = ordered
        # so that a material that is added later goes after all of these
        materials._last_index = len(data_inputs) - 1

    def _convert_material(self, elem: ET.Element):
        mat_id = _get_id(elem)
        name = _get(elem, "name")
        label = f"Material {mat_id}" + (f" ({name})" if name else "")
        if elem.find("macroscopic") is not None:
            raise UnsupportedFeature(
                f"{label} is a multi-group (macroscopic) material, which can not be converted."
            )
        material = montepy.Material(number=mat_id)
        _set_comment(material, name)
        components = []
        fraction_types = set()
        for child in elem:
            if child.tag not in {"nuclide", "element"}:
                continue
            for fraction_type in ("ao", "wo"):
                if child.get(fraction_type) is not None:
                    fraction = float(child.get(fraction_type))
                    break
            else:
                raise ValueError(
                    f'{label}: {child.get("name")} has no atom fraction (ao) or mass fraction (wo).'
                )
            fraction_types.add(fraction_type)
            components.append((self._make_nuclide(child, label), fraction))
        if not components:
            raise ValueError(f"{label} has no nuclides.")
        if len(fraction_types) > 1:
            raise ValueError(
                f"{label} mixes atom fractions (ao) and mass fractions (wo), which MCNP does not allow."
            )
        material.is_atom_fraction = fraction_types == {"ao"}
        for nuclide, fraction in components:
            material.add_nuclide(nuclide, fraction)
            _load_float(
                material._components[-1][1],
                fraction,
                negative=not material.is_atom_fraction,
            )
        self._densities[mat_id] = self._get_density(elem, label, components, material)
        self._problem.materials.append(material)
        self._convert_thermal_scattering(elem, material, label)

    def _convert_thermal_scattering(self, elem, material, label):
        """Adds the ``MT`` input for the ``<sab>`` tables of the material."""
        for sab in elem.findall("sab"):
            name = sab.get("name")
            if name not in self._sab_register:
                warnings.warn(
                    f"{label}: the thermal scattering table {name!r} was not converted, "
                    "as it is not in the register. Add it to sab_register, "
                    "or use Material.add_thermal_scattering.",
                    stacklevel=7,
                )
                continue
            if float(sab.get("fraction", "1.0")) != 1.0:
                warnings.warn(
                    f"{label}: the fraction of the thermal scattering table {name!r} "
                    "was ignored, as MCNP has no input for it.",
                    stacklevel=7,
                )
            if material.thermal_scattering is None:
                material.add_thermal_scattering(self._sab_register[name])
                law = material.thermal_scattering
                law.link_to_problem(self._problem)
                # moved to be right after its material by _convert_materials
                self._problem.data_inputs.append(law)
            else:
                material.thermal_scattering.add_scattering_law(self._sab_register[name])

    def _make_nuclide(self, elem: ET.Element, label: str) -> montepy.Nuclide:
        name = elem.get("name", "")
        if elem.tag == "element":
            # a natural element
            symbol, A, meta = name, 0, 0
        else:
            match = _NUCLIDE_NAME.fullmatch(name)
            if match is None:
                raise ValueError(f"{label}: {name!r} is not a valid nuclide name.")
            symbol = match["symbol"]
            A = int(match["A"])
            meta = int(match["meta"]) if match["meta"] else 0
        element = montepy.Element.get_by_symbol(symbol.capitalize())
        library = str(self._library) if self._library is not None else ""
        return montepy.Nuclide(element=element, A=A, meta_state=meta, library=library)

    @staticmethod
    def _get_density(elem, label, components, material) -> tuple[float, bool]:
        """Gets the density of the material for MCNP.

        Returns
        -------
        tuple[float, bool]
            the density, and whether it is an atom density [atom/b-cm] (True), or a mass density [g/cm3] (False).
        """
        density = elem.find("density")
        if density is None:
            raise ValueError(f"{label} has no density.")
        units = density.get("units", "")
        if units == "sum":
            if not material.is_atom_fraction:
                raise ValueError(
                    f'{label}: the density units "sum" need atom fractions (ao).'
                )
            return (math.fsum(fraction for _, fraction in components), True)
        if units == "macro":
            raise UnsupportedFeature(
                f"{label} is a multi-group (macroscopic) material, which can not be converted."
            )
        if density.get("value") is None:
            raise ValueError(f"{label} has no density value.")
        value = float(density.get("value"))
        if units in {"g/cm3", "g/cc"}:
            return (value, False)
        if units == "kg/m3":
            return (_clean_float(value / 1000.0), False)
        if units == "atom/b-cm":
            return (value, True)
        if units == "atom/cm3":
            return (_clean_float(value / 1.0e24), True)
        raise ValueError(f"{label} has unknown density units: {units!r}.")

    # ------------------------------------------------------------------
    # Surfaces
    # ------------------------------------------------------------------

    @staticmethod
    def _make_surface(
        number: int, surface_type: str, constants: list[float]
    ) -> montepy.Surface:
        surface_type = montepy.SurfaceType(surface_type)
        builder = montepy.surfaces.surface_builder
        cls = builder._SPECIFIC_DISPATCH.get(
            surface_type
        ) or builder._GENERIC_DISPATCH.get(surface_type)
        surface = cls(number=number)
        nodes = surface._surface_constants
        if len(nodes) != len(constants):
            raise ValueError(
                f"Surface {number} of type {surface_type} needs {len(nodes)} coefficients. "
                f"{len(constants)} given."
            )
        for node, constant in zip(nodes, constants):
            _load_float(node, constant)
        return surface

    def _convert_surfaces(self):
        periodic = []
        for elem in self._geometry.findall("surface"):
            number = _get_id(elem)
            openmc_type = _get(elem, "type")
            if openmc_type not in self._SURFACE_TYPES:
                raise UnsupportedFeature(
                    f"Surface {number} is of type {openmc_type!r}, which can not be converted."
                )
            coeffs = _floats(_get(elem, "coeffs", ""))
            mcnp_type, simple_type, zero_indices = self._SURFACE_TYPES[openmc_type]
            if simple_type and len(coeffs) > max(zero_indices):
                # e.g., use CZ and not C/Z for a cylinder on the Z axis.
                if all(coeffs[i] == 0.0 for i in zero_indices):
                    mcnp_type = simple_type
                    coeffs = [c for i, c in enumerate(coeffs) if i not in zero_indices]
            surface = self._make_surface(number, mcnp_type, coeffs)
            _set_comment(surface, _get(elem, "name"))
            boundary = _get(elem, "boundary", "transmission")
            if boundary == "reflective":
                surface.is_reflecting = True
            elif boundary == "white":
                surface.is_white_boundary = True
            elif boundary == "periodic":
                periodic.append((surface, _get(elem, "periodic_surface_id")))
            elif boundary not in {"transmission", "vacuum"}:
                raise ValueError(
                    f"Surface {number} has an unknown boundary type: {boundary!r}."
                )
            self._problem.surfaces.append(surface)
        self._link_periodic_surfaces(periodic)

    def _link_periodic_surfaces(self, periodic):
        for surface, partner_id in periodic:
            if partner_id is not None:
                try:
                    partner = self._problem.surfaces[int(partner_id)]
                except KeyError:
                    raise ValueError(
                        f"Surface {surface.number} is periodic with surface {partner_id}, which does not exist."
                    )
            else:
                # OpenMC pairs these on its own, when there is no ambiguity.
                others = [
                    other
                    for other, _ in periodic
                    if other is not surface
                    and other.surface_type == surface.surface_type
                ]
                if len(others) != 1:
                    warnings.warn(
                        f"The periodic surface for surface {surface.number} could not be found. "
                        "Set Surface.periodic_surface.",
                        stacklevel=6,
                    )
                    continue
                partner = others[0]
            surface.periodic_surface = partner

    def _get_all_space_surface(self) -> montepy.Surface:
        """The plane that is used for the cells that have no region in OpenMC."""
        if self._all_space_surface is None:
            self._all_space_surface = self._new_surface(
                "PZ",
                [0.0],
                "both sides of this are used for the cells with no region in OpenMC",
            )
        return self._all_space_surface

    # ------------------------------------------------------------------
    # Universes
    # ------------------------------------------------------------------

    def _make_universes(self):
        """Makes all of the universes, and finds which is the root universe."""
        filled = set()
        for elem in self._cell_elems:
            fill = _get(elem, "fill")
            if fill is not None:
                filled.add(int(fill))
        for elem in self._lattice_elems:
            filled.update(int(u) for u in _get(elem, "universes", "").split())
            outer = _get(elem, "outer")
            if outer is not None:
                filled.add(int(outer))
        unknown = filled - self._universe_ids - self._lattice_ids
        if unknown:
            raise ValueError(
                f"These universes are used as a fill, but have no cells: {sorted(unknown)}"
            )
        roots = self._universe_ids - filled
        if len(roots) != 1:
            raise ValueError(
                "There must be exactly one root universe: a universe that does not fill another cell. "
                f"These were found: {sorted(roots)}"
            )
        self._root_id = roots.pop()
        for universe_id in sorted(self._universe_ids | self._lattice_ids):
            if universe_id == self._root_id:
                # MCNP's root universe is always 0.
                universe = montepy.Universe(0)
                self._problem.universes.append(universe)
            elif universe_id == 0:
                # 0 is taken by the root universe.
                universe = self._new_universe()
                warnings.warn(
                    f"Universe 0 is not the root universe, and was renumbered to {universe.number}.",
                    stacklevel=5,
                )
            else:
                universe = montepy.Universe(universe_id)
                self._problem.universes.append(universe)
            self._universes[universe_id] = universe

    # ------------------------------------------------------------------
    # Cells
    # ------------------------------------------------------------------

    def _to_half_space(self, node) -> montepy.surfaces.half_space.HalfSpace:
        """Converts a region tree to a MontePy geometry."""
        kind = node[0]
        if kind == "surf":
            _, number, is_positive = node
            try:
                surface = self._problem.surfaces[number]
            except KeyError:
                raise ValueError(
                    f"Surface {number} is used in a region, but does not exist."
                )
            return +surface if is_positive else -surface
        children = [self._to_half_space(child) for child in node[1]]
        # Combine as a balanced tree. This is the same geometry as a chain (the operators are associative),
        # but a chain of 100s of surfaces would be a very deep tree, which is slow and can hit the recursion limit.
        while len(children) > 1:
            pairs = []
            for i in range(0, len(children) - 1, 2):
                left, right = children[i : i + 2]
                pairs.append(left & right if kind == "and" else left | right)
            if len(children) % 2:
                pairs.append(children[-1])
            children = pairs
        return children[0]

    def _all_space(self) -> montepy.surfaces.half_space.HalfSpace:
        """A geometry that is all of space.

        An MCNP cell must have a geometry, so this is both sides of a plane.
        """
        plane = self._get_all_space_surface()
        return +plane | -plane

    def _convert_cell(self, elem: ET.Element):
        number = _get_id(elem)
        cell = self._make_cell(number, _get(elem, "name"))
        region = _get(elem, "region")
        if region:
            cell.geometry = self._to_half_space(_parse_region(region))
        else:
            cell.geometry = self._all_space()
        universe_id = int(_get(elem, "universe", "0"))
        if universe_id != self._root_id:
            self._set_universe(cell, self._universes[universe_id])
        material = _get(elem, "material")
        fill = _get(elem, "fill")
        if fill is not None:
            cell.fill.universe = self._universes[int(fill)]
            self._set_fill_transform(cell, elem)
        elif material is None:
            raise ValueError(f"Cell {number} has no material and no fill.")
        elif len(material.split()) > 1:
            raise UnsupportedFeature(
                f"Cell {number} has distributed materials, which can not be converted."
            )
        elif material != "void":
            self._set_material(cell, int(material), _get(elem, "density"))
        self._add_cell(cell)

    def _add_cell(self, cell: montepy.Cell):
        """Adds the finished cell to the problem."""
        _wrap_geometry(cell)
        self._problem.cells.append(cell)
        _break_before_parameters(cell)

    def _set_universe(self, cell: montepy.Cell, universe: montepy.Universe):
        cell.universe = universe
        _forget_placeholder(cell._universe._tree["data"][0])

    def _set_material(self, cell: montepy.Cell, mat_id: int, cell_density: str):
        try:
            cell.material = self._problem.materials[mat_id]
        except KeyError:
            raise ValueError(
                f"Cell {cell.number} uses material {mat_id}, which does not exist."
            )
        _forget_placeholder(cell._tree["material"]["mat_number"])
        density, is_atom_density = self._densities[mat_id]
        if cell_density is not None:
            # The density [g/cm3] of this cell replaces the density of the material.
            density, is_atom_density = float(cell_density.split()[0]), False
        if is_atom_density:
            cell.atom_density = density
        else:
            cell.mass_density = density
        _load_float(cell._density_node, density, negative=not is_atom_density)

    @staticmethod
    def _make_transform(
        translation: list[float], rotation: np.ndarray = None
    ) -> montepy.Transform:
        """Makes a transform that has no number, to be used in a fill."""
        transform = montepy.Transform(pass_through=True)
        transform.displacement_vector = np.array(translation, dtype=float)
        for node, value in zip(transform._tree["data"], translation):
            _load_float(node, value)
        if rotation is not None:
            transform.rotation_matrix = np.array(
                [float(value) for value in rotation.flatten()]
            )
        return transform

    def _set_fill_transform(self, cell: montepy.Cell, elem: ET.Element):
        translation = _get(elem, "translation")
        rotation = _get(elem, "rotation")
        if translation is None and rotation is None:
            return
        translation = _floats(translation) if translation else [0.0] * 3
        if len(translation) != 3:
            raise ValueError(
                f"Cell {cell.number} must have 3 values for its translation."
            )
        if rotation is not None:
            rotation = _rotation_matrix(_floats(rotation))
        cell.fill.transform = self._make_transform(translation, rotation)

    # ------------------------------------------------------------------
    # Lattices
    # ------------------------------------------------------------------

    def _convert_lattice(self, elem: ET.Element):
        """Converts a rectangular lattice.

        For an OpenMC lattice with the ID ``n`` these are made:

        #. A ``LAT=1`` cell, in a new universe. Its [0, 0, 0] element is centered on the origin,
           because that is where MCNP puts the origin of the universes that fill a lattice.
        #. A cell in universe ``n``, which is filled with that new universe. It is translated
           so that the elements are where they are in OpenMC. So all the cells that are
           filled with the lattice ``n`` in OpenMC are filled with the universe ``n`` in MCNP.
        #. If the lattice has an ``outer`` universe: the cell above is limited to the extent of the lattice,
           and a second cell in universe ``n`` is all of the space around it.
           That is filled with a second lattice where every element is the outer universe,
           as OpenMC repeats the outer universe with the pitch of the lattice.
        """
        lat_id = _get_id(elem)
        label = f"lattice {lat_id}"
        name = _get(elem, "name")
        if name:
            label += f" ({name})"
        shape = [int(n) for n in _get(elem, "dimension", "").split()]
        pitch = _floats(_get(elem, "pitch", ""))
        lower_left = _floats(_get(elem, "lower_left", ""))
        n_dim = len(shape)
        if n_dim not in {2, 3} or len(pitch) != n_dim or len(lower_left) != n_dim:
            raise ValueError(
                f"The dimension, pitch, and lower_left of {label} must all have 2 or 3 values."
            )
        if any(n < 1 for n in shape) or any(p <= 0.0 for p in pitch):
            raise ValueError(
                f"The dimension and pitch of {label} must all be positive."
            )
        ids = [int(u) for u in _get(elem, "universes", "").split()]
        if len(ids) != math.prod(shape):
            raise ValueError(
                f"{label} needs {math.prod(shape)} universes. {len(ids)} given."
            )
        # OpenMC lists x the fastest, then y from the top (max y) down, then z from the bottom up.
        # MCNP lists x (i) the fastest, then y (j) from the bottom up, then z (k) from the bottom up.
        full_shape = shape + [1] * (3 - n_dim)
        nx, ny, nz = full_shape
        ids = np.array(ids).reshape((nz, ny, nx))
        universes = np.empty((nx, ny, nz), dtype=object)
        for (k, j, i), universe_id in np.ndenumerate(ids):
            universes[i, ny - 1 - j, k] = self._universes[int(universe_id)]

        # the lattice cell: element [0, 0, 0] is centered on the origin
        halves = []
        for axis, width in zip(_AXES, pitch):
            mnemonic = f"P{axis.upper()}"
            comment = f"{label}: {axis} side of an element"
            half_width = _clean_float(width / 2.0)
            # the order of the surfaces sets the directions of the lattice indices in MCNP
            halves.append(-self._new_surface(mnemonic, [half_width], comment))
            halves.append(+self._new_surface(mnemonic, [-half_width], comment))

        def make_lattice_cell(comment: str) -> montepy.Cell:
            cell = self._new_cell(comment)
            geometry = halves[0]
            for half in halves[1:]:
                geometry = geometry & half
            cell.geometry = geometry
            cell.lattice_type = montepy.LatticeType.RECTANGULAR
            self._set_universe(cell, self._new_universe())
            self._add_cell(cell)
            return cell

        lattice = make_lattice_cell(f"{label}: the lattice")
        lattice.fill.universes = universes
        _wrap_lattice_fill(lattice)

        # the cell(s) that the lattice is seen through
        # the center of element [0, 0, 0] in OpenMC
        translation = [
            _clean_float(lower_left[i] + pitch[i] / 2.0) for i in range(n_dim)
        ]
        translation += [0.0] * (3 - n_dim)

        def make_window(comment: str, geometry, lattice_cell: montepy.Cell):
            cell = self._new_cell(comment)
            cell.geometry = geometry
            self._set_universe(cell, self._universes[lat_id])
            cell.fill.universe = lattice_cell.universe
            if any(translation):
                cell.fill.transform = self._make_transform(translation)
            self._add_cell(cell)

        outer = _get(elem, "outer")
        if outer is None:
            make_window(f"{label}: positions the lattice", self._all_space(), lattice)
            return
        # OpenMC repeats the outer universe in every element that is outside of the lattice.
        # So this is another lattice, where all of the elements are the outer universe.
        outer_lattice = make_lattice_cell(f"{label}: the outer universe, repeated")
        outer_lattice.fill.universe = self._universes[int(outer)]
        box = []
        for i, axis in enumerate(_AXES[:n_dim]):
            mnemonic = f"P{axis.upper()}"
            comment = f"{label}: {axis} boundary"
            upper = _clean_float(lower_left[i] + shape[i] * pitch[i])
            lower = self._new_surface(mnemonic, [lower_left[i]], comment)
            upper = self._new_surface(mnemonic, [upper], comment)
            box += [("surf", lower.number, True), ("surf", upper.number, False)]
        box = ("and", box)
        make_window(
            f"{label}: positions the lattice", self._to_half_space(box), lattice
        )
        make_window(
            f"{label}: outside of the lattice",
            self._to_half_space(_complement(box)),
            outer_lattice,
        )

    # ------------------------------------------------------------------
    # Outside world
    # ------------------------------------------------------------------

    def _add_graveyard(self):
        """Adds the cell that is everything outside of the root universe's cells, where particles are killed."""
        regions = []
        for elem in self._cell_elems:
            if int(_get(elem, "universe", "0")) != self._root_id:
                continue
            region = _get(elem, "region")
            if not region:
                # This cell is all of space: there is no outside.
                return
            regions.append(_parse_region(region))
        cell = self._new_cell("graveyard: added for MCNP")
        cell.geometry = self._to_half_space(_complement(("or", regions)))
        cell.importance.neutron = 0.0
        self._add_cell(cell)
