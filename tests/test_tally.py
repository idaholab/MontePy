# Copyright 2024-2025, Battelle Energy Alliance, LLC All Rights Reserved.
import io

import pytest

import montepy
from montepy.data_inputs.data_parser import parse_data
from montepy.data_inputs.tally import (
    EnergyDepositionTally,
    F1Tally,
    F4Tally,
    F6Tally,
    FlatGroup,
    LatticeIndex,
    ParticleFilter,
    PathGroup,
    SpatialFilter,
    TallyGroup,
)
from montepy.data_inputs.tally_type import Score, TallyType
from montepy.input_parser.block_type import BlockType
from montepy.input_parser.mcnp_input import Input
from montepy.input_parser.tally_parser import TallyParser
from montepy.input_parser.tokens import TallyLexer


class TestTallyParser:
    @pytest.mark.parametrize(
        "line",
        [
            "F4:n (1 3i 5) T",
            "F4:n (1 2 3 4 5) T",
            "F4:n 1 2 3",
            "F4:n (1 3i 5) (7 8 9) T",
            "f4:n (1 3i 5) (7 8 9)",
            "F7 (1 3i 5) (7 8 9)",
            "F7 (1 3i 5) (7 8 9) ",
        ],
    )
    def test_parsing_tally_groups(_, line):
        data = parse_data(line)
        assert data.prefix == "f"

    def test_parsing_tally_print(_):
        input = Input(["Fq4 f p e"], BlockType.DATA)
        data = parse_data(input)
        assert data.prefix == "fq"

    @pytest.mark.parametrize(
        "test",
        [
            "fm904   (1.0) (1.0 961 103)",
            "fm3064 (1.0 361001 444) $ 1.0=mult",
        ],
    )
    def test_parsing_tally_multiplier(_, test):
        test_lines = {
            "fm904   (1.0) (1.0 961 103)",
            "fm3064 (1.0 361001 444) $ 1.0=mult",
        }
        for test in test_lines:
            print(test)
            input = Input([test], BlockType.DATA)
            data = parse_data(input)

    @pytest.mark.parametrize(
        "line",
        [
            "fs14 -123",
            "fs12 -456 t",
            "fs11 -1 -2",
            "fs16 +1 +2 c",
            "fs17 -1 -2 t c",
        ],
    )
    def test_tally_segment_init(_, line):
        input = Input([line], BlockType.DATA)
        data = parse_data(input)

    @pytest.mark.parametrize("line", ["de4 log 1 2 3 4"])
    def test_de_parsing_jail(_, line):
        data = parse_data(line)
        assert data.mcnp_str() == line
        with pytest.raises(montepy.exceptions.UnsupportedFeature):
            data.data


class TestTallyPathSyntax:
    """Tests for complex MCNP tally path syntax (universe paths, lattice elements)."""

    _parser = TallyParser()
    _lexer = TallyLexer()

    @pytest.mark.parametrize(
        "line",
        [
            "f64:n (1<1)",
            "f74:n (1<1< 2)",
            "f84:n (1[0 0 0]<2)",
            "f94:n (1[0 0 0]<2<3)",
            "F154:n,p  (1 < (2[0 0 0] 2[0 1 0]) < 5)",
            "F1464:n  (1 < 2[0:1 0:1 0:0] < 5)",
            "F174:n  (1 < (2[0:1 0:1 0:0]) < 5)",
            "F184:n  (1 < 2[0 0 0, 0 1 0] < 5)",
            "F184:n  (1 < 2[0 0 0,0 1 0] < 5)",  # comma with no trailing padding
            "F194:n  (1 < 2 < 5)",
            "F104:n  ((u=1) < 2[0 0 0] < 5)",
            "F114:n  (u=1 < 2[0 0 0] < 5)",
        ],
    )
    def test_tally_path_parsing(self, line):
        result = self._parser.parse(self._lexer.tokenize(line))
        assert result is not None, f"TallyParser failed to parse: {line}"


class TestFmesh:
    # this is hacky; just makes sure it doesn't crash
    @pytest.mark.parametrize("line", ["fmesh14:n vec=0 0 0", "fmesh14:n vec=0, 0, 0"])
    def test_fmesh_parse(_, line):
        parse_data(line)


@pytest.fixture
def tally_problem():
    return montepy.read_input("tests/inputs/test_tally.imcnp")


class TestTallyObject:
    """Tests for the Tally object model: clone, clone_as, scores, filters."""

    def test_clone_same_type(self, tally_problem):
        f4 = tally_problem.tallies[4]
        clone = f4.clone()
        assert clone.number != f4.number
        assert clone.number % 10 == 4
        assert clone in tally_problem.tallies
        assert list(clone.cells.numbers) == list(f4.cells.numbers)

    def test_clone_as_class(self, tally_problem):
        f4 = tally_problem.tallies[4]
        new = f4.clone_as(F6Tally)
        assert isinstance(new, EnergyDepositionTally)
        assert new.number % 10 == 6
        assert new in tally_problem.tallies
        assert list(new.cells.numbers) == list(f4.cells.numbers)
        assert new.scores == [Score.ENERGY_DEPOSITION]

    def test_clone_as_enum(self, tally_problem):
        f4 = tally_problem.tallies[4]
        new = f4.clone_as(TallyType.ENERGY_DEPOSITION)
        assert isinstance(new, EnergyDepositionTally)
        assert new.number % 10 == 6
        assert new in tally_problem.tallies

    def test_clone_as_incompatible_category(self, tally_problem):
        f1 = tally_problem.tallies[1]
        with pytest.raises(ValueError):
            f1.clone_as(F4Tally)

    def test_clone_as_bad_type(self, tally_problem):
        f4 = tally_problem.tallies[4]
        with pytest.raises(TypeError):
            f4.clone_as("f6")

    @pytest.mark.parametrize(
        "number, expected",
        [
            (1, [Score.CURRENT]),
            (2, [Score.FLUX]),
            # not 4: it has a linked fm4 card, tested in test_tally_multiplier.py
            (34, [Score.FLUX]),
            (6, [Score.ENERGY_DEPOSITION]),
            (7, [Score.FISSION_ENERGY_DEPOSITION]),
            (8, [Score.PULSE_HEIGHT]),
        ],
    )
    def test_scores_default(self, tally_problem, number, expected):
        assert tally_problem.tallies[number].scores == expected

    def test_filters_default(self, tally_problem):
        f1 = tally_problem.tallies[1]  # f1:n,p 1000
        filters = f1.filters
        assert len(filters) == 2
        particle_filter, spatial_filter = filters
        assert isinstance(particle_filter, ParticleFilter)
        assert isinstance(spatial_filter, SpatialFilter)
        assert set(particle_filter.particles) == set(f1.particle_classifiers)
        assert spatial_filter.groups == f1.groups

    def test_add_cell_before_full_parse_preserves_existing_groups(self, tally_problem):
        # Regression test: add_cell/add_group/add_path_group must trigger a
        # full parse *before* mutating _groups, or the mutation is silently
        # lost the next time a @needs_full_ast getter forces a full parse.
        f4 = tally_problem.tallies[4]  # f4:n 1 2 3
        assert not f4.fully_parsed
        new_cell = tally_problem.cells[1].clone()
        f4.add_cell(new_cell)
        assert f4.fully_parsed
        numbers = list(f4.cells.numbers)
        assert {1, 2, 3}.issubset(set(numbers))
        assert new_cell.number in numbers

    def test_from_input_invalid_tally_type_digit(self):
        with pytest.raises(montepy.exceptions.MalformedInputError):
            parse_data(Input(["f3:n 1 2 3"], BlockType.DATA))

    def test_direct_tally_construction_invalid_digit(self):
        # Tally() bypasses from_input's dispatch-time digit check, so
        # _parse_tally_body must catch it too, once fully parsed.
        from montepy.data_inputs.tally import Tally

        t = Tally(Input(["f3:n 1 2 3"], BlockType.DATA), jit_parse=True)
        with pytest.raises(montepy.exceptions.MalformedInputError):
            t.groups

    def test_jump_in_tally_numbers_is_skipped(self):
        t = F4Tally(Input(["f4:n 1 J 3"], BlockType.DATA))
        assert [g.old_numbers[0] for g in t.groups] == [1, 3]

    def test_universe_spec_nested_in_bare_group(self):
        # A universe designator wrapped in its own parens, inside a group
        # with no `<` path separator at all: _extract_universe_spec_from_nodes
        # must recurse into the nested "tally group" node to find it.
        t = F4Tally(Input(["f4:n (5 (u=2) 7)"], BlockType.DATA))
        assert t.groups[0].universe_spec == 2

    def test_from_input_bare_prefix_no_number(self):
        # A tally card with no number at all: the light JIT parser succeeds
        # (it doesn't validate structure), so from_input's own "has no
        # number" check and except-Exception fallback both have to run,
        # and the fallback's real full construction is what actually
        # surfaces the parsing error.
        with pytest.raises(montepy.exceptions.ParsingError):
            parse_data(Input(["f"], BlockType.DATA))

    def test_clone_as_non_tally_type_raises_type_error(self, tally_problem):
        f34 = tally_problem.tallies[34]
        with pytest.raises(TypeError):
            f34.clone_as(str)

    def test_clone_as_custom_subclass_outside_category_raises(self, tally_problem):
        from montepy.data_inputs.tally import Tally

        class CustomTally(Tally):
            _TALLY_TYPE = TallyType.CELL_FLUX

        f34 = tally_problem.tallies[34]
        with pytest.raises(ValueError):
            f34.clone_as(CustomTally)

    def test_str_and_repr_on_uninitialized_tally(self):
        # __new__ bypasses __init__ entirely, leaving no _number/_groups --
        # exactly the partially-constructed state __str__/__repr__'s except
        # branches exist to report gracefully.
        from montepy.data_inputs.tally import Tally

        t = Tally.__new__(Tally)
        assert str(t) == "Tally: (unparsed)"
        assert repr(t) == "TALLY: (unparsed)"

    def test_all_fixture_tallies_fully_parse(self, tally_problem):
        # Force a full parse of every tally in the fixture, including the
        # path/lattice/universe forms (104, 114, 154, 1464, 174, 184, 194)
        # that no other test touches directly.
        for t in tally_problem.tallies:
            groups = t.groups
            assert groups is not None
            assert len(groups) > 0
            _ = t.include_total

    def test_include_total(self, tally_problem):
        assert tally_problem.tallies[24].include_total is True
        assert tally_problem.tallies[34].include_total is True
        assert tally_problem.tallies[1].include_total is False

    def test_contains_linked_flat_group(self, tally_problem):
        f34 = tally_problem.tallies[34]
        assert tally_problem.cells[1] in f34
        assert tally_problem.cells[99] not in f34

    def test_contains_linked_path_group(self, tally_problem):
        f64 = tally_problem.tallies[64]
        assert tally_problem.cells[1] in f64

    def test_contains_forces_full_parse(self, tally_problem):
        # __contains__ is @needs_full_ast: membership must be checked
        # against real data, not silently read as False while still JIT.
        f34 = tally_problem.tallies[34]
        assert not f34.fully_parsed
        assert tally_problem.cells[1] in f34
        assert f34.fully_parsed

    def test_contains_unlinked_flat_group_by_number_only(self):
        t = F4Tally(Input(["f4:n 1 2 3"], BlockType.DATA))

        class FakeCellByNumber:
            number = 2

        assert FakeCellByNumber() in t

    def test_contains_unlinked_flat_group_by_old_number(self):
        t = F4Tally(Input(["f4:n 1 2 3"], BlockType.DATA))

        class FakeCellByOldNumber:
            old_number = 2

        assert FakeCellByOldNumber() in t

    def test_number_validator_rejects_wrong_digit(self, tally_problem):
        f34 = tally_problem.tallies[34]
        with pytest.raises(ValueError):
            f34.number = 16

    def test_clone_unlinked_tally(self):
        t = F4Tally(Input(["f4:n 1 2 3"], BlockType.DATA))
        clone = t.clone()
        assert clone.number != t.number
        assert clone.number % 10 == 4

    def test_clone_as_unlinked_tally(self):
        t = F4Tally(Input(["f4:n 1 2 3"], BlockType.DATA))
        new = t.clone_as(F6Tally)
        assert isinstance(new, EnergyDepositionTally)
        assert new.number % 10 == 6

    def test_clone_as_same_type_delegates_to_clone(self, tally_problem):
        f34 = tally_problem.tallies[34]
        new = f34.clone_as(type(f34))
        assert new.number % 10 == 4
        assert new in tally_problem.tallies

    def test_clone_starting_number_needs_alignment(self, tally_problem):
        # starting_number's digit (9) doesn't match the tally type's digit
        # (4), forcing _align_to_type's "aligned < start" +10 branch.
        f34 = tally_problem.tallies[34]
        new = f34.clone(starting_number=9)
        assert new.number % 10 == 4
        assert new.number >= 14

    def test_blank_tally_construction(self):
        t = F4Tally()
        assert t.groups == []


class TestTallyBuilders:
    """Tests for the from-scratch tally-building API: add_surface, add_group,
    add_path_group, and PathGroup.inside chaining."""

    def test_surface_tally_add_surface_and_group(self, tally_problem):
        f1 = tally_problem.tallies[1]  # f1:n,p 1000 -- only surface 1000 so far
        s = tally_problem.surfaces[1005]
        f1.add_surface(s)
        assert s in f1.surfaces
        assert f1.groups[-1].old_numbers == [s.number]

        s_already_present = tally_problem.surfaces[1000]
        s_new = tally_problem.surfaces[1010]
        f1.add_group([s_already_present, s_new])
        assert f1.groups[-1].is_grouped
        assert set(f1.groups[-1].old_numbers) == {
            s_already_present.number,
            s_new.number,
        }
        assert s_new in f1.surfaces

    def test_surface_tally_add_path_group_and_inside_chaining(self, tally_problem):
        f1 = tally_problem.tallies[1]
        s1, s2 = tally_problem.surfaces[1000], tally_problem.surfaces[1005]
        pg = f1.add_path_group(s1)
        assert isinstance(pg, PathGroup)
        pg.inside(s2, lattice=[0, 0, 0])
        assert pg in f1.groups
        assert len(pg.levels) == 2

        # Re-linking must recurse into the newly added PathGroup too.
        f1.link_to_problem(tally_problem)
        assert s1 in f1.surfaces and s2 in f1.surfaces

    def test_link_group_surfaces_skips_missing_surface(self, tally_problem):
        f1 = tally_problem.tallies[1]
        _ = f1.surfaces  # force full parse
        f1._groups.append(FlatGroup([99999], is_grouped=False))
        f1.link_to_problem(tally_problem)
        assert 99999 not in list(f1.surfaces.numbers)

    def test_cell_tally_add_group(self, tally_problem):
        f34 = tally_problem.tallies[34]  # cells 1,2,3,5 -- 99 is new
        c_already_present = tally_problem.cells[1]
        c_new = tally_problem.cells[99]
        f34.add_group([c_already_present, c_new])
        assert f34.groups[-1].is_grouped
        assert set(f34.groups[-1].old_numbers) == {
            c_already_present.number,
            c_new.number,
        }
        assert c_new in f34.cells

    def test_cell_tally_add_path_group_and_inside_chaining(self, tally_problem):
        f34 = tally_problem.tallies[34]
        c1, c2 = tally_problem.cells[1], tally_problem.cells[2]
        pg = f34.add_path_group(c1)
        assert isinstance(pg, PathGroup)
        pg.inside(c2)
        assert pg in f34.groups
        assert len(pg.levels) == 2


def verify_export(tally):
    """Format ``tally`` to MCNP text, re-parse it standalone, and confirm
    the result is equivalent. Mirrors the ``verify_export`` convention in
    ``tests/test_surfaces.py``/``tests/test_cell_problem.py``."""
    output = tally.format_for_mcnp_input((6, 3, 0))
    joined = "\n".join(output)
    assert joined == tally.mcnp_str((6, 3, 0))
    new_tally = type(tally)(joined)
    assert new_tally.number == tally.number
    assert new_tally.tally_type == tally.tally_type
    assert new_tally.include_total == tally.include_total
    assert len(new_tally.groups) == len(tally.groups)
    for old_group, new_group in zip(tally.groups, new_tally.groups):
        assert isinstance(new_group, type(old_group))
        if isinstance(old_group, FlatGroup):
            assert old_group.is_grouped == new_group.is_grouped
    return new_tally


def verify_prob_export(problem, tally):
    """Write the whole ``problem`` out and re-read it, returning the
    equivalent tally from the new problem. The only test shape that can
    catch bugs in problem/collection-level registration (e.g. an FM card
    silently missing from ``data_inputs``), since a per-object
    :func:`verify_export` check never sees the problem at all."""
    with io.StringIO() as fh:
        problem.write_problem(fh)
        fh.seek(0)
        new_problem = montepy.read_input(fh)
    return new_problem.tallies[tally.number]


class TestGroupRoundTrip:
    """Mutating a Tally's groups through the public API must be reflected in
    mcnp_str(), not just in the in-memory Python state. These lock in the
    Tally._update_values / FlatGroup/PathGroup node-generation layer."""

    def test_unmodified_tally_round_trips_exactly(self, tally_problem):
        for number in (4, 14, 24, 34, 44, 54, 64, 74, 84, 94):
            tally = tally_problem.tallies[number]
            before = tally.mcnp_str()
            tally.full_parse()
            assert tally.mcnp_str() == before
            verify_export(tally)

    def test_add_cell_reflected_in_mcnp_str(self):
        t = F4Tally(Input(["f4:n 1 2 3"], BlockType.DATA), jit_parse=False)
        cell = montepy.Cell()
        cell.number = 99
        t.add_cell(cell)
        assert "99" in t.mcnp_str()
        assert "1" in t.mcnp_str() and "2" in t.mcnp_str() and "3" in t.mcnp_str()
        verify_export(t)

    def test_blank_tally_add_cell_writes_valid_card(self):
        t = F4Tally()
        t.number = 4
        cell = montepy.Cell()
        cell.number = 1
        t.add_cell(cell)
        text = t.mcnp_str()
        assert "1" in text
        # the unfixed bug wrote out only 'F 4 ', with no cell number at all
        assert text.strip() != "F 4"

    def test_add_group_reflected_in_mcnp_str(self):
        t = F4Tally(Input(["f4:n 1 2 3"], BlockType.DATA), jit_parse=False)
        c1, c2 = montepy.Cell(), montepy.Cell()
        c1.number = 10
        c2.number = 11
        t.add_group([c1, c2])
        text = t.mcnp_str()
        assert "10" in text and "11" in text
        assert "(" in text and ")" in text
        verify_export(t)

    def test_renumbered_cell_reflected_in_mcnp_str(self):
        t = F4Tally(Input(["f4:n 1 2 3"], BlockType.DATA), jit_parse=False)
        cell = montepy.Cell()
        cell.number = 99
        t.add_cell(cell)
        cell.number = 199
        text = t.mcnp_str()
        assert "199" in text
        assert "99" not in text.replace("199", "")
        verify_export(t)

    def test_include_total_settable(self):
        t = F4Tally(Input(["f4:n 1 2 3"], BlockType.DATA), jit_parse=False)
        assert not t.include_total
        t.include_total = True
        assert t.include_total
        assert t.mcnp_str().strip().endswith("T")
        t.include_total = False
        assert not t.include_total
        assert not t.mcnp_str().strip().endswith("T")

    def test_remove_cell_reflected_in_mcnp_str(self):
        t = F4Tally(Input(["f4:n 1 2 3"], BlockType.DATA), jit_parse=False)
        cell = montepy.Cell()
        cell.number = 99
        t.add_cell(cell)
        assert "99" in t.mcnp_str()
        t.remove_cell(cell)
        assert "99" not in t.mcnp_str()
        assert cell not in t.cells

    def test_remove_cell_keeps_cell_if_referenced_elsewhere(self):
        t = F4Tally(Input(["f4:n 1 2 3"], BlockType.DATA), jit_parse=False)
        cell = montepy.Cell()
        cell.number = 99
        other = montepy.Cell()
        other.number = 98
        t.add_cell(cell)
        t.add_group([cell, other])
        t.remove_cell(cell)
        assert cell in t.cells
        assert "99" in t.mcnp_str()

    def test_remove_cell_raises_if_not_a_single_cell_group(self):
        t = F4Tally(Input(["f4:n 1 2 3"], BlockType.DATA), jit_parse=False)
        cell = montepy.Cell()
        cell.number = 99
        with pytest.raises(ValueError):
            t.remove_cell(cell)

    def test_remove_group_reflected_in_mcnp_str(self):
        t = F4Tally(Input(["f4:n 1 2 3"], BlockType.DATA), jit_parse=False)
        c1, c2 = montepy.Cell(), montepy.Cell()
        c1.number = 10
        c2.number = 11
        t.add_group([c1, c2])
        group = t.groups[-1]
        t.remove_group(group)
        text = t.mcnp_str()
        assert "10" not in text and "11" not in text
        assert c1 not in t.cells and c2 not in t.cells

    def test_remove_surface_reflected_in_mcnp_str(self, tally_problem):
        f1 = tally_problem.tallies[1]
        s = tally_problem.surfaces[1005]
        f1.add_surface(s)
        assert "1005" in f1.mcnp_str()
        f1.remove_surface(s)
        assert "1005" not in f1.mcnp_str()
        assert s not in f1.surfaces


class TestReprAndEquality:
    """Smoke tests for __repr__ and __eq__-against-wrong-type on the small
    standalone value objects in tally.py. Coverage only counts a line as hit
    if it executes, and pytest only reprs on assertion *failure*, so these
    branches need explicit exercising."""

    def test_lattice_index(self):
        li = LatticeIndex([1, (2, 3)])
        assert li.dimensions == [1, (2, 3)]
        assert "LatticeIndex" in repr(li)

    def test_tally_group_contains_not_implemented(self):
        with pytest.raises(NotImplementedError):
            1 in TallyGroup()

    def test_particle_filter_eq_wrong_type_and_repr(self):
        obj = ParticleFilter([montepy.Particle.NEUTRON])
        assert obj != "not a filter"
        assert "ParticleFilter" in repr(obj)

    def test_spatial_filter_eq_wrong_type_and_repr(self):
        obj = SpatialFilter([FlatGroup([1], is_grouped=False)])
        assert obj != "not a filter"
        assert "SpatialFilter" in repr(obj)

    def test_flat_group_properties_and_repr(self):
        fg = FlatGroup([1, 2], is_grouped=True, universe_spec=3)
        assert fg.old_numbers == [1, 2]
        assert fg.is_grouped is True
        assert fg.universe_spec == 3
        assert "FlatGroup" in repr(fg)

    def test_path_group_levels_and_repr(self):
        pg = PathGroup([FlatGroup([1], is_grouped=False)])
        assert len(pg.levels) == 1
        assert "PathGroup" in repr(pg)

    def test_path_group_empty_levels_contains(self):
        assert 1 not in PathGroup([])

    def test_tally_parent_collections(self):
        from montepy.data_inputs.tally import Tally

        assert Tally._parent_collections() == ()
