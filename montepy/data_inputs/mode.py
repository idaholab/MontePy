# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from montepy.data_inputs.data_input import DataInputAbstract
from montepy.input_parser import syntax_node
from montepy.particle import Particle


class Mode(DataInputAbstract):
    """
    Class for the particle mode for a problem.

    :param input: the Input object representing this data input
    :type input: Input
    """

    def __init__(self, input=None):
        super().__init__(input)
        if input:
            self._particles = set()
            self._parse_and_override_particle_modes(
                [p.value for p in self._tree["data"]]
            )
        else:
            self._particles = {Particle.NEUTRON}
            classifier = syntax_node.ClassifierNode()
            classifier.prefix = self._generate_default_node(str, "MODE")
            classifier.padding = syntax_node.PaddingNode(" ")
            self._tree = syntax_node.SyntaxNode(
                "mode",
                {
                    "classifier": classifier,
                    "data": syntax_node.ListNode("particles"),
                },
            )

    def _parse_and_override_particle_modes(self, particles):
        self._particles = set()
        for particle in particles:
            if not isinstance(particle, str):
                raise TypeError(f"Mode particle must be a str. {particle} given.")
            self._particles.add(Particle(particle.upper()))

    @property
    def particles(self):
        """
        The type of particles involved in this problem.

        The set will contain instances of :class:`montepy.particle.Particle`.

        :rtype: set
        """
        return self._particles.copy()

    def add(self, particle):
        """
        Adds the given particle to the problem.

        If specifying particle type by string this must be the MCNP shorthand,
        such as ``n`` for ``Particle.NEUTRON``.

        :param particle: the particle type to add to the mode.
        :type particle: Particle, str
        :raises ValueError: if string is not a valid particle shorthand.
        """
        if not isinstance(particle, (Particle, str, syntax_node.ValueNode)):
            raise TypeError("particle must be a Particle instance")
        if isinstance(particle, (str, syntax_node.ValueNode)):
            # error catching not needed
            # enum will raise ValueError "foo is not a valid Particle"
            if isinstance(particle, syntax_node.ValueNode):
                particle = particle.value
            particle = Particle(particle.upper())
        self._particles.add(particle)

    def remove(self, particle):
        """
        Remove the given particle from the problem

        :param particle: the particle type to remove from the mode.
        :type particle: Particle, str
        :raises ValueError: if string is not a valid particle shorthand.
        """
        if not isinstance(particle, (Particle, str)):
            raise TypeError("particle must be a Particle instance")
        if isinstance(particle, str):
            particle = Particle(particle.upper())
        self._particles.remove(particle)

    def set(self, particles):
        """
        Completely override the current mode.

        Can specify it as:
         * ``"n p"``
         * ``["n", "p"]``
         * ``[Particle.NEUTRON, Particle.PHOTON]``

        :param particles: the particles that the mode will be switched to.
        :type particles: list, str
        :raises ValueError: if string is not a valid particle shorthand.
        """
        if not isinstance(particles, (list, set, str)):
            raise TypeError("particles must be a list, string, or set")
        if isinstance(particles, (list, set)):
            is_str = True
            for particle in particles:
                if not isinstance(particle, (str, Particle)):
                    raise TypeError("particle must be a Particle or string")
                if not isinstance(particle, str):
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

    def __contains__(self, obj):
        return obj in self._particles

    def __iter__(self):
        return iter(self._particles)

    def __len__(self):
        return len(self._particles)

    def __str__(self):
        return f"Mode: {self.particles}"

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
