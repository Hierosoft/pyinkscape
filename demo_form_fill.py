import os
import sys

import pyinkscape

from pyinkscape import Canvas
from pyinkscape.xmlnav import get_leaf


# ------------------------------------------------------------------------------
# Development information
# ------------------------------------------------------------------------------
print("-" * 60)
print("pyInkscape demo form fill code")
print("-" * 60)
print(f"lxml available: {pyinkscape.inkscape._LXML_AVAILABLE}")
print(f"chirptext available: {pyinkscape.inkscape._CHIRPTEXT_AVAILABLE}")
print()
REPO_DIR = os.path.dirname(os.path.realpath(__file__))
doc_name = "fillable_sheet.svg"
no_ext = os.path.splitext(doc_name)[0]
outpath = no_ext + "-OUTPUT.svg"
try_dirs = [
    os.path.join(REPO_DIR, "test", "data"),
    REPO_DIR,
]
form_path = None
for try_dir in try_dirs:
    try_path = os.path.join(try_dir, doc_name)
    if os.path.isfile(try_path):
        # Use a copy in the current working directory if available.
        form_path = os.path.abspath(try_path)
        # Use abspath not realpath to allow symlinks to work as user may
        #   expect (be used as files).

if not form_path:
    print(f"This demo requires {doc_name} but it was not in"
          f" any of: {try_dirs}. Go to the source code"
          " repository and run this demo from a downloaded copy"
          " or download the file to the current directory.")
    sys.exit(1)

canvas = Canvas(filepath=form_path)

fill_ids = {
    "armor_class_": 17,
}

for key, value in fill_ids.items():
    if not canvas.setField(key, value):
        print("Failed to set {}={}".format(key, repr(value)))

if os.path.isfile(outpath):
    # A more complete program can confirm overwrite here
    #   and render if confirmed.
    print(f"Error: {outpath} already exists."
          " Delete or rename it to try filling the form again.")
    sys.exit(1)

canvas.render(outpath=outpath)

print(f"Saved {outpath} with {fill_ids}!")