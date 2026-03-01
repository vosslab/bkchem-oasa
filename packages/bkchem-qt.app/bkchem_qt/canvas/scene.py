"""Chemistry scene for the BKChem Qt canvas."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import oasa.hex_grid
import bkchem_qt.themes.theme_loader

# -- default scene dimensions in pixels --
DEFAULT_SCENE_WIDTH = 4000
DEFAULT_SCENE_HEIGHT = 3000

# -- paper defaults --
PAPER_WIDTH = 2000
PAPER_HEIGHT = 1500
PAPER_Z_VALUE = -200

# -- grid defaults --
# hex grid spacing matches the Tk version default bond length
DEFAULT_GRID_SPACING = 26.5
GRID_Z_VALUE = -100


#============================================
class ChemScene(PySide6.QtWidgets.QGraphicsScene):
	"""QGraphicsScene subclass for 2D chemistry drawing.

	Provides a paper rectangle on a transparent background,
	an optional snap grid overlay constrained to the paper area,
	and coordinate snapping helpers. Colors are loaded from the
	shared YAML theme files in bkchem_data/themes/.

	Args:
		parent: Optional parent QObject.
		theme_name: Initial theme name ('dark' or 'light').
	"""

	#============================================
	def __init__(self, parent: PySide6.QtCore.QObject = None,
			theme_name: str = "dark"):
		"""Initialize the scene with default rect, paper, and grid.

		Args:
			parent: Optional parent QObject.
			theme_name: Theme name for initial colors.
		"""
		super().__init__(parent)
		self._theme_name = theme_name
		# set scene rectangle
		self.setSceneRect(0, 0, DEFAULT_SCENE_WIDTH, DEFAULT_SCENE_HEIGHT)
		# leave background transparent so the QGraphicsView dark viewport shows through

		# paper state
		self._paper_item: PySide6.QtWidgets.QGraphicsRectItem = None

		# grid state
		self._grid_spacing: int = DEFAULT_GRID_SPACING
		self._grid_visible: bool = True
		self._grid_group: PySide6.QtWidgets.QGraphicsItemGroup = None

		# build the paper rectangle centered in the scene
		self._build_paper()
		# build the grid constrained to the paper area
		self._build_grid()

	#============================================
	def _build_paper(self) -> None:
		"""Create the paper rectangle centered in the scene.

		The paper sits at PAPER_Z_VALUE (-200), below the grid at -100,
		so grid lines render on top of the paper surface. Color comes
		from the active YAML theme file.
		"""
		# center the paper within the scene rect
		scene_rect = self.sceneRect()
		paper_x = (scene_rect.width() - PAPER_WIDTH) / 2.0
		paper_y = (scene_rect.height() - PAPER_HEIGHT) / 2.0

		# get paper color from YAML theme
		paper_color = bkchem_qt.themes.theme_loader.get_paper_color(self._theme_name)

		self._paper_item = self.addRect(
			paper_x, paper_y, PAPER_WIDTH, PAPER_HEIGHT,
			PySide6.QtGui.QPen(PySide6.QtCore.Qt.PenStyle.NoPen),
			PySide6.QtGui.QBrush(PySide6.QtGui.QColor(paper_color)),
		)
		self._paper_item.setZValue(PAPER_Z_VALUE)

	#============================================
	def _build_grid(self) -> None:
		"""Create hex grid honeycomb lines and dots constrained to the paper rect.

		Uses oasa.hex_grid to generate pointy-top hexagonal grid lines
		and vertex dots matching the Tk version. Colors come from the
		active YAML theme file. Items are collected into a group that
		can be shown or hidden as a unit.
		"""
		self._grid_group = self.createItemGroup([])
		self._grid_group.setZValue(GRID_Z_VALUE)
		self._grid_group.setVisible(self._grid_visible)

		# get grid colors from YAML theme
		grid_colors = bkchem_qt.themes.theme_loader.get_grid_colors(self._theme_name)

		# constrain grid to the paper rect boundaries
		p_rect = self._paper_item.rect()
		left = p_rect.left()
		top = p_rect.top()
		right = p_rect.right()
		bottom = p_rect.bottom()

		# draw honeycomb line segments
		line_pen = PySide6.QtGui.QPen(
			PySide6.QtGui.QColor(grid_colors["line"])
		)
		line_pen.setWidthF(1.0)
		line_pen.setCosmetic(True)

		edges = oasa.hex_grid.generate_hex_honeycomb_edges(
			left, top, right, bottom, self._grid_spacing,
		)
		if edges is not None:
			for (x1, y1), (x2, y2) in edges:
				line = self.addLine(x1, y1, x2, y2, line_pen)
				self._grid_group.addToGroup(line)

		# draw dots at hex grid vertices
		dot_pen = PySide6.QtGui.QPen(
			PySide6.QtGui.QColor(grid_colors["dot_outline"])
		)
		dot_pen.setWidthF(0.375)
		dot_brush = PySide6.QtGui.QBrush(
			PySide6.QtGui.QColor(grid_colors["dot_fill"])
		)
		dot_radius = 1.5

		points = oasa.hex_grid.generate_hex_grid_points(
			left, top, right, bottom, self._grid_spacing,
		)
		if points is not None:
			for px, py in points:
				dot = self.addEllipse(
					px - dot_radius, py - dot_radius,
					dot_radius * 2, dot_radius * 2,
					dot_pen, dot_brush,
				)
				self._grid_group.addToGroup(dot)

	#============================================
	def apply_theme(self, theme_name: str) -> None:
		"""Update paper and grid colors from the named YAML theme.

		Rebuilds the grid with new colors and updates the paper fill.

		Args:
			theme_name: 'dark' or 'light'.
		"""
		self._theme_name = theme_name
		# update paper color
		paper_color = bkchem_qt.themes.theme_loader.get_paper_color(theme_name)
		self._paper_item.setBrush(
			PySide6.QtGui.QBrush(PySide6.QtGui.QColor(paper_color))
		)
		# rebuild grid with new theme colors
		if self._grid_group is not None:
			self.destroyItemGroup(self._grid_group)
			self._grid_group = None
		self._build_grid()

	#============================================
	@property
	def paper_rect(self) -> PySide6.QtCore.QRectF:
		"""Return the paper rectangle in scene coordinates.

		Returns:
			QRectF describing the paper area.
		"""
		return self._paper_item.rect()

	#============================================
	def set_paper_color(self, color: str) -> None:
		"""Change the paper fill color.

		Args:
			color: CSS hex color string (e.g. '#ffffff').
		"""
		self._paper_item.setBrush(
			PySide6.QtGui.QBrush(PySide6.QtGui.QColor(color))
		)

	#============================================
	@property
	def grid_visible(self) -> bool:
		"""Whether the grid overlay is currently visible."""
		return self._grid_visible

	#============================================
	def set_grid_visible(self, visible: bool) -> None:
		"""Show or hide the grid overlay.

		Args:
			visible: True to show grid lines, False to hide.
		"""
		self._grid_visible = visible
		if self._grid_group is not None:
			self._grid_group.setVisible(visible)

	#============================================
	def snap_to_grid(self, x: float, y: float) -> tuple:
		"""Snap coordinates to the nearest hex grid point.

		Args:
			x: Scene x coordinate.
			y: Scene y coordinate.

		Returns:
			Tuple of (snapped_x, snapped_y) on the hex grid.
		"""
		snapped = oasa.hex_grid.snap_to_hex_grid(
			x, y, self._grid_spacing,
		)
		return snapped
