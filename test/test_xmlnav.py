import os
import sys
import tempfile
import unittest

import xml.etree.ElementTree as ET

try:
    from lxml import etree
    from lxml.etree import XMLParser
    _LXML_AVAILABLE = True
except ImportError:
    # logging.getLogger(__name__).debug("lxml is not available, fall back to xml.etree.ElementTree")
    from xml.etree import ElementTree as etree
    from xml.etree.ElementTree import XMLParser
    _LXML_AVAILABLE = False


from pathlib import Path

TEST_DIR = Path(os.path.dirname(os.path.realpath(__file__)))

if __name__ == "__main__":
    REPO_DIR = os.path.dirname(TEST_DIR)
    sys.path.insert(0, REPO_DIR)

from pyinkscape import (
    Canvas,
    # el_repr,
)

from pyinkscape.xmlnav import (
    used_element,
    get_leaf,
    used_elements,
    has_text,
    child_tags,
)


class TestSVGReading(unittest.TestCase):
    def setUp(self):
        # Sample SVG elements for testing
        self.elem_with_text = etree.Element("test")
        self.elem_with_text.text = "Sample text"

        self.elem_with_blank_text = etree.Element("test")
        self.elem_with_blank_text.text = "   "

        self.elem_with_no_text = etree.Element("test")

        self.elem_with_descendant_text = etree.Element("parent")
        child = etree.SubElement(self.elem_with_descendant_text, "child")
        child.text = "Child text"

        self.elem_with_blank_descendant = etree.Element("parent")
        etree.SubElement(self.elem_with_blank_descendant, "child")

        self.elem_no_descendants = etree.Element("parent")

        self.data = {
            "simple": {"path": os.path.join(TEST_DIR, "data", "simple.xml")},
            "no_text": {"path": os.path.join(TEST_DIR, "data", "no_text.xml")}
        }
        # The following hard-coded values must reflect the file content
        #   so tests know what they should find:
        self.data['no_text']['item_count'] = 2
        self.data['simple']['item_count'] = 3
        self.load_simple_xml()

    def load_simple_xml(self):
        # Iterate through each sub-dict in self.data to load the XML files
        for key in self.data:
            path = self.data[key]["path"]
            self.assertTrue(os.path.isfile(path), "missing {}".format(path))

            parser = XMLParser()
            tree = etree.parse(path, parser)
            root = tree.getroot()

            # Store the parsed tree and root in the sub-dictionaries
            self.data[key]["tree"] = tree
            self.data[key]["root"] = root

    def test_do_not_get_empty_leaf_matching_tag(self):
        root = self.data['no_text']['root']
        # Test case where a matching leaf is found
        leaf = get_leaf(root, "leaf", skip_empty=True)
        self.assertIsNone(leaf)

    def test_get_empty_leaf_matching_tag(self):
        root = self.data['no_text']['root']
        leaf = get_leaf(root, "leaf")
        self.assertIsNotNone(leaf)
        self.assertEqual(leaf.tag, "leaf")

    def test_get_first(self):
        root = self.data['simple']['root']
        leaf = get_leaf(root, "leaf", skip_empty=False, spacing=True)
        self.assertIsNotNone(leaf)
        self.assertEqual(leaf.tag, "leaf")
        self.assertEqual(leaf.get('id'), "l1")

    def test_get_first_spacing(self):
        root = self.data['simple']['root']
        leaf = get_leaf(root, "leaf", skip_empty=True, spacing=True)
        self.assertIsNotNone(leaf)
        self.assertEqual(leaf.tag, "leaf")
        self.assertEqual(leaf.get('id'), "l2")

    def test_get_first_non_spacing(self):
        root = self.data['simple']['root']
        leaf = get_leaf(root, "leaf", skip_empty=True, spacing=False)
        self.assertIsNotNone(leaf)
        self.assertEqual(leaf.tag, "leaf")
        self.assertEqual(leaf.get('id'), "l3")

    def test_get_used_leaf_matching_tag(self):
        root = self.data['simple']['root']
        # Test case where a matching leaf is found
        leaf = get_leaf(root, "leaf", skip_empty=True)
        # ^ skip empty should still find one since 'simple' xml file has text there
        self.assertIsNotNone(leaf)

    def test_do_not_get_non_matching_leaf(self):
        root = self.data['simple']['root']
        # Test case where no matching leaf is found
        leaf = get_leaf(root, "nonexistent")
        self.assertIsNone(leaf)

    def test_get_leaf_partial_match(self):
        root = self.data['simple']['root']
        leaf = get_leaf(root, "subitem")
        self.assertIsNotNone(leaf)
        self.assertEqual(leaf.tag, "subitem")

    def test_has_text_direct_text(self):
        self.assertTrue(has_text(self.elem_with_text, False))
        self.assertFalse(has_text(self.elem_with_blank_text, False))
        self.assertFalse(has_text(self.elem_with_no_text, False))

    def test_has_text_descendant_text(self):
        self.assertTrue(has_text(self.elem_with_descendant_text, False))
        self.assertFalse(has_text(self.elem_with_blank_descendant, False))
        self.assertFalse(has_text(self.elem_no_descendants, False))

    def test_used_elements(self):
        elems = [
            self.elem_with_no_text,
            self.elem_with_blank_text,
            self.elem_with_text,
            self.elem_with_descendant_text,
            self.elem_with_blank_descendant
        ]
        placeholders = used_elements(elems)
        self.assertEqual(len(placeholders), 2)
        self.assertIn(self.elem_with_text, placeholders)
        self.assertIn(self.elem_with_descendant_text, placeholders)

    def test_used_element(self):
        elems = [
            self.elem_with_no_text,
            self.elem_with_blank_text,
            self.elem_with_text,
            self.elem_with_descendant_text,
            self.elem_with_blank_descendant
        ]
        first_placeholder = used_element(elems)
        self.assertEqual(first_placeholder, self.elem_with_text)

        # Test with an element that has only descendants with text
        elems_with_descendant_text = [self.elem_with_no_text, self.elem_with_descendant_text]
        first_placeholder = used_element(elems_with_descendant_text)
        self.assertEqual(first_placeholder, self.elem_with_descendant_text)

        # Test with all elements having no text
        elems_no_text = [self.elem_with_no_text, self.elem_with_blank_text, self.elem_with_blank_descendant]
        first_placeholder = used_element(elems_no_text)
        self.assertIsNone(first_placeholder)

    def test_root_element(self):
        root = self.data['simple']['root']
        self.assertEqual(root.tag, 'root')

    def test_items(self):
        # Test the actual test data. If this fails, fix the test data.
        doc_name = 'no_text'
        root = self.data[doc_name]['root']
        items = root.findall('item')
        self.assertEqual(len(items), self.data[doc_name]['item_count'])

        # Check the first item
        item1 = items[0]
        subitem1 = item1.find('subitem')
        self.assertEqual(subitem1.get('id'), 'a')
        leaf1 = subitem1.find('leaf')
        self.assertEqual(leaf1.get('id'), 'l1')

        # Check the second item
        item2 = items[1]
        subitem2 = item2.find('subitem')
        self.assertEqual(subitem2.get('id'), 'b')
        leaf2 = subitem2.find('leaf')
        self.assertIsNone(leaf2.get('id'))

    def test_leaf_elements(self):
        # Test the actual test data. If this fails, fix the test data.
        doc_name = 'no_text'
        root = self.data[doc_name]['root']
        leaves = root.findall('.//leaf')
        self.assertEqual(len(leaves), self.data[doc_name]['item_count'])

        # Verify the first leaf
        leaf1 = leaves[0]
        self.assertEqual(leaf1.get('id'), 'l1')

        # Verify the second leaf
        leaf2 = leaves[1]
        self.assertIsNone(leaf2.get('id'))

    def test_child_tags(self):
        doc_name = 'simple'
        root = self.data[doc_name]['root']
        # Test for tag 'subitem'
        subitems = child_tags(root, 'subitem')
        self.assertEqual(len(subitems), 0)
        items = child_tags(root, 'item')
        self.assertEqual(len(items), self.data[doc_name]['item_count'],
                         "Got {} item child tags in root, expected {}"
                         .format(len(items), self.data[doc_name]['item_count']))
        # self.assertTrue(all(item.tag == 'item' for item in items))
        # ^ failure isn't descriptive, so instead:
        self.assertEqual([item.tag for item in items], ['item' for item in items])

        subitems = child_tags(items[0], 'subitem')
        self.assertEqual(len(subitems), 1)

        # Test for tag 'leaf'
        leaves = child_tags(root, 'leaf')
        self.assertEqual(len(leaves), 0)
        leaves = child_tags(subitems[0], 'leaf')
        self.assertEqual(len(leaves), 1)
        self.assertTrue(all(leaf.tag == 'leaf' for leaf in leaves))
        # TODO: add more data to test different lengths

    def test_no_matching_tags(self):
        root = self.data['simple']['root']
        # Test for a tag *not* in the file
        non_existent = child_tags(root, 'nonexistent')
        self.assertEqual(non_existent, [])


if __name__ == "__main__":
    sys.exit(unittest.main())
    # For quickly getting a traceback for the first test that fails:
    # test = TestSVGReading()
    # test.setUp()
    # for sub in dir(test):
    #     if sub.startswith("test"):
    #         getattr(test, sub)()
    #         count += 1
    # print("All {} test(s) passed.".format(count))
