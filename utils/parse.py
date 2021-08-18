import re

_re_arg_splitter = re.compile(
    #       Match text in quotes as a single group
    #       V                          Match any number of double backslashes so that \" is a valid quote escape but \\" isn't.
    #       V                          V          Match \" within quotes
    #       V                          V          V        Match content within quotes
    #       V                          V          V        V          Match closing quote
    #       V                          V          V        V          V               Match unquoted content
    #       V                          V          V        V          V               V           End match with the end of the
    #       V                          V          V        V          V               V           string, a comma with any amount
    #       V                          V          V        V          V               V           of whitespace, or whitespace.
    #       V                          V          V        V          V               V           V
    r'\s*(?:(?:\"(?P<quoted_text>(?:(?:(?:\\\\)*)|(?:\\\")|(?:[^"]))*)\")|(?:(?P<text>[^\s,，]+)))(?P<tail>$|(?:\s*[,，]\s*)|(?:\s+))'
)
_re_remove_escaped_quote = re.compile(r'((?:[^\\]|^)(?:\\\\)*)\\"')


def split_args(args: str, treat_comma_as_space: bool = False) -> list[str]:
    """Splits a string of arguments into a list of arguments. Arguments are
    separated by spaces, unless `treat_comma_as_space` is `True` and `args`
    contains a comma not enclosed in quotes, in which case arguments are
    separated by commas. Arguments can also be grouped using quotes to include
    spaces or commas without being separated. Quotes escaped using a backslash
    can be included in quoted text. Double backslashes are also replaced with
    single backslashes.

    Examples
    -----------
    .. code-block:: python3
        split_args('A B C D') == ['A', 'B', 'C', 'D']

    .. code-block:: python3
        split_args('A B, C D', False) == ['A B', 'C D']

    .. code-block:: python3
        split_args('A B, C D', True) == ['A', 'B', 'C', 'D']

    .. code-block:: python3
        split_args('A "B C" D', False) == ['A', 'B C', 'D']

    .. code-block:: python3
        # Single escaped backslash
        split_args('A "B\\"C" D', False) == ['A', 'B"C', 'D']
    """
    comma_separated = False

    # Get matches
    matches = []
    for m in _re_arg_splitter.finditer(args):
        matches.append(m)
        comma_separated = comma_separated or (
            not treat_comma_as_space
            and m.group("tail") != ""
            and not m.group("tail").isspace()  # Checks for comma
        )

    # Matches can contain their arg in the groups "text" or "quoted_text"
    if not comma_separated:
        ret = [
            m.group("text") if m.group("text") is not None else m.group("quoted_text")
            for m in matches
        ]
    else:
        # If args are comma separated, group all matches in between commas
        # into a single string.
        ret = []

        # A list of matches that appear together before a comma
        combine: list[re.Match] = []
        for match in matches:
            if match.group("tail") and not match.group("tail").isspace():
                # If match ends with a comma, combine it with previous matches
                # without commas into one single arg.

                if match.group("text"):
                    ret.append(
                        "".join(m.group(0) for m in combine) + match.group("text")
                    )
                elif not combine:
                    # If the match contains text in quotes and there are no
                    # previous matches to combine it with, add only the text
                    # inside of the quotes to the list of arguments.
                    ret.append(match.group("quoted_text"))
                else:
                    ret.append(
                        "".join(m.group(0) for m in combine)
                        + match.group("quoted_text")
                    )
                combine = []
            else:
                combine.append(match)
        if combine:
            if len(combine) == 1 and combine[0].group("quoted_text") is not None:
                # If there is only one match that contains text in quotes add
                # only the text inside of the quotes to the list of arguments.
                last_arg = combine[0].group("quoted_text")
            else:
                # Otherwise, combine all remaining matches into one argument
                last_arg = "".join(m.group(0) for m in combine[:-1])
                # Exclude the tail of the last match
                last_match = combine[-1]
                last_arg += (
                    last_match.group("text")
                    if last_match.group("text") is not None
                    else last_match.group("quoted_text")
                )
            ret.append(last_arg)

    # Replace \" with " and \\ with \
    ret = [_re_remove_escaped_quote.sub(r'\1"', s).replace("\\\\", "\\") for s in ret]

    return ret