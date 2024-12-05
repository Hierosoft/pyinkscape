id_finding_test-MARKED.svg is just a version of id_finding_test.svg manually edited to help prevent regression in get by ID features (added for issue #3)
- armor_class_
  - getLeaf with skip_empty=True should return "B"
  - getLeaf with skip_empty=False should return ""
- hp_
  - getLeaf with skip_empty=True should return "A"
  - getLeaf with skip_empty=False should return "A"
