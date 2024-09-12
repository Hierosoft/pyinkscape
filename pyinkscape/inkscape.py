#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Helper functions to manipulate Inkscape SVG content

Latest version can be found at https://github.com/letuananh/pyinkscape

@author: Le Tuan Anh <tuananh.ke@gmail.com>
@license: MIT
'''

# Copyright (c) 2017, Le Tuan Anh <tuananh.ke@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

########################################################################

import logging
import math
import os
import sys
import warnings

from pathlib import Path
try:
    from lxml import etree
    from lxml.etree import XMLParser
    _LXML_AVAILABLE = True
except ImportError:
    # logging.getLogger(__name__).debug("lxml is not available, fall back to xml.etree.ElementTree")
    from xml.etree import ElementTree as etree
    from xml.etree.ElementTree import XMLParser
    _LXML_AVAILABLE = False
try:
    from chirptext.anhxa import IDGenerator  # type:ignore
    from chirptext.cli import setup_logging  # type:ignore
    _CHIRPTEXT_AVAILABLE = True
except ImportError:
    _CHIRPTEXT_AVAILABLE = False
    # When chirptext is not available, fall back to built-in IDGenerator
    # IDGenerator class is adopted from:
    # https://github.com/letuananh/chirptext/blob/master/chirptext/anhxa.py
    import threading
    class IDGenerator(object):

        def __init__(self, id_seed=1, id_hook=None):
            ''' id_seed = starting number '''
            self.__id_seed = id_seed
            self.__id_check_hook = id_hook  # external ID checker
            self.__lock = threading.Lock()

        def __next__(self):
            with self.__lock:
                while True:
                    valid_id = self.__id_seed
                    self.__id_seed += 1
                    if self.__id_check_hook is None or not self.__id_check_hook(valid_id):
                        break
                return valid_id

from pyinkscape.xmlnav import (
    clean_el_repr,
    used_element,
    get_leaf,
    used_elements,
    SVG_NS,
)

_MY_DIR = Path(os.path.dirname(os.path.realpath(__file__)))

_BLANK_CANVAS = _MY_DIR / 'data' / 'blank.svg'

# ------------------------------------------------------------------------------
# use chirptext setup_logging if possible
try:
    setup_logging('logging.json', 'logs')
except Exception:
    pass
# -------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------

logger = logging.getLogger(__name__)


def el_repr(el):
    ''' Convert SVG element to str such as for display in logs '''
    return clean_el_repr(el, exclude="{" + SVG_NS + "}")


class Style:
    def __init__(self, **kwargs):
        self.attributes = {}
        self.attributes.update(kwargs)

    # alias of attributes
    @property
    def attrs(self):
        return self.attributes

    def __str__(self):
        return ";".join("{}:{}".format(k.replace('_', '-'), v) for k, v in self.attributes.items())

    def clone(self, **kwargs):
        s = Style(**self.attributes)
        s.attributes.update(kwargs)
        return s


INKSCAPE_NS = 'http://www.inkscape.org/namespaces/inkscape'
SVG_NAMESPACES = {'ns': SVG_NS,
          'svg': SVG_NS,
          'dc': "http://purl.org/dc/elements/1.1/",
          'cc': "http://creativecommons.org/ns#",
          'rdf': "http://www.w3.org/1999/02/22-rdf-syntax-ns#",

          "sodipodi": "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd",
          'inkscape': INKSCAPE_NS}
DEFAULT_LINESTYLE = Style(display='inline', fill='none', stroke_width='0.86458332px', stroke_linecap='butt', stroke_linejoin='miter', stroke_opacity='1', stroke='#FF0000')
STYLE_FPNAME = Style(font_size='20px', font_family='sans-serif', font_style='normal', font_weight='normal', line_height='1.25', letter_spacing='0px', word_spacing='0px', fill='#000000', fill_opacity='1', stroke='none')
BLIND_COLORS = ("#999999", "#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7")
__idgen = IDGenerator()


def new_id(prefix=None):
    if not prefix:
        prefix = '_pyinkscape_'
    return '{prefix}_{id}'.format(prefix=prefix, id=next(__idgen))


class Point:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def __repr__(self):
        return str(self)

    def __str__(self):
        return f"Point(x={self.x}, y={self.y})"

    def __eq__(self, other):
        if not isinstance(other, Point):
            return NotImplemented
        return self.x == other.x and self.y == other.y

    def __add__(self, other):
        if isinstance(other, Point):
            return Point(self.x + other.x, self.y + other.y)
        if isinstance(other, Dimension):
            return Point(self.x + other.width, self.y + other.height)
        else:
            return Point(self.x + other, self.y + other)

    def __sub__(self, other):
        if isinstance(other, Point):
            return Point(self.x - other.x, self.y - other.y)
        if isinstance(other, Dimension):
            return Point(self.x - other.width, self.y - other.height)
        else:
            return Point(self.x - other, self.y - other)

    def __mul__(self, other):
        if isinstance(other, Point):
            return Point(self.x * other.x, self.y * other.y)
        if isinstance(other, Dimension):
            return Point(self.x * other.width, self.y * other.height)
        else:
            return Point(self.x * other, self.y * other)

    def __div__(self, other):
        if isinstance(other, Point):
            return Point(self.x / other.x, self.y / other.y)
        if isinstance(other, Dimension):
            return Point(self.x / other.width, self.y / other.height)
        else:
            return Point(self.x / other, self.y / other)

    @staticmethod
    def rotate_percent(point, center, percent):
        degrees = percent * 3.6
        logger.debug(f"Percent: {percent} - Degrees: {degrees}")
        return Point.rotate(point, center, degrees)

    @staticmethod
    def ensure(p):
        if isinstance(p, Point):
            return p
        else:
            return Point(*p)

    @staticmethod
    def rotate(point, center, theta: float):
        ''' Rotate a `point` around a `center` point by `theta` degrees

        :param point: The point to rotate
        :param center: The center point of the rotation
        :param theta: Rotating angle, in degrees
        '''
        point = Point.ensure(point)
        center = Point.ensure(center)
        t_rad = math.radians(theta)
        n_x = point.x - center.x  # shift center point to (0, 0)
        n_y = point.y - center.y
        logger.debug(f"shifted = ({n_x}, {n_y}) - theta (in radians) = {t_rad}")
        r_x = n_x * math.cos(t_rad) - n_y * math.sin(t_rad)  # rotation matrix
        r_y = n_x * math.sin(t_rad) + n_y * math.cos(t_rad)
        logger.debug(f"new point = ({r_x + center.x}, {r_y + center.y})")
        return Point(r_x + center.x, r_y + center.y)  # shift it back


class Dimension:
    def __init__(self, width, height):
        self.width = width
        self.height = height

    def ensure(p):
        if isinstance(p, Dimension):
            return p
        else:
            return Dimension(*p)


class BBox():
    ''' A bounding box represents by a top-left anchor (x1, y1) and a dimension (width, height) '''

    def __init__(self, x, y, width, height):
        self.__anchor = Point(x, y)
        self.__dimension = Dimension(width, height)

    @property
    def x1(self):
        ''' x value of the top-left anchor '''
        return self.__anchor.x

    @property
    def y1(self):
        ''' y value of the top-left anchor '''
        return self.__anchor.y

    @property
    def width(self):
        ''' Width of the bounding box '''
        return self.__dimension.width

    @property
    def height(self):
        ''' Height of the bounding box '''
        return self.__dimension.height

    @property
    def x2(self):
        return self.__anchor.x + self.__dimension.width

    @property
    def y2(self):
        return self.__anchor.y + self.__dimension.height

    def to_tuple(self) -> tuple:
        return (self.x1, self.y1, self.width, self.height)

    def __str__(self):
        return f"{self.x1} {self.y1} {self.width} {self.height}"


class Group:

    ''' Represents either a group (composite object) or a layer (special group) '''

    def __init__(self, elem, parent_elem):
        self.elem = elem
        self.parent_elem = parent_elem
        self.ID = elem.get('id')
        self.tag = elem.tag
        self.label = elem.get('{http://www.inkscape.org/namespaces/inkscape}label')

    def delete(self):
        ''' Remove this group/layer from a canvas '''
        self.parent_elem.remove(self.elem)
        # self.elem.getparent().remove(self.elem)

    def paths(self):
        paths = self.elem.xpath('//ns:path', namespaces=SVG_NAMESPACES)
        return [Path(p) for p in paths]

    def new(self, tag_name, id=None, style=None, id_prefix=None, **kwargs):
        e = etree.SubElement(self.elem, tag_name)
        if not id:
            id = new_id(prefix=id_prefix)
        e.set('id', id)
        if style:
            e.set('style', str(style))
        for k, v in kwargs.items():
            e.set(str(k), str(v))
        return e

    def line(self, from_point, to_point, style: Style=DEFAULT_LINESTYLE, id_prefix='__pyinkscape_line', **kwargs):
        ''' Draw a new line between two points using a style

        :param style: A `Style` object
        :type style: pyinkscape.inkscape.Style
        '''
        from_point = Point.ensure(from_point)
        to_point = Point.ensure(to_point)
        return self.new("line",
                        x1=from_point.x, y1=from_point.y,
                        x2=to_point.x, y2=to_point.y,
                        style=style, id_prefix=id_prefix,
                        **kwargs)

    def rect(self, topleft, size, style=DEFAULT_LINESTYLE, id_prefix='__pyinkscape_rect', **kwargs):
        topleft = Point.ensure(topleft)
        size = Dimension.ensure(size)
        return self.new("rect", x=topleft.x, y=topleft.y, width=size.width, height=size.height, style=style, id_prefix=id_prefix, **kwargs)

    def path(self, path_code, id=None, style=DEFAULT_LINESTYLE, id_prefix='__pyinkscape_path', **kwargs):
        p = self.new("path", style=style, id_prefix=id_prefix, **kwargs)
        p.set('d', path_code)
        p.set('{http://www.inkscape.org/namespaces/inkscape}connector-curvature', "0")
        return Path(p)

    def circle(self, center, r, style=DEFAULT_LINESTYLE, id_prefix='__pyinkscape_circle', **kwargs):
        center = Point.ensure(center)
        c = self.new("circle", style=style, id_prefix=id_prefix, **kwargs)
        c.set('cx', str(center.x))
        c.set('cy', str(center.y))
        c.set('r', str(r))
        return Circle(c)

    def text(self, text, center, width='', height='', font_size='18px', font_family="sans-serif", fill="black", text_anchor='middle', style=STYLE_FPNAME, id_prefix='__pyinkscape_text', **kwargs):
        txt = self.new('text', id_prefix=id_prefix)
        center = Point.ensure(center)
        txt.set('x', str(center.x))
        txt.set('y', str(center.y))
        txt.set('font-size', font_size)
        txt.set('font-family', font_family)
        txt.set('fill', fill)
        txt.set('text-anchor', text_anchor)
        if style:
            txt.set('style', str(style))
        for k, v in kwargs.items():
            txt.set(k, str(v))
        txt.text = text
        return Text(txt)


class Shape:
    def __init__(self, elem):
        self.elem = elem
        self.ID = elem.get('id')
        self.label = elem.get('label')


class Text(Shape):
    pass


class Circle(Shape):
    pass


class Path(Shape):
    pass


class Canvas:

    ''' This class represents an Inkscape drawing page (i.e. a SVG file) '''

    FILEPATH_MEMORY = ':memory:'

    def __init__(self, filepath: str = FILEPATH_MEMORY, *args, **kwargs):
        ''' Create a new blank canvas or read from an existing file.

        To create a blank canvas, just ignore the filepath property.
        >>> c = Canvas()

        To open an existing file, use
        >>> c = Canvas("/path/to/file.svg")

        :param filepath: Path to an existing SVG file.
        '''
        if not filepath:
            warnings.warn(
                "filepath was explicitly set to {} instead of the default"
                .format(filepath))

        self.__filepath = filepath
        self.__tree = None
        self.__root = None
        self.__units = 'mm'
        self.__width = 0
        self.__height = 0
        self.__viewbox = None
        self.__scale = 1.0
        self.__elem_group_map = dict()
        if len(args) > 0:
            # warn so the args don't get lost silently!
            warnings.warn(
                "Extra arguments detected: {}."
                " Maybe you meant filepath=\"{}\""
                .format(args, args[0])
            )
        if filepath is not None:
            self.__load_file(*args, **kwargs)

    def __load_file(self, remove_blank_text=True, encoding="utf-8", **kwargs):
        with open(_BLANK_CANVAS if self.__filepath == Canvas.FILEPATH_MEMORY else self.__filepath, encoding=encoding) as infile:
            if _LXML_AVAILABLE:
                kwargs['remove_blank_text'] = remove_blank_text  # this flag is lxml specific
            parser = XMLParser(**kwargs)
            if not _LXML_AVAILABLE:
                for k, v in SVG_NAMESPACES.items():
                    etree.register_namespace(k, v)
                # register SVG as the default namespace
                etree.register_namespace('', SVG_NS)
            self.__tree = etree.parse(infile, parser)
            self.__root = self.__tree.getroot()
            self.__update_vsg_info()

    def __update_vsg_info(self):
        # load SVG information
        if self.__svg_node.get('width'):
            self.__units = self.__svg_node.get('width')[-2:]
            self.__width = float(self.__svg_node.get('width')[:-2])
        if self.__svg_node.get('height'):
            self.__height = float(self.__svg_node.get('height')[:-2])
        if self.__svg_node.get('viewBox'):
            self.__viewbox = BBox(*(float(x) for x in self.__svg_node.get('viewBox').split()))
            if not self.__width:
                self.__width = self.__viewbox.width
            if not self.__height:
                self.__width = self.__viewbox.height
        if self.viewBox and self.__width:
            self.__scale = self.viewBox.width / self.__width

    def __parent_map(self):
        return {c: p for p in self.__tree.iter() for c in p}

    def __build_group(self, elem):
        if elem not in self.__elem_group_map:
            if _LXML_AVAILABLE:
                _group_obj = Group(elem, elem.getparent())
            else:
                _group_obj = Group(elem, self.__parent_map()[elem])
            self.__elem_group_map[elem] = _group_obj
        return self.__elem_group_map[elem]

    @property
    def __svg_node(self):
        return self.__root

    @property
    def units(self):
        return self.__units

    @property
    def width(self):
        return self.__width

    @property
    def height(self):
        return self.__height

    @property
    def scale(self):
        return self.__scale

    @property
    def viewBox(self):
        return self.__viewbox

    @property
    def version(self):
        return self.__svg_node.get('version')

    @property
    def inkscape_version(self):
        return self.__svg_node.get('{http://www.inkscape.org/namespaces/inkscape}version')

    @property
    def docname(self):
        return self.__svg_node.get('{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}docname')

    @docname.setter
    def docname(self, value):
        return self.__svg_node.set('{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}docname', value)

    @staticmethod
    def load(filepath, encoding="utf-8", remove_blank_text=True, **kwargs):
        warnings.warn("load() is deprecated and will be removed in near future, use Canvas constructor instead.", DeprecationWarning, stacklevel=2)
        return Canvas(filepath=filepath, encoding=encoding, remove_blank_text=remove_blank_text, **kwargs)

    def to_xml_string(self, encoding: str = "utf-8",
                      pretty_print: bool = False, **kwargs) -> str:
        ''' Convert the XML tree to a string representation.

        Typically this is accessed via str(self) (Python uses the
        __str__ dunder method since defined in this class) which is
        called by render.

        :param encoding: The encoding format to use (defaults to
            "utf-8").
        :param pretty_print: Whether to pretty-print the XML. If True,
            text would get mangled by extra newlines (Issue #3), due to
            having newlines and indents for the tspan tags which
            function like HTML span tags in Inkscape! Therefore,
            generally do not use True (defaults to `False`).
        :param kwargs: Additional keyword arguments to pass to
            `etree.tostring`.
        :return: Inkscape-style XML representing the Canvas (entire
            Inkscape document).
        '''

        if _LXML_AVAILABLE:
            return etree.tostring(self.__root, encoding=encoding, pretty_print=pretty_print, **kwargs).decode('utf-8')
        else:
            return etree.tostring(self.__root, encoding=encoding, **kwargs).decode('utf-8')

    def __str__(self):
        return self.to_xml_string()

    def _xpath_query(self, query_string, namespaces=None):
        if _LXML_AVAILABLE:
            return self.__root.xpath(query_string, namespaces=namespaces)
        else:
            logger.info(
                "[_xpath_query] xml query_string={}"
                .format(repr(query_string)))
            return self.__tree.findall(query_string, namespaces=namespaces)

    def groups(self, layer_only=False):
        if layer_only:
            groups = self._xpath_query(".//ns:g[@inkscape:groupmode='layer']", namespaces=SVG_NAMESPACES)
        else:
            groups = self._xpath_query(".//ns:g", namespaces=SVG_NAMESPACES)
        return [self.__build_group(g) for g in groups]

    def group(self, name, layer_only=False):
        if layer_only:
            if _LXML_AVAILABLE:
                groups = self._xpath_query(f".//ns:g[@inkscape:groupmode='layer' and @inkscape:label='{name}']", namespaces=SVG_NAMESPACES)
            else:
                groups = self._xpath_query(f".//ns:g[@inkscape:groupmode='layer'][@inkscape:label='{name}']", namespaces=SVG_NAMESPACES)
        else:
            groups = self._xpath_query(f".//ns:g[@inkscape:label='{name}']", namespaces=SVG_NAMESPACES)
        if groups:
            return self.__build_group(groups[0])
        else:
            # some groups in Inkscape have empty name and use ID as name instead
            _try_group = self.group_by_id(name, layer_only=layer_only)
            if _try_group and not _try_group.label:
                return _try_group
            else:
                return None

    def group_by_id(self, id, layer_only=False):
        if layer_only:
            if _LXML_AVAILABLE:
                groups = self._xpath_query(f".//ns:g[@inkscape:groupmode='layer' and @id='{id}']", namespaces=SVG_NAMESPACES)
            else:
                groups = self._xpath_query(f".//ns:g[@inkscape:groupmode='layer'][@id='{id}']", namespaces=SVG_NAMESPACES)
        else:
            groups = self._xpath_query(f".//ns:g[@id='{id}']", namespaces=SVG_NAMESPACES)
        return self.__build_group(groups[0]) if groups else None

    def layers(self):
        ''' Get all available layers in this canvas '''
        return self.groups(layer_only=True)

    def layer(self, name: str) -> Group:
        ''' Find the first layer with a name

        Layer names are not unique. If there are multiple layers with the same name, only the first one will be returned

        :param name: Name of the layer to search (Note: Layer names a not unique)
        :returns: A `Group` object if found, or None
        :rtype: pyinkscape.inkscape.Group
        '''
        return self.group(name, layer_only=True)

    def layer_by_id(self, id):
        ''' Find the first layer with an ID

        Layer IDs are unique

        :param id: ID of the layer to search
        :returns: A `Group` object if found, or None
        :rtype: pyinkscape.inkscape.Group
        '''
        return self.group_by_id(id=id, layer_only=True)

    def render(self, outpath, overwrite=False, encoding="utf-8"):
        if not overwrite and os.path.isfile(outpath):
            logger.warning(f"File {outpath} exists. SKIPPED")
            return False
        output = str(self)
        with open(outpath, mode='w', encoding=encoding) as outfile:
            outfile.write(output)
            logger.info("Written output to {}".format(outfile.name))
            return True

    def getElementsByTagName(self, tag: str, skip_empty: bool = False,
                             spacing: bool = False,
                             assert_id_in: str = None):
        elems = self._xpath_query(".//ns:{tag}".format(tag=tag),
                                  namespaces=SVG_NAMESPACES)
        if not elems:
            if assert_id_in:
                raise AssertionError("<{} ... > was not found in {}"
                                     .format(tag, repr(assert_id_in)))
            return None
        if skip_empty:
            return used_elements(elems, spacing=spacing)
        return elems

    def getElementById(self, id: str, skip_empty: bool = False,
                       assert_id_in: str = None):
        elems = self._xpath_query(".//*[@id='{id}']".format(id=id), namespaces=SVG_NAMESPACES)
        if not elems:
            if assert_id_in:
                raise AssertionError("id {} was not found in {}"
                                     .format(id, repr(assert_id_in)))
            return None
        if skip_empty:
            return used_element(elems)
        return elems[0]

    def getLeafById(self, tag, id, skip_empty: bool = False,
                    spacing: bool = False,
                    assert_id_in: str = None):
        el = self.getElementById(id, skip_empty=skip_empty)
        # NOTE: even if found, may not be truthy, so always check
        #   against None
        if el is None:
            if assert_id_in:
                raise AssertionError(
                    "id {} was not found in {}"
                    .format(id, repr(assert_id_in)))
            return None
        return get_leaf(el, tag, skip_empty=skip_empty, spacing=spacing)

    def getLeavesById(self, id: str, tag: str, leaf_tag: str,
                      skip_empty: bool = True,
                      spacing: bool = True) -> list:
        ''' Get leaves such as `tspan` by id of ancestor.

        This method is useful when Inkscape generates multiple groups
        and/or multiple `text` tags when only a single text field is
        apparent to the user.

        If you are trying to fill the field and more than one element is
        returned, set the text of all but the first to an empty string
        (`""`) to avoid artifacts (e.g., weird upside-down copies,
        etc.). For more details, see issue #3. The setField method
        should call this to avoid the issue.

        :param id: The id of the container or the group of containers.
        :param tag: The container tag, such as `g` or `text`.
        :param leaf_tag: The leaf tag, such as `tspan`.
        :param skip_empty: Whether to return only elements that
            contain text. This should be set to `False` to avoid issue
            #3 (Inkscape creates nested groups and multiple transformed
            copies for a simple text box). Defaults to `False`.
        :param spacing: Whether elements containing only spacing
            characters are considered non-empty for skip_empty.
            Not used if not skip_empty. Defaults to True.
        :return: A list of elements matching the specified criteria. If
            setting text, clear text on all but the first element.
        :rtype: list[Element]
        '''
        query_str = (".//svg:{}[@id='{}']/svg:{}"
                     .format(tag, id, leaf_tag)
        )
        elements = self._xpath_query(query_str, namespaces=SVG_NAMESPACES)
        # NOTE: Inkscape usually puts many junk empty tspan tags in
        #   each text tag, but get all of them and if one is non-empty
        #   choose that one since that is probably the formatted one
        #   (user should put "_" or something in there to identify
        #   the correct one if attempting to use a form filler
        #   that uses this code).
        if elements:
            # return [best_field_element(elements, id=id,
            #                            tag=tag, leaf_tag=leaf_tag)]
            if skip_empty:
                return used_elements(elements, spacing=spacing)
            else:
                return elements
        query_str = (".//svg:g[@id='{}']//svg:{}"
                     .format(id, leaf_tag)
        )
        # ^ such as ".//svg:g[@id='armor_class_']//svg:tspan"
        # logger.warning("trying {}".format(repr(query_str)))
        elements = self._xpath_query(query_str, namespaces=SVG_NAMESPACES)
        if elements:
            logger.warning(
                f"Found <g id=\"{id}\"...>:"
                f" speculated since no <{tag} id=\"{id}\"...>")
            if skip_empty:
                return used_elements(elements, spacing=spacing)
            else:
                return elements
        logger.warning(
            f"Missing <{tag} id=\"{id}\" Also tried <g id=\"{id}\"...>:"
            f" ...>")
        return None

    def getField(self, id: str):
        ''' Set an Inkscape text field's content.
        Any tag (including typical `g` or `text`) are checked for the
        id, then first deepest tspan's text is returned (See setField
        for details).
        '''
        el = self.getElementById(id)
        if el is None:
            return None
        leaf = get_leaf(el, "tspan", skip_empty=False)
        if leaf is not None:
            return leaf.text
        return None

    def setField(self, id: str, value, skip_empty: bool=False,
                 spacing: bool=False) -> bool:
        ''' Set an Inkscape text field's content.
        Assuming typical SVG `<ANY id="ID"><tspan>VALUE` where ANY is
        usually `g` or `text` (or both nested), set the tspan's content.
        Clear content of extra tspan tags to avoid corruption
        (See skip_empty and issue #3). This doesn't occur with Inkscape
        1.2 (at least after initially setting id of a text field--text
        gets the id), but this method should maintain compatibility with
        older InkScape SVG files.

        :param id: The id of the text field or group containing it (The
            text tag must contain a tspan or nested tspan in tspan, as
            is expected in an InkScape SVG).
        :param value: The value to set (will be converted to str).
        :param skip_empty: Whether to return only elements that
            contain text. This should be set to `False` to avoid issue
            #3 (Inkscape creates nested groups and multiple transformed
            copies for a simple text box). Defaults to `False`.
        :param spacing: Whether elements containing only spacing
            characters are considered non-empty for skip_empty
            (allows user to create a form where only spacing characters
            are in the empty form field). If not skip_empty, this has no
            effect. Defaults to True.
        :return: Whether any matching field was found and set.
        '''
        leaves = self.getLeavesById(id, "text", "tspan", skip_empty=skip_empty,
                                    spacing=spacing)
        new_value = str(value)  # Must be str, or can't be serialized! (or
        #   lxml has "TypeError: Argument must be bytes or unicode, got 'int'"
        #   and xml has "TypeError: cannot serialize 17 (type int)")
        if len(leaves) > 0:
            for leaf in leaves:
                leaf.text = new_value
                new_value = ""  # erase remaining extra transformed copies
                #  that Inkscape may generate (See issue 3)
            return True
        el = self.getElementById(id)
        if el is not None:
            leaf = get_leaf(el, "tspan", skip_empty=skip_empty,
                            spacing=spacing)
            if leaf is not None:
                leaf.text = new_value
                return True
        print(
            f"Warning: Canvas filepath=\"{self.__filepath}\""
            f" does not contain id {id}."
            f" Cannot set {id}='{new_value}' in the file.",
            file=sys.stderr)
        return False

    def getText(self, id):
        ''' Get flowRoot or text elements with matching id. '''
        elems = self._xpath_query(
            ".//ns:flowRoot[@id='{id}']/ns:flowPara"
            .format(id=id), namespaces=SVG_NAMESPACES)
        if elems:
            return elems
        # try get <text> element instead of flowRoot ...
        elems = self._xpath_query(
            ".//ns:text[@id='{id}']/ns:tspan"
            .format(id=id), namespaces=SVG_NAMESPACES)
        logger.debug(f"Found: {elems}")
        return elems
