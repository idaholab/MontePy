from mcnpy.errors import *
from mcnpy.data_cards import transform
from mcnpy.mcnp_card import MCNP_Card
from mcnpy.surfaces.surface_type import SurfaceType
from mcnpy.utilities import *
import re


class Surface(MCNP_Card):
    """
    Object to hold a single MCNP surface
    """

    def __init__(self, input_card, comment=None):
        """
        :param input_card: The Card object representing the input
        :type input_card: Card
        :param comment: the Comment object representing the
                        preceding comment block.
        :type comment: Comment
        """
        super().__init__(input_card, comment)
        words = input_card.words
        self._periodic_surface = None
        self._old_periodic_surface = None
        self._transform = None
        self._old_transform_number = None
        self._surface_number = -1
        i = 0
        # surface number
        surface_num = words[i]
        if "*" in surface_num:
            self._is_reflecting = True
            surface_num = surface_num.strip("*")
        else:
            self._is_reflecting = False
        if "+" in surface_num:
            self._is_white_boundary = True
            surface_num = surface_num.strip("+")
        else:
            self._is_white_boundary = False

        try:
            surface_num = int(surface_num)
            assert surface_num > 0
            self._surface_number = surface_num
            self._old_surface_number = surface_num
        except (AssertionError, ValueError):
            raise MalformedInputError(
                input_card, f"{words[i]} could not be parsed as a surface number."
            )
        i += 1
        num_finder = re.compile("\d+")
        # handle N if specified
        if num_finder.search(words[i]):
            try:
                num = int(words[i])
                if num > 0:
                    self._old_transform_number = abs(num)
                elif num < 0:
                    self._old_periodic_surface = abs(num)
                i += 1
            except ValueError:
                raise MalformedInputError(
                    input_card,
                    f"{words[i]} could not be parsed as a periodic surface or a transform.",
                )
        # parse surface mnemonic
        try:
            self._surface_type = SurfaceType(words[i].upper())
        except ValueError:
            raise MalformedInputError(
                input_card,
                f"{words[i]} could not be parsed as a surface type mnemonic.",
            )
        # parse the parameters
        self._surface_constants = []
        for entry in words[i + 1 :]:
            try:
                self._surface_constants.append(fortran_float(entry))
            except ValueError:
                raise MalformedInputError(
                    input_card,
                    f"{entry} could not be parsed as a surface constant.",
                )

    @property
    def surface_type(self):
        """
        The mnemonic for the type of surface.

        E.g. CY, PX, etc.
        :rtype: SurfaceType
        """
        return self._surface_type

    @property
    def is_reflecting(self):
        """
        If true this surface is a reflecting boundary.

        :rtype: bool
        """
        return self._is_reflecting

    @is_reflecting.setter
    def is_reflecting(self, reflect):
        assert isinstance(reflect, bool)
        self._mutated = True
        self._is_reflecting = reflect

    @property
    def is_white_boundary(self):
        """
        If true this surface is a white boundary.

        :rtype: bool
        """
        return self._is_white_boundary

    @is_white_boundary.setter
    def is_white_boundary(self, white):
        assert isinstance(white, bool)
        self._mutated = True
        self._is_white_boundary = white

    @property
    def surface_constants(self):
        """
        The constants defining the surface

        :rtype: list
        """
        return self._surface_constants

    @surface_constants.setter
    def surface_constants(self, constants):
        assert isinstance(constants, list)
        for constant in constants:
            assert isinstance(constant, float)
        self._mutated = True
        self._surface_constants = constants

    @property
    def old_transform_number(self):
        """
        The transformation number for this surface in the original file.

        TODO connect and allow updates
        :rtype: int
        """
        return self._old_transform_number

    @property
    def old_periodic_surface(self):
        """
        The surface number this is periodic with reference to in the original file.
        """
        return self._old_periodic_surface

    @property
    def periodic_surface(self):
        """
        The surface that this surface is periodic with respect to
        """
        return self._periodic_surface

    @periodic_surface.setter
    def periodic_surface(self, periodic):
        assert isinstance(periodic, Surface)
        self._mutated = True
        self._periodic_surface = periodic

    @periodic_surface.deleter
    def periodic_surface(self):
        self._mutated = True
        self._periodic_surface = None

    @property
    def transform(self):
        """
        The Transform object that translates this surface

        :rtype:Transform
        """
        return self._transform

    @transform.setter
    def transform(self, tr):
        assert isinstance(tr, transform.Transform)
        self._mutated = True
        self._transform = tr

    @transform.deleter
    def transform(self):
        self._mutated = True
        self._transform = None
        self._old_transform_number = None

    @property
    def old_number(self):
        """
        The surface number that was used in the read file
        :rtype: int
        """
        return self._old_surface_number

    @property
    def number(self):
        """
        The surface number to use.
        :rtype: int
        """
        return self._surface_number

    @number.setter
    def number(self, number):
        assert isinstance(number, int)
        assert number > 0
        self._mutated = True
        self._surface_number = number

    def __str__(self):
        return f"SURFACE: {self.number}, {self.surface_type}"

    def __repr__(self):
        return self.__str__()

    def update_pointers(self, surface_dict, data_cards):
        """
        Updates the internal pointers to the appropriate objects.

        Right now only periodic surface links will be made.
        Eventually transform pointers should be made.
        """
        if self.old_periodic_surface:
            try:
                self._periodic_surface = surface_dict[self.old_periodic_surface]
            except KeyError:
                raise BrokenObjectLinkError(
                    "Surface",
                    self.number,
                    "Periodic Surface",
                    self.old_periodic_surface,
                )
        if self.old_transform_number:
            for card in data_cards:
                if isinstance(card, transform.Transform):
                    if card.number == self.old_transform_number:
                        self._transform = card
            if not self.transform:
                raise BrokenObjectLinkError(
                    "Surface",
                    self.number,
                    "Transform",
                    self.old_transform_number,
                )

    def format_for_mcnp_input(self, mcnp_version):
        ret = super().format_for_mcnp_input(mcnp_version)
        if self.mutated:
            buffList = []
            # surface number
            if self.is_reflecting:
                buffList.append(f"*{self.number}")
            elif self.is_white_boundary:
                buffList.append(f"+{self.number}")
            else:
                buffList.append(str(self.number))

            if self.periodic_surface:
                buffList.append(str(-self.periodic_surface.number))
            elif self.transform:
                buffList.append(str(self.transform.number))

            buffList.append(self.surface_type.value)

            for constant in self.surface_constants:
                buffList.append(f"{constant:.6g}")
            ret += Surface.wrap_words_for_mcnp(buffList, mcnp_version, True)
        else:
            ret += self.input_lines
        return ret

    def __lt__(self, other):
        return self.number < other.number

    def __eq__(self, other):
        return (
            self.number == other.number
            and self.surface_type == other.surface_type
            and self.is_reflecting == other.is_reflecting
            and self.is_white_boundary == other.is_white_boundary
            and self.surface_constants == other.surface_constants
        )

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((self.number, str(self.surface_type)))

    def __eq__(self, other):
        return (
            self.number == other.number
            and self.surface_type == other.surface_type
            and self.is_reflecting == other.is_reflecting
            and self.is_white_boundary == other.is_white_boundary
            and self.surface_constants == other.surface_constants
        )

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((self.number, str(self.surface_type)))

    def find_duplicate_surfaces(self, surfaces, tolerance):
        """Finds all surfaces that are effectively the same as this one.

        :param surfaces: a list of the surfaces to compare against this one.
        :type surfaces: list
        :param tolerance: the amount of relative error to allow
        :type tolerance: float
        :returns: A list of the surfaces that are identical
        :rtype: list
        """
        return []
