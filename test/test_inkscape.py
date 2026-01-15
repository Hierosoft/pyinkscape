#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# tests/test_getElementById.py

import unittest
from xml.etree import ElementTree as ET
from unittest.mock import patch

from pyinkscape.inkscape import Canvas
from pyinkscape.xmlnav import SVG_NS


# SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)


class TestCanvasGetElementById(unittest.TestCase):
    def _create_canvas_from_string(self, svg_string: str) -> Canvas:
        """Create Canvas from SVG string using in-memory mode."""
        canvas = Canvas(None)  # triggers FILEPATH_MEMORY path → loads blank template
        root = ET.fromstring(svg_string)
        # Replace the loaded tree with our test tree
        canvas._Canvas__tree = ET.ElementTree(root)
        canvas._Canvas__root = root
        # Clear any existing cache
        if hasattr(canvas, "_id_to_elements"):
            del canvas._id_to_elements
        return canvas

    def test_simple_path_by_id(self):
        svg = f'<svg xmlns="{SVG_NS}"><path id="category_symbol_2_weapon_1_"/></svg>'
        canvas = self._create_canvas_from_string(svg)
        elem = canvas.getElementById("category_symbol_2_weapon_1_")
        self.assertIsNotNone(elem)
        self.assertIn("path", elem.tag)

    def test_text_with_nested_tspan(self):
        svg = f'''
        <svg xmlns="{SVG_NS}">
          <text id="weapon_name_caption_4_">
            <tspan><tspan>Name</tspan></tspan>
          </text>
        </svg>
        '''
        canvas = self._create_canvas_from_string(svg)
        elem = canvas.getElementById("weapon_name_caption_4_")
        self.assertIsNotNone(elem)
        self.assertIn("text", elem.tag)

    def test_multiple_elements_same_id_returns_first(self):
        svg = f'''
        <svg xmlns="{SVG_NS}">
          <g id="dup"/>
          <rect id="dup"/>
        </svg>
        '''
        canvas = self._create_canvas_from_string(svg)
        elem = canvas.getElementById("dup")
        self.assertIn("g", elem.tag)  # first match

    def test_returns_none_when_not_found(self):
        svg = f'<svg xmlns="{SVG_NS}"/>'
        canvas = self._create_canvas_from_string(svg)
        self.assertIsNone(canvas.getElementById("missing"))

    def test_assert_id_in_raises(self):
        canvas = self._create_canvas_from_string(f'<svg xmlns="{SVG_NS}"><rect id="real"/></svg>')
        with self.assertRaises(AssertionError) as cm:
            canvas.getElementById("ghost", assert_id_in="test.svg")
        self.assertIn("ghost", str(cm.exception))
        self.assertIn("test.svg", str(cm.exception))

    @patch("pyinkscape.inkscape._LXML_AVAILABLE", True)
    def test_lxml_path_taken_when_available(self):
        svg = f'<svg xmlns="{SVG_NS}"><path id="lxml_test"/></svg>'
        canvas = self._create_canvas_from_string(svg)

        with patch.object(canvas, "_xpath_query") as mock_xpath:
            mock_xpath.return_value = [canvas._Canvas__root.find(".//{*}path")]
            result = canvas.getElementById("lxml_test")
            mock_xpath.assert_called_once_with(".//*[@id=$id]", {"id": "lxml_test"})
            self.assertIsNotNone(result)

    @patch("pyinkscape.inkscape._LXML_AVAILABLE", False)
    def test_cache_used_when_no_lxml(self):
        svg = f'<svg xmlns="{SVG_NS}"><circle id="pure_etree"/></svg>'
        canvas = self._create_canvas_from_string(svg)
        elem = canvas.getElementById("pure_etree")
        self.assertIsNotNone(elem)
        self.assertIn("circle", elem.tag)

    def test_skip_empty_calls_used_element(self):
        svg = f'''
        <svg xmlns="{SVG_NS}">
          <text id="mixed">
            <tspan>   </tspan>
            <tspan>Real</tspan>
          </text>
        </svg>
        '''
        canvas = self._create_canvas_from_string(svg)

        with patch("pyinkscape.inkscape.used_element") as mock_used:
            mock_used.return_value = "filtered"
            result = canvas.getElementById("mixed", skip_empty=True)
            mock_used.assert_called_once()
            self.assertEqual(result, "filtered")

    def test_cache_is_shared_and_not_rebuilt(self):
        svg = f'''
        <svg xmlns="{SVG_NS}">
          <path id="first"/>
          <path id="second"/>
        </svg>
        '''
        canvas = self._create_canvas_from_string(svg)

        # First call builds cache
        canvas.getElementById("first")

        # Second call must NOT call iter() again
        with patch.object(canvas._Canvas__tree, "iter") as mock_iter:
            canvas.getElementById("second")
            mock_iter.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)