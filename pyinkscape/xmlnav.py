'''
Functions for navigating xml at the element level.

This module should not import pyinkscape.inkscape, since
that submodule imports this.
'''
from logging import getLogger

logger = getLogger(__name__)

SVG_NS = 'http://www.w3.org/2000/svg'


def emit_cast(value):
    ''' Show the type and value such as for logging '''
    return "{}({})".format(type(value), repr(value))


def clean_tag_str(tag, exclude="{"+SVG_NS+"}"):
    if isinstance(exclude, (list, tuple)):
        for ex in exclude:
            tag = tag.replace(ex, "")
    else:
        tag = tag.replace(exclude, "")
    return tag


def clean_el_repr(el, exclude="{"+SVG_NS+"}"):
    ''' Format an element or list of them to str neatly for messages.

    Convert the given element(s) into a neat string format, optionally
    removing specific substrings from the element tags to make messages
    clearer.

    :param el: The element or list of elements to convert.
    :type el: Element or list[Element]
    :param exclude: Substrings to exclude from the element tags. This
        can be a single string, a list of strings, or a tuple of
        strings.
    :type exclude: str | list[str] | tuple[str]
    :return: A string representation of the element or list of elements,
        with specified substrings excluded from the tags.
    :rtype: str
    '''
    if isinstance(el, list):
        new_list = []
        for sub in el:
            new_list.append(clean_el_repr(sub, exclude=exclude))
        return str(new_list)
    if not hasattr(el, "tag"):
        logger.warning(
            "{} does not have a tag."
            " Reverting to repr (should only affect log)."
            .format(emit_cast(el)))
        return repr(el)
    tag = el.tag
    if tag:
        tag = clean_tag_str(tag, exclude=exclude)
    text = el.text
    if text is None:
        text = ""
    return "<%s ...>%s</%s>" % (tag, text, tag)


def has_text(element, spacing: bool, recursive: bool = True):
    """ Check if element or any descendants has non-blank text.

    :param element: An lxml or xml Element object.
    :param spacing: If having only spaces is considered having text.
    :param recursive: If the descendants should be checked for the text.
    :return: True if the element or any descendant has non-blank text,
        False otherwise.
    """
    # Check if the element has non-blank text
    if element.text and (spacing or element.text.strip()):
        # ^ Must check element.text before access, since may be None!
        return True

    if not recursive:
        return False

    # Check if any descendant has non-blank text
    for text in element.itertext():
        if (spacing and text) or text.strip():
            return True
    return False


def used_elements(elements, spacing=False):
    '''Get elements with text.
    This is useful for when Inkscape generates multiple
    text fields and only one is actually used though
    others are non-blank. In that case, all should
    be cleared and the first should be set to the
    desired value (others may have transforms etc).
    '''
    if not isinstance(elements, (list, tuple)):
        raise TypeError("Expected list[Element], got {}"
                        .format(emit_cast(elements)))
    return [elem for elem in elements if has_text(elem, spacing)]


def used_element(elements, spacing=False, get_any_if_one=False):
    if get_any_if_one:
        if len(elements) == 1:
            return elements[0]
    used = used_elements(elements, spacing=spacing)
    if len(used) == 0:
        if get_any_if_one:
            logger.warning("All blank, returning first of {}"
                        .format(elements))
            return elements[0]
        return None
    elif len(used) == 1:
        return used[0]
    # elif len(used) > 1:
    logger.warning("multiple non-blank, returning first of: {}"
                   .format(used))
    return used[0]


def child_tags(el, tag: str) -> list:
    return [child for child in el if child.tag == tag]


def _get_leaf(el, tag: str, skip_empty=False, spacing=False,
              matching_ancestor=None):
    ''' See get_leaf for additional documentation.

    :param matching_ancestor: The most recent ancestor that matched the
        tag. Leave as None to detect (typical use).
    '''
    if el is None:
        raise ValueError("Expected Element, got None")

    if isinstance(el, (list, tuple, str)):
        raise TypeError(
            "Need a parent but got: {}"
            .format(emit_cast(el)))
    el_tag = None
    # Clean the element's tag for comparison
    if el.tag is not None:
        el_tag = clean_tag_str(el.tag)
        # Otherwise it will never match...
        #   the non-cleaned tag is something like
        #   {http://www.w3.org/2000/svg}g

    # Ensure the cleaned tag does not contain namespace braces
    if el_tag:
        assert "{" not in el_tag, "clean_tag_str didn't remove { in %s" % el_tag

    # Check if the current element's tag matches the desired tag
    if el_tag and (el_tag.lower() == tag.lower()):
        # Determine if the element should be considered based on text content
        if (not skip_empty and not child_tags(el, tag)) or has_text(el, spacing, recursive=False):
            # ^ The child_tags check avoids returning tspan that has no
            #   text but has tspan in it (same goes for tag other than
            #   tspan)
            matching_ancestor = el
    else:
        logger.debug("<{} ...> is not {}".format(el.tag, tag))

    # Recursively search through all children to find the most deeply nested match
    for child in el:
        result = _get_leaf(child, tag, skip_empty=skip_empty,
                           spacing=spacing,
                           matching_ancestor=matching_ancestor)
        if result is not None:  # may be falsey, so check vs None!
            return result

    # If no child matched, return the most recent matching ancestor
    return matching_ancestor


def get_leaf(el, tag: str, skip_empty=False, spacing=False):
    ''' Get element with tag that is a leaf or closest to a leaf.

    Recursively searches for the most deeply nested element where the 'tag'
    attribute matches the provided tag argument.

    :param tag: The tag (case-insensitive) to match against.
    :type tag: str
    :param el: The current XML element to search.
    :type el: Element
    :param skip_empty: Whether to ignore elements that do not contain text.
        Defaults to False.
    :type skip_empty: bool
    :param spacing: Treats text containing only spacing characters as non-empty.
        Defaults to False.
    :type spacing: bool
    :param matching_ancestor: The most recent ancestor that matched the tag.
        Leave as None to detect (typical use).
    :type matching_ancestor: Element or None
    :raises ValueError: If `el` is None.
    :raises TypeError: If `el` is a list or tuple instead of an element.
    :return: The most deeply nested element with a matching tag, or None.
    :rtype: Element or None
    '''
    return _get_leaf(el, tag, skip_empty=skip_empty, spacing=spacing)
