# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.

import traceback


class LineOverRunWarning(UserWarning):
    """
    Raised when non-comment inputs exceed the allowed line length in an input.
    """

    def __init__(self, message):
        self.message = message


class MalformedInputError(ValueError):
    """
    Raised when there is an error with the MCNP input not related to the parser.
    """

    def __init__(self, input, message):
        if input and getattr(input, "input_file", None) and input.input_file:
            self.input = input
            path = input.input_file.path
            start_line = input.line_number
            self.path = path
            self.start = start_line
            lines = "\n".join(input.input_lines)
        else:
            path = ""
            start_line = 0
            lines = ""
        self.message = message
        super().__init__(self.message)


class ParsingError(MalformedInputError):
    """
    Raised when there is an error parsing the MCNP input at the SLY parsing layer.
    """

    def __init__(self, input, message, error_queue):
        messages = []
        if input and getattr(input, "input_file", None) and input.input_file:
            self.input = input
            path = input.input_file.path
            start_line = input.line_number
            self.path = path
            self.start = start_line
        else:
            path = ""
            start_line = 0
        if error_queue:
            for error in error_queue:
                if token := error["token"]:
                    line_no = error["line"]
                    index = error["index"]
                    self.rel_line = line_no
                    self.abs_line = line_no + start_line
                    base_message = f'There was an error parsing "{token.value}".'
                else:
                    line_no = 0
                    index = 0
                    base_message = f"The input ended prematurely."
                messages.append(
                    _print_input(
                        path,
                        start_line,
                        error["message"],
                        line_no,
                        input,
                        token,
                        base_message,
                        index,
                    )
                )
            self.message = "\n".join(messages + [message])
        else:
            self.message = message

        ValueError.__init__(self, self.message)


def _print_input(
    path,
    start_line,
    error_msg,
    line_no=0,
    input=None,
    token=None,
    base_message=None,
    index=None,
):
    buffer = [f"    {path}, line {start_line + line_no -1}", ""]
    if input:
        for i, line in enumerate(input.input_lines):
            if i == line_no - 1:
                buffer.append(f"    >{start_line + i:5g}| {line}")
                if token:
                    length = len(token.value)
                    marker = "^" * length
                    buffer.append(
                        f"{' '* 10}|{' ' * (index+1)}{marker} not expected here."
                    )
            else:
                buffer.append(f"     {start_line + i:5g}| {line}")
        if base_message:
            buffer.append(base_message)
        buffer.append(error_msg)
    return "\n".join(buffer)


class NumberConflictError(Exception):
    """
    Raised when there is a conflict in number spaces
    """

    def __init__(self, message):
        self.message = message
        super().__init__(message)


class BrokenObjectLinkError(MalformedInputError):
    """Raised when the referenced object does not exist in the input file."""

    def __init__(self, parent_type, parent_number, child_type, child_number):
        """
        :param parent_type: Name of the parent object linking (e.g., Cell)
        :type parent_type: str
        :param parent_number: the number of the parent object
        :type parent_number: int
        :param child_type: Name of the type of object missing in the link (e.g., surface)
        :type child_type: str
        :param child_number: the number for the missing object
        :type child_number: int
        """
        super().__init__(
            None,
            f"{child_type} {child_number} is missing from the input from the definition of: {parent_type} {parent_number}",
        )


class RedundantParameterSpecification(ValueError):
    """
    Raised when multiple conflicting parameters are given.

    e.g., ``1 0 -1 imp:n=5 imp:n=0``
    """

    def __init__(self, key, new_value):
        self.message = (
            f"Multiple values given for parameter: {key}. new_value given: {new_value}."
        )
        super().__init__(self.message)


class ParticleTypeNotInProblem(ValueError):
    """
    Raised when data are set for a particle type not in
    the problem's mode.
    """

    def __init__(self, message):
        self.message = message
        super().__init__(message)


class ParticleTypeNotInCell(ValueError):
    """
    Raised when data for importance data for a particle in
    the problem is not provided for a cell.
    """

    def __init__(self, message):
        self.message = message
        super().__init__(message)


class UnsupportedFeature(NotImplementedError):
    """
    Raised when MCNP syntax that is not supported is found
    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class UnknownElement(ValueError):
    """
    Raised when an undefined element is used.
    """

    def __init__(self, missing_val):
        self.message = f"An element identified by: {missing_val} is unknown to MontePy."
        super().__init__(self.message)


class IllegalState(ValueError):
    """
    Raised when an object can't be printed out due to an illegal state.
    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class LineExpansionWarning(Warning):
    """
    Warning for when a field or line expands that may damage user formatting.
    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


def add_line_number_to_exception(error, broken_robot):
    """
    Adds additional context to an Exception raised by an :class:`~montepy.mcnp_object.MCNP_Object`.

    This will add the line, file name, and the input lines to the error.

    :param error: The error that was raised.
    :type error: Exception
    :param broken_robot: The parent object that had the error raised.
    :type broken_robot: MCNP_Object
    :raises Exception: ... that's the whole point.
    """
    # avoid calling this n times recursively
    if hasattr(error, "montepy_handled"):
        raise error
    error.montepy_handled = True
    args = error.args
    trace = error.__traceback__
    if len(args) > 0:
        message = args[0]
    else:
        message = ""
    try:
        input_obj = broken_robot._input
        assert input_obj is not None
        lineno = input_obj.line_number
        file = str(input_obj.input_file)
        lines = input_obj.input_lines
        message = _print_input(file, lineno, message, input=input_obj)
    except Exception as e:
        try:
            message = (
                f"{message}\n\nError came from {broken_robot} from an unknown file."
            )
        except Exception as e2:
            message = f"{message}\n\nError came from an object of type {type(broken_robot)} from an unknown file."
    args = (message,) + args[1:]
    error.args = args
    raise error.with_traceback(trace)
