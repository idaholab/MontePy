class Isotope:
    """A class to represent an MCNP isotope

    .. deprecated:: 0.4.1

        This will class is deprecated, and has been renamed: :class:`~montepy.data_inputs.nuclide.Nuclide`.
        For more details see the :ref:`migrate 0 1`.

    Raises
    ------
    DeprecationWarning
        Whenever called.
    """

    def __init__(self, *args, **kwargs):
        raise DeprecationWarning(
            "montepy.data_inputs.isotope.Isotope is deprecated and is renamed: Nuclide.\n"
            "See <https://www.montepy.org/migrations/migrate0_1.html> for more information "
        )
