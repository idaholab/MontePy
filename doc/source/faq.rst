Frequently Asked Questions
==========================

Or more likely Frequent Error Debugging.

Encoding Errors: UnicodeDecodeError
-----------------------------------

If you received the error below while opening a file in MontePy,
there is like a non-ASCII character in your input file.
You can read more about :ref:`Character Encoding here <encoding_background>`.

To solve this problem you can:

1. Try another encoding such as ``'utf8'`` or ``'cp1252'``. Pass it as an argument to :func:`~montepy.input_parser.input_reader.read_input`.
2. Remove all non-ASCII characters with :ref:`the change_to_ascii utility <convert_ascii>`

.. code-block:: python

      ---------------------------------------------------------------------------
        UnicodeDecodeError                        Traceback (most recent call last)
        Cell In[2], line 1
        ----> 1 problem = montepy.read_input("tests/inputs/bad_encoding.imcnp")

        File ~/dev/montepy/montepy/input_parser/input_reader.py:35, in read_input(input_file, mcnp_version, encoding)
             33 problem = mcnp_problem.MCNP_Problem(input_file)
             34 problem.mcnp_version = mcnp_version
        ---> 35 problem.parse_input(encoding=encoding)
             36 return problem

        File ~/dev/montepy/montepy/mcnp_problem.py:262, in MCNP_Problem.parse_input(self, check_input, encoding)
            253 OBJ_MATCHER = {
            254     block_type.BlockType.CELL: (Cell, self._cells),
            255     block_type.BlockType.SURFACE: (
           (...)
            259     block_type.BlockType.DATA: (parse_data, self._data_inputs),
            260 }
            261 try:
        --> 262     for i, input in enumerate(
            263         input_syntax_reader.read_input_syntax(
            264             self._input_file, self.mcnp_version, encoding=encoding
            265         )
            266     ):
            267         self._original_inputs.append(input)
            268         if i == 0 and isinstance(input, mcnp_input.Message):

        File ~/dev/montepy/montepy/input_parser/input_syntax_reader.py:48, in read_input_syntax(input_file, mcnp_version, encoding)
             46 reading_queue = deque()
             47 with input_file.open("r", encoding=encoding) as fh:
        ---> 48     yield from read_front_matters(fh, mcnp_version)
             49     yield from read_data(fh, mcnp_version)

        File ~/dev/montepy/montepy/input_parser/input_syntax_reader.py:79, in read_front_matters(fh, mcnp_version)
             77 lines = []
             78 raw_lines = []
        ---> 79 for i, line in enumerate(fh):
             80     if i == 0 and line.upper().startswith("MESSAGE:"):
             81         is_in_message_block = True

        File ~/dev/montepy/montepy/input_parser/input_file.py:95, in MCNP_InputFile.__iter__(self)
             94 def __iter__(self):
        ---> 95     for lineno, line in enumerate(self._fh):
             96         self._lineno = lineno + 1
             97         yield line

        File ~/mambaforge/lib/python3.10/encodings/ascii.py:26, in IncrementalDecoder.decode(self, input, final)
             25 def decode(self, input, final=False):
        ---> 26     return codecs.ascii_decode(input, self.errors)[0]

        UnicodeDecodeError: 'ascii' codec can't decode byte 0xff in position 159: ordinal not in range(128)
