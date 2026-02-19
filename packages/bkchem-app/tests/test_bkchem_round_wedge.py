# SPDX-License-Identifier: LGPL-3.0-or-later

"""BKChem rounded wedge and Haworth q rendering tests."""

# local repo modules
import bkchem.bond
import bkchem.classes
import singleton_store


class _DummyPaper(object):
	def __init__(self):
		self.created = []

	def real_to_canvas(self, value):
		return value

	def create_polygon(self, coords, **kwargs):
		self.created.append(("polygon", coords, kwargs))
		return len(self.created)

	def create_line(self, coords, **kwargs):
		self.created.append(("line", coords, kwargs))
		return len(self.created)

	def addtag_withtag(self, tag, item):
		return None

	def register_id(self, item, obj):
		return None


class _DummyParent(object):
	def __init__(self, paper):
		self.paper = paper


class _DummyAtom(object):
	def __init__(self, x, y):
		self.x = x
		self.y = y
		self.show = False
		self.neighbors = []
		self.occupied_valency = 0

	def get_xy_on_paper(self):
		return (self.x, self.y)

	def bbox(self, substract_font_descent=True):
		return (self.x - 1.0, self.y - 1.0, self.x + 1.0, self.y + 1.0)


#============================================
def test_bkchem_rounded_wedge_polygon():
	standard = bkchem.classes.standard()
	singleton_store.Screen.dpi = 72
	bond = bkchem.bond.bond(standard=standard, type="w", order=1)
	paper = _DummyPaper()
	bond.parent = _DummyParent(paper)
	bond.wedge_width = 6.0
	bond.line_width = 1.0
	polygon = bond._rounded_wedge_polygon((0.0, 0.0, 12.0, 0.0))
	assert polygon
	assert len(polygon) % 2 == 0
	assert len(polygon) >= 8


#============================================
def test_bkchem_haworth_q_draws_round_line():
	standard = bkchem.classes.standard()
	singleton_store.Screen.dpi = 72
	bond = bkchem.bond.bond(standard=standard, type="q", order=1)
	paper = _DummyPaper()
	bond.parent = _DummyParent(paper)
	bond.atom1 = _DummyAtom(0.0, 0.0)
	bond.atom2 = _DummyAtom(10.0, 0.0)
	bond.line_color = "#000"
	bond.wedge_width = 6.0
	bond.line_width = 1.0
	bond._transform = None
	bond._draw_q1()
	assert paper.created
	kind, _coords, kwargs = paper.created[-1]
	assert kind == "line"
	assert kwargs.get("capstyle") == "round"
	assert kwargs.get("width") == 6.0
