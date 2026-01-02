# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from montepy.utilities import *
from montepy.data_inputs.data_input import DataInputAbstract, InitInput
from montepy.input_parser import syntax_node
from montepy.particle import Particle
import montepy.types as ty


class Mode(DataInputAbstract):
    """Class for the particle mode for a problem.

    Parameters
    ----------
    input : Input
        the Input object representing this data input
    """

    def _init_blank(self):
        self._particles = {Particle.NEUTRON}

    def _parse_tree(self):
        super()._parse_tree()
        self._particles = set()
        self._parse_and_override_particle_modes([p.value for p in self._tree["data"]])

    def _parse_and_override_particle_modes(self, particles):
        self._particles = set()
        for particle in particles:
            if not isinstance(particle, str):
                raise TypeError(f"Mode particle must be a str. {particle} given.")
            self._particles.add(Particle(particle.upper()))

    def _generate_default_tree(self):
        super()._generate_default_tree()
        self._tree["data"].append(self._generate_default_node(str, "N"))

    @property
    @needs_full_ast
    def particles(self):
        """The type of particles involved in this problem.

        The set will contain instances of :class:`montepy.particle.Particle`.

        Returns
        -------
        set
        """
        return self._particles.copy()

    @args_checked
    @needs_full_cst
    def add(self, particle: Particle | str | syntax_node.ValueNode):
        """Adds the given particle to the problem.

        If specifying particle type by string this must be the MCNP shorthand,
        such as ``n`` for ``Particle.NEUTRON``.

        Parameters
        ----------
        particle : Particle, str
            the particle type to add to the mode.

        Raises
        ------
        ValueError
            if string is not a valid particle shorthand.
        """
        if isinstance(particle, (str, syntax_node.ValueNode)):
            # error catching not needed
            # enum will raise ValueError "foo is not a valid Particle"
            if isinstance(particle, syntax_node.ValueNode):
                particle = particle.value
            particle = Particle(particle.upper())
        self._particles.add(particle)

    @args_checked
    @needs_full_cst
    def remove(self, particle: Particle | str):
        """Remove the given particle from the problem

        Parameters
        ----------
        particle : Particle, str
            the particle type to remove from the mode.

        Raises
        ------
        ValueError
            if string is not a valid particle shorthand.
        """
        if isinstance(particle, str):
            particle = Particle(particle.upper())
        self._particles.remove(particle)

    @args_checked
    @needs_full_cst
    def set(self, particles: str | ty.Iterable[Particle | str]):
        """Completely override the current mode.

        Can specify it as:
         * ``"n p"``
         * ``["n", "p"]``
         * ``[Particle.NEUTRON, Particle.PHOTON]``

        Parameters
        ----------
        particles : list, str
            the particles that the mode will be switched to.

        Raises
        ------
        ValueError
            if string is not a valid particle shorthand.
        """
        if isinstance(particles, ty.Iterable) and not isinstance(particles, str):
            is_str = True
            for particle in particles:
                if isinstance(particle, Particle):
                    is_str = False
        else:
            particles = particles.split()
            is_str = True
        if is_str:
            self._parse_and_override_particle_modes(particles)
        else:
            for particle in particles:
                if not isinstance(particle, Particle):
                    raise ValueError("cannot mix particle and string in mode")
            self._particles = set(particles)

    @needs_full_ast
    def __contains__(self, obj):
        return obj in self._particles

    @needs_full_ast
    def __iter__(self):
        return iter(self._particles)

    @needs_full_ast
    def __len__(self):
        return len(self._particles)

    @staticmethod
    def _class_prefix():
        return "mode"

    @staticmethod
    def _has_number():
        return False

    @staticmethod
    def _has_classifier():
        return 0

    def _update_values(self):
        old_particles = {}
        for particle in self._tree["data"]:
            part = Particle(particle.value.upper())
            old_particles[part] = particle
        old_parts = set(old_particles.keys())
        to_remove = old_parts - self.particles
        to_add = self.particles - old_parts
        for removal in to_remove:
            node = old_particles[removal]
            self._tree["data"].remove(node)
        for addition in to_add:
            self._tree["data"].append(self._generate_default_node(str, addition.value))
