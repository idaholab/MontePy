# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import pytest

from montepy.data_inputs.mode import Mode
from montepy.input_parser.block_type import BlockType
from montepy.input_parser.mcnp_input import Input
from montepy.particle import Particle
import montepy


def test_mode_init():
    in_str = "mode n p"
    # Test with string
    mode = Mode(in_str)
    assert len(mode) == 2
    assert Particle.NEUTRON in mode
    assert Particle.PHOTON in mode.particles
    # Test with Input object (constructor test)
    mode2 = Mode(Input([in_str], BlockType.CELL))
    assert len(mode2) == 2
    assert Particle.NEUTRON in mode2
    assert Particle.PHOTON in mode2.particles
    # test bad input
    in_str = "kcode"
    with pytest.raises(montepy.exceptions.MalformedInputError):
        Mode(in_str)
    in_str = "mode 1"
    with pytest.raises(TypeError):
        Mode(in_str)
    mode = Mode()
    assert len(mode) == 1
    assert Particle.NEUTRON in mode


def test_mode_add():
    mode = Mode()
    with pytest.raises(TypeError):
        mode.add(5)
    with pytest.raises(ValueError):
        mode.add("5")
    mode.add("p")
    assert Particle.PHOTON in mode
    mode.add(Particle.NEGATIVE_MUON)
    assert Particle.NEGATIVE_MUON in mode
    assert len(mode) == 3


def test_mode_remove():
    mode = Mode()
    with pytest.raises(TypeError):
        mode.remove(5)
    with pytest.raises(ValueError):
        mode.remove("5")
    mode.remove("n")
    assert len(mode) == 0
    assert Particle.NEUTRON not in mode
    mode.add("p")
    # force update of syntax tree
    output = mode.format_for_mcnp_input((6, 2, 0))
    mode.remove(Particle.PHOTON)
    assert len(mode) == 0
    assert Particle.PHOTON not in mode
    output = mode.format_for_mcnp_input((6, 2, 0))
    assert "p" not in output[0].lower()


def test_mode_iter():
    mode = Mode()
    mode.add("p")
    parts = [Particle.NEUTRON, Particle.PHOTON]
    i = 0
    for particle in mode:
        assert particle in parts
        i += 1
    assert i == 2


def test_mode_format_input():
    mode = Mode()
    mode.add("e")
    mode.add("p")
    output = mode.format_for_mcnp_input((6, 2, 0))
    print(output)
    assert len(output) == 1
    assert "MODE" in output[0]
    assert "N" in output[0]
    assert "P" in output[0]
    assert "E" in output[0]


def test_set_mode():
    particles = {Particle.ELECTRON, Particle.PHOTON}
    mode = Mode()
    mode.set("e p")
    assert len(mode) == 2
    for part in particles:
        assert part in mode
    mode = Mode()
    mode.set(["e", "p"])
    assert len(mode) == 2
    for part in particles:
        assert part in mode
    mode = Mode()
    mode.set(particles)
    assert len(mode) == 2
    for part in particles:
        assert part in mode
    with pytest.raises(TypeError):
        mode.set(5)
    with pytest.raises(TypeError):
        mode.set([5])
    with pytest.raises(ValueError):
        mode.set(["n", Particle.PHOTON])
    with pytest.raises(ValueError):
        mode.set([Particle.PHOTON, "n"])
