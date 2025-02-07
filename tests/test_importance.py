# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import montepy
from montepy.cell import Cell
from montepy.particle import Particle
from montepy.data_inputs.importance import Importance
from montepy.errors import *
from montepy.input_parser import mcnp_input, block_type
import os
import pytest


def test_importance_init_cell():
    # test_normal cell init
    in_str = "1 0 -1 IMP:N,P=1"
    card = mcnp_input.Input([in_str], block_type.BlockType.CELL)
    cell = Cell(card)
    assert cell.importance.neutron == 1.0
    assert cell.importance.photon == 1.0
    assert cell.importance.alpha_particle == 0.0
    assert cell.importance.all is None
    assert cell.importance.in_cell_block
    # test non-number imp
    in_str = "1 0 -1 IMP:N,P=h"
    card = mcnp_input.Input([in_str], block_type.BlockType.CELL)
    with pytest.raises(ValueError):
        cell = Cell(card)
    # test negative imp
    in_str = "1 0 -1 IMP:N,P=-2"
    card = mcnp_input.Input([in_str], block_type.BlockType.CELL)
    with pytest.raises(ValueError):
        cell = Cell(card)


def test_importance_init_data():
    in_str = "IMP:N,P 1 0"
    card = mcnp_input.Input([in_str], block_type.BlockType.CELL)
    imp = Importance(card)
    assert [
        val.value for val in imp._particle_importances[Particle.NEUTRON]["data"]
    ] == [1.0, 0.0]
    assert [
        val.value for val in imp._particle_importances[Particle.PHOTON]["data"]
    ] == [1.0, 0.0]
    # test non-number imp
    in_str = "IMP:N,P 1 h"
    card = mcnp_input.Input([in_str], block_type.BlockType.CELL)
    with pytest.raises(ValueError):
        imp = Importance(card)
    # test negative
    in_str = "IMP:N,P 1 -2"
    card = mcnp_input.Input([in_str], block_type.BlockType.CELL)
    with pytest.raises(ValueError):
        imp = Importance(card)
    # test bad in_cell_block
    in_str = "IMP:N,P 1 2"
    card = mcnp_input.Input([in_str], block_type.BlockType.CELL)
    with pytest.raises(TypeError):
        imp = Importance(card, in_cell_block=1)
    # test bad key
    in_str = "IMP:N,P 1 2"
    card = mcnp_input.Input([in_str], block_type.BlockType.CELL)
    with pytest.raises(TypeError):
        imp = Importance(card, key=1)
    # test bad value
    in_str = "IMP:N,P 1 2"
    card = mcnp_input.Input([in_str], block_type.BlockType.CELL)
    with pytest.raises(TypeError):
        imp = Importance(card, value=1)


def test_importance_iter_getter_in():
    in_str = "1 0 -1 IMP:N,P=1"
    card = mcnp_input.Input([in_str], block_type.BlockType.CELL)
    cell = Cell(card)
    imp = cell.importance
    particles = [
        montepy.particle.Particle.NEUTRON,
        montepy.particle.Particle.PHOTON,
    ]
    for particle in imp:
        assert particle in particles
        assert imp[particle] == 1.0
    for particle in particles:
        assert particle in imp
    with pytest.raises(TypeError):
        imp["hi"]


def test_importance_all_setter():
    in_str = "1 0 -1 IMP:N,P=1"
    card = mcnp_input.Input([in_str], block_type.BlockType.CELL)
    cell = Cell(card)
    problem = montepy.mcnp_problem.MCNP_Problem("foo")
    problem.mode.add(montepy.particle.Particle.NEUTRON)
    problem.mode.add(montepy.particle.Particle.PHOTON)
    imp = cell.importance
    cell.link_to_problem(problem)
    imp.all = 2.0
    assert imp.neutron == 2.0
    assert imp.photon == 2.0
    # try wrong type
    with pytest.raises(TypeError):
        imp.all = "h"
    # try negative type
    with pytest.raises(ValueError):
        imp.all = -2.0


def test_importance_setter():
    in_str = "1 0 -1 IMP:N,P=1"
    card = mcnp_input.Input([in_str], block_type.BlockType.CELL)
    cell = Cell(card)
    cell.importance.neutron = 2.5
    assert cell.importance.neutron == 2.5
    problem = montepy.mcnp_problem.MCNP_Problem("foo")
    cell.link_to_problem(problem)
    # test problem mode enforcement
    with pytest.warns(ParticleTypeNotInProblem):
        cell.importance.photon = 1.0
    # test wrong type
    with pytest.raises(TypeError):
        cell.importance.neutron = "h"
    # test negative
    with pytest.raises(ValueError):
        cell.importance.neutron = -0.5

    cell.importance[Particle.NEUTRON] = 3
    assert cell.importance.neutron == 3.0
    with pytest.raises(TypeError):
        cell.importance[""] = 5
    with pytest.raises(TypeError):
        cell.importance[Particle.NEUTRON] = ""
    with pytest.raises(ValueError):
        cell.importance[Particle.NEUTRON] = -1.0


def test_importance_deleter():
    in_str = "1 0 -1 IMP:N,P=1"
    card = mcnp_input.Input([in_str], block_type.BlockType.CELL)
    cell = Cell(card)
    del cell.importance.neutron
    assert cell.importance.neutron == 0.0
    del cell.importance[Particle.PHOTON]
    assert cell.importance.photon == 0.0
    with pytest.raises(TypeError):
        del cell.importance[""]


def test_importance_merge():
    in_str = "IMP:N,P 1 0"
    card = mcnp_input.Input([in_str], block_type.BlockType.DATA)
    imp1 = Importance(card)
    in_str = "IMP:E 0 0"
    card = mcnp_input.Input([in_str], block_type.BlockType.DATA)
    imp2 = Importance(card)
    imp1.merge(imp2)
    assert [
        val.value for val in imp1._particle_importances[Particle.NEUTRON]["data"]
    ] == [1.0, 0.0]
    assert [
        val.value for val in imp1._particle_importances[Particle.ELECTRON]["data"]
    ] == [0.0, 0.0]
    # test bad type
    with pytest.raises(TypeError):
        imp1.merge("hi")
    # test bad block type
    in_str = "1 0 -1 IMP:N,P=1"
    card = mcnp_input.Input([in_str], block_type.BlockType.CELL)
    cell = Cell(card)
    with pytest.raises(ValueError):
        imp1.merge(cell.importance)
    in_str = "IMP:P 0 0"
    card = mcnp_input.Input([in_str], block_type.BlockType.CELL)
    imp2 = Importance(card)
    with pytest.raises(MalformedInputError):
        imp1.merge(imp2)


def tests_redundant_importance():
    with pytest.raises(MalformedInputError):
        montepy.read_input(os.path.join("tests", "inputs", "test_imp_redundant.imcnp"))
