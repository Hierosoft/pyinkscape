#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
Test script for pyInkscape
Latest version can be found at https://github.com/letuananh/pyinkscape

:copyright: (c) 2021 Le Tuan Anh <tuananh.ke@gmail.com>
:license: MIT, see LICENSE for more details.
'''

import logging
import os
import sys
import unittest
# import warnings

from pathlib import Path

TEST_DIR = Path(os.path.dirname(os.path.realpath(__file__)))

if __name__ == "__main__":
    REPO_DIR = os.path.dirname(TEST_DIR)
    sys.path.insert(0, REPO_DIR)

from pyinkscape import (  # noqa: E402
    Canvas,
)

from pyinkscape.inkscape import (  # noqa: E402
    el_repr,
)

from pyinkscape.xmlnav import (  # noqa: E402
    # used_element,
    get_leaf,
    # used_elements,
)


# -------------------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------------------

TEST_DATA_DIR = TEST_DIR / 'data'
TEST_CANVAS = TEST_DATA_DIR / 'canvas-0.92.4.svg'
TEST_GRAPHIC = TEST_DATA_DIR / 'graphic.svg'
FILLABLE_SHEET = TEST_DATA_DIR / 'fillable_sheet.svg'
FILLED_SHEET = TEST_DATA_DIR / 'fillable_sheet-FILLED.svg'  # temp file
MARKED_SHEET = TEST_DATA_DIR / 'id_finding_test-MARKED.svg'
# - Ran https://xml-beautify.com on FILLABLE_SHEET
#   (and manually reordered svg tag properties),
#   so spacing matches FILLED_SHEET for easier comparison
#   (formatting occurs during render, ends up that way)

logger = logging.getLogger(__name__)
# ------------------------------------------------------------------------------
# Test cases
# ------------------------------------------------------------------------------

class TestTemplate(unittest.TestCase):

    def test_load_inkscape_file(self):
        t = Canvas(TEST_CANVAS)
        self.assertTrue(t)

    def test_new_blank_template(self):
        t = Canvas()
        self.assertTrue(t)

    def test_empty_template(self):
        t = Canvas(filepath=None)
        self.assertTrue(t)

    def test_static_load_function(self):
        with self.assertWarnsRegex(
                DeprecationWarning,
                r'load\(\) is deprecated [a-z ]+, use Canvas constructor instead\.') as cm:
            _ = Canvas.load(TEST_CANVAS)

    def test_read_svg_properties(self):
        t = Canvas()
        # test reading size info
        _properties = (t.width, t.height, t.units, t.viewBox.to_tuple(), t.scale)
        _expected = (210.0, 297.0, 'mm', (0.0, 0.0, 840.0, 1188.0), 4.0)
        self.assertEqual(_properties, _expected)
        # test reading version info
        self.assertEqual((t.version, t.inkscape_version), ('1.1', '1.0.1 (3bc2e813f5, 2020-09-07)'))
        # assert that 'new.svg' is in the generated SVG code
        # test docname (by default, docname is 'blank.svg')
        self.assertEqual(t.docname, 'blank.svg')
        t.docname = 'new.svg'
        self.assertEqual(t.docname, 'new.svg')
        self.assertIn('sodipodi:docname="new.svg"', str(t))


class TestSelectingObject(unittest.TestCase):

    def test_layer_search(self):
        c = Canvas()
        layers = c.layers()
        self.assertEqual(len(layers), 1)
        _ = layers[0]  # the first layer
        l1 = c.layer('Layer 1')
        self.assertIsNotNone(l1)
        l2 = c.layer_by_id('layer1')
        self.assertIsNotNone(l2)
        self.assertEqual(l1, l2)  # same object
        self.assertEqual((l1.ID, l1.label, l1.elem), (l2.ID, l2.label, l2.elem))

    def test_group_search(self):
        c = Canvas(TEST_GRAPHIC)
        groups = c.groups()
        self.assertEqual(len(groups), 6)
        _expected_groups = {('complex shape 2', 'g886'), ('Layer 2', 'layer2'),
                            (None, 'g855'), ('Layer 1', 'layerManual'),
                            (None, 'g841'), ('complex shape 1', 'g837')}
        self.assertEqual({(x.label, x.ID) for x in groups}, _expected_groups)
        g1a = c.group('Layer 1')
        self.assertEqual(g1a.label, 'Layer 1')
        g1b = c.group('Layer 1', layer_only=True)
        self.assertEqual(g1b.label, 'Layer 1')
        # look for a group that is layer by ID
        g2a = c.group_by_id("layer2")
        self.assertIsNotNone(g2a)
        g2b = c.group_by_id("layer2", layer_only=True)
        self.assertIsNotNone(g2b)
        # look for a group without a label (i.e. label is implied by ID)
        g3a = c.group('g855')
        self.assertIsNotNone(g3a)
        self.assertIsNone(g3a.label)


class TestSVGAddElements(unittest.TestCase):

    def test_draw(self):
        c = Canvas()
        l0 = c.layers()[0]
        l0.text("Hello World", (50, 50))
        l0.circle((50, 50), 100)
        _xml_code = str(c)
        self.assertIn("__pyinkscape_text_", _xml_code)
        self.assertIn("__pyinkscape_circle_", _xml_code)

    def test_remove_group(self):
        c = Canvas()
        l1 = c.layer('Layer 1')
        o = l1.elem.find('..')


class TestSVGReading(unittest.TestCase):
    def test_get_leaf(self):
        doc_path = MARKED_SHEET
        doc_name = os.path.basename(doc_path)
        self.assertTrue(os.path.isfile(doc_path))
        canvas = Canvas(filepath=doc_path)
        el = canvas.getElementById("armor_class_", skip_empty=False,
                                   assert_id_in=doc_name)
        self.assertIsNotNone(el)
        self.assertNotIsInstance(el, list)

        leaf = get_leaf(el, "tspan", skip_empty=False)
        self.assertIsNotNone(leaf)
        self.assertNotIsInstance(leaf, list)
        # skip_empty=False allows blanks and a blank is
        #   first child of armor_class_ in this file, so:
        self.assertIn(leaf.text, {None, ""})

        leaf = get_leaf(el, "tspan", skip_empty=True)
        self.assertIsNotNone(leaf)
        self.assertNotIsInstance(leaf, list)
        self.assertEqual(leaf.text, "B",
                         "Expected the tspan with text \"B\" but got blank {}"
                         .format(el_repr(leaf)))

    def test_getLeafById(self):
        self.assertTrue(os.path.isfile(MARKED_SHEET))
        canvas = Canvas(filepath=MARKED_SHEET)

        leaf = canvas.getLeafById("tspan", "armor_class_", skip_empty=False,
                                  assert_id_in=MARKED_SHEET)
        self.assertIsNotNone(leaf)
        self.assertNotIsInstance(leaf, list)
        self.assertIn(leaf.text, {None, ""})

        # skip_empty=False allows blanks and a blank is
        #   first child of armor_class_ in this file, so
        #   see test_getLeafById_placeholder for a
        #   complete test.

    def test_getLeafById_placeholder(self):
        self.assertTrue(os.path.isfile(MARKED_SHEET))
        canvas = Canvas(filepath=MARKED_SHEET)
        _id = "armor_class_"
        leaf = canvas.getLeafById("tspan", _id, skip_empty=True,
                                  assert_id_in=MARKED_SHEET)
        self.assertIsNotNone(leaf)
        self.assertNotIsInstance(leaf, list)
        self.assertEqual(leaf.text, "B",
                         "text of {} {} is {} not B"
                         .format(leaf.tag, _id, leaf.text))

    def test_getElementById(self):
        doc_path = MARKED_SHEET
        doc_name = os.path.basename(doc_path)
        self.assertTrue(os.path.isfile(doc_path))
        canvas = Canvas(filepath=doc_path)
        el = canvas.getElementById("armor_class_", skip_empty=False,
                                   assert_id_in=doc_name)
        self.assertIsNotNone(el)
        self.assertNotIsInstance(el, list)



class TestSVGEditing(unittest.TestCase):
    def test_svg_editing(self):
        self.assertTrue(os.path.isfile(FILLABLE_SHEET))
        canvas = Canvas(filepath=FILLABLE_SHEET)
        data = {
            "armor_class_": 17,
            "character_name_": "John Smith",
        }
        for field, value in data.items():
            leaves = canvas.getLeavesById(field, "text", "tspan",
                                          skip_empty=False)
            self.assertTrue(leaves)
            text = str(value)
            for leaf in leaves:
                if leaf.text:
                    leaf.text = text
                    text = ""  # Make the rest blank to avoid showing strange transformed
                    #  sibling groups generated by Inkscape (Issue #3)
                    # else blank version (Inkscape generates these for
                    # some reason)
        if os.path.isfile(FILLED_SHEET):
            os.remove(FILLED_SHEET)
        canvas.render(outpath=FILLED_SHEET)
        self.assertTrue(os.path.isfile(FILLED_SHEET))
        del canvas  # Make sure the old version doesn't pollute the test
        filled = Canvas(filepath=FILLED_SHEET)
        for field, value in data.items():
            # Get leaf, since user probably set id using group since
            #   Inkscape makes n-deep groups automatically :(
            leaves = filled.getLeavesById(field, "text", "tspan", skip_empty=False)
            self.assertTrue(leaves)
            text = str(value)
            for leaf in leaves:
                if leaf.text:
                    self.assertEqual(leaf.text, text)
                    text = ""  # See comment on `text = ""` above



# -------------------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------------------

if __name__ == "__main__":
    # sys.exit(unittest.main())

    # If Visual Studio Code doesn't go to the line number when traceback
    #   line is clicked :/ try:

    # For quickly getting a traceback for the first test that fails:
    test = TestSVGReading()
    test.setUp()
    for sub in dir(test):
        if sub.startswith("test"):
            getattr(test, sub)()
