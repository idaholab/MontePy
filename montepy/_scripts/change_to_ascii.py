import argparse
import sys


def define_args(args):
    """
    Parses the arguments from the command line.

    :param args: the arguments from the command line.
    :type args: list
    :returns: the parsed arguments (with argparse)
    :rtype: argparse.Namespace
    """
    parser = argparse.ArgumentParser(
        prog="Change_to_ascii",
        description="Change the encoding of a file to strict ASCII. Everything not compliant will be removed.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-d",
        "--delete",
        dest="delete",
        action="store_true",
        help="Delete any non-ascii characters. This is the default.",
    )
    group.add_argument(
        "-w",
        "--whitespace",
        dest="whitespace",
        action="store_true",
        help="Replace non-ascii characters with a space.",
    )
    parser.add_argument("in_file", nargs=1, help="The input file to convert")
    parser.add_argument("out_file", nargs=1, help="The input file to convert")
    args = parser.parse_args(args)
    return args


def strip_characters(args):
    """
    Strips non-ascii characters from the input file, and writes out the output file.

    :param args: the parsed command line arguments.
    :type args: argparse.Namespace
    """
    if args.whitespace:
        replacer = " "
    elif args.delete:
        replacer = ""
    # default to delete
    else:
        replacer = ""
    with open(args.in_file[0], "rb") as in_fh, open(args.out_file[0], "wb") as out_fh:
        for line in in_fh:
            utf8_line = line.decode(encoding="utf8", errors="replace")
            utf8_line = utf8_line.replace("�", replacer)

            try:
                out_fh.write(utf8_line.encode(encoding="ascii", errors="strict"))
            except UnicodeError as e:
                new_line = []
                # find the bad characters character by character
                for char in utf8_line:
                    if ord(char) > 128:
                        new_line.append(replacer)
                    else:
                        new_line.append(char)
                out_fh.write(
                    "".join(new_line).encode(encoding="ascii", errors="strict")
                )


def main(args=None):
    """
    Main runner function.

    :param args: The arguments passed from the command line.
    :type args: list
    """
    if args is None:
        args = sys.argv[1:]
    args = define_args(args)
    strip_characters(args)


if __name__ == "__main__":
    main(sys.argv[1:])
