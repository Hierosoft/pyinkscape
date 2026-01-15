#!/usr/bin/env python3
import os

from pyinkscape import Canvas

t = Canvas()
g = t.group('Layer 1')
g.text("Hello World", center=(100, 100))
t.render(os.path.join('output', 'hello.svg'))
