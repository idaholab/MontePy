from mcnpy.data_inputs.data_input import DataInputAbstract
from mcnpy.input_parser.mode_parser import ModeParser
from mcnpy.particle import Particle


class Mode(DataInputAbstract):
    """
    Class for the particle mode for a problem.

    :param input: the Input object representing this data input
    :type input: Input
    :param comments: The Comment that may proceed this
    :type comments: Comment
    """

    _parser = ModeParser()

    def __init__(self, input=None, comments=None):
        super().__init__(input, comments)
        if input:
            self._particles = set()
            self._parse_and_override_particle_modes(self.words[1:])
        else:
            self._particles = {Particle.NEUTRON}

    def _parse_and_override_particle_modes(self, part_names):
        self._particles = set()
        for particle in part_names:
            self._particles.add(Particle(particle.upper()))

    @property
    def particles(self):
        """
        The type of particles involved in this problem.

        The set will contain instances of :class:`mcnpy.particle.Particle`.

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
        if not isinstance(particle, (Particle, str)):
            raise TypeError("particle must be a Particle instance")
        if isinstance(particle, str):
            # error catching not needed
            # enum will raise ValueError "foo is not a valid Particle"
            particle = Particle(particle.upper())
        self._mutated = True
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
        self._mutated = True
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

    def format_for_mcnp_input(self, mcnp_version):
        if self.mutated:
            words = ["MODE"]
            for particle in self.particles:
                words.append(particle.value)
            self.words = words
            ret = super().format_for_mcnp_input(mcnp_version)
        else:
            ret = self._format_for_mcnp_unmutated(mcnp_version)

        return ret
