"""Chemistry scene for the BKChem Qt canvas."""

# PIP3 modules
import math
import re
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import oasa.hex_grid
import bkchem_qt.bridge.oasa_bridge
import bkchem_qt.canvas.graphics_retirement
import bkchem_qt.config.geometry_units
import bkchem_qt.themes.theme_loader

# -- default scene dimensions in pixels --
DEFAULT_SCENE_WIDTH = 4000
DEFAULT_SCENE_HEIGHT = 3000

# -- paper defaults --
PAPER_WIDTH = 2000
PAPER_HEIGHT = 1500
PAPER_Z_VALUE = -200

# -- grid defaults (scene-space points) --
DEFAULT_GRID_SPACING_PT = bkchem_qt.config.geometry_units.DEFAULT_BOND_LENGTH_PT
GRID_Z_VALUE = -100

_PAPER_NUMBER_RE = re.compile(r"(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)")


#============================================
class HexGridOverlayItem(PySide6.QtWidgets.QGraphicsItem):
	"""Draw one disposable hex-grid projection from OASA display geometry.

	The overlay is intentionally a frontend-only item.  It retains no document
	objects and delegates all vertex and edge geometry to ``oasa.hex_grid``.
	"""

	#============================================
	def __init__(self, paper_rect: PySide6.QtCore.QRectF, spacing: float,
			grid_colors: dict[str, str]) -> None:
		"""Initialize cached geometry and style for one paper-local overlay."""
		super().__init__()
		self.setAcceptedMouseButtons(PySide6.QtCore.Qt.MouseButton.NoButton)
		self.setAcceptHoverEvents(False)
		self._paper_rect = PySide6.QtCore.QRectF()
		self._line_path = PySide6.QtGui.QPainterPath()
		self._dot_path = PySide6.QtGui.QPainterPath()
		self._line_pen = PySide6.QtGui.QPen()
		self._dot_pen = PySide6.QtGui.QPen()
		self._dot_brush = PySide6.QtGui.QBrush()
		self.set_style(grid_colors)
		self.set_geometry(paper_rect, spacing)

	#============================================
	def boundingRect(self) -> PySide6.QtCore.QRectF:
		"""Return the persistent paper-local extent of this decoration."""
		result = PySide6.QtCore.QRectF(self._paper_rect)
		return result

	#============================================
	def paint(self, painter: PySide6.QtGui.QPainter,
			option: PySide6.QtWidgets.QStyleOptionGraphicsItem,
			widget: PySide6.QtWidgets.QWidget | None = None) -> None:
		"""Paint cached lines and vertex dots without creating child items."""
		painter.save()
		painter.setClipRect(self._paper_rect)
		painter.setPen(self._line_pen)
		painter.setBrush(PySide6.QtCore.Qt.BrushStyle.NoBrush)
		painter.drawPath(self._line_path)
		painter.setPen(self._dot_pen)
		painter.setBrush(self._dot_brush)
		painter.drawPath(self._dot_path)
		painter.restore()

	#============================================
	def set_geometry(self, paper_rect: PySide6.QtCore.QRectF, spacing: float) -> None:
		"""Replace cached display paths after paper or spacing changes."""
		self.prepareGeometryChange()
		self._paper_rect = PySide6.QtCore.QRectF(paper_rect)
		self._line_path = _hex_grid_line_path(self._paper_rect, spacing)
		self._dot_path = _hex_grid_dot_path(self._paper_rect, spacing)
		self.update()

	#============================================
	def set_style(self, grid_colors: dict[str, str]) -> None:
		"""Change colors without rebuilding grid geometry."""
		line_pen = PySide6.QtGui.QPen(PySide6.QtGui.QColor(grid_colors["line"]))
		line_pen.setWidthF(0.375)
		dot_pen = PySide6.QtGui.QPen(
			PySide6.QtGui.QColor(grid_colors["dot_outline"])
		)
		dot_pen.setWidthF(0.375)
		self._line_pen = line_pen
		self._dot_pen = dot_pen
		self._dot_brush = PySide6.QtGui.QBrush(
			PySide6.QtGui.QColor(grid_colors["dot_fill"])
		)
		self.update()


#============================================
def _hex_grid_line_path(paper_rect: PySide6.QtCore.QRectF,
		spacing: float) -> PySide6.QtGui.QPainterPath:
	"""Build the current paper's honeycomb path from OASA's pure geometry."""
	path = PySide6.QtGui.QPainterPath()
	edges = oasa.hex_grid.generate_hex_honeycomb_edges(
		paper_rect.left(), paper_rect.top(), paper_rect.right(), paper_rect.bottom(),
		spacing,
	)
	if edges is not None:
		for (x1, y1), (x2, y2) in edges:
			path.moveTo(x1, y1)
			path.lineTo(x2, y2)
	return path


#============================================
def _hex_grid_dot_path(paper_rect: PySide6.QtCore.QRectF,
		spacing: float) -> PySide6.QtGui.QPainterPath:
	"""Build the current paper's vertex-dot path from OASA's pure geometry."""
	path = PySide6.QtGui.QPainterPath()
	points = oasa.hex_grid.generate_hex_grid_points(
		paper_rect.left(), paper_rect.top(), paper_rect.right(), paper_rect.bottom(),
		spacing,
	)
	if points is not None:
		for px, py in points:
			path.addEllipse(px - 1.0, py - 1.0, 2.0, 2.0)
	return path


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
			theme_name: str = "dark", grid_spacing_pt: float = DEFAULT_GRID_SPACING_PT,
			grid_snap_enabled: bool = True) -> None:
		"""Initialize the scene with default rect, paper, and grid.

		Args:
			parent: Optional parent QObject.
			theme_name: Theme name for initial colors.
			grid_spacing_pt: Hex-grid spacing in scene-space points.
			grid_snap_enabled: Whether point snapping is enabled.
		"""
		super().__init__(parent)
		self._theme_name = theme_name
		# set scene rectangle
		self.setSceneRect(0, 0, DEFAULT_SCENE_WIDTH, DEFAULT_SCENE_HEIGHT)
		# leave background transparent so the QGraphicsView dark viewport shows through

		# paper state
		self._paper_item: PySide6.QtWidgets.QGraphicsRectItem = None

		# grid state
		self._grid_spacing_pt: float = float(grid_spacing_pt)
		self._grid_visible: bool = True
		self._grid_snap_enabled: bool = bool(grid_snap_enabled)
		self._grid_overlay: HexGridOverlayItem | None = None
		self._contents_lifecycle = "active"

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

		# get paper color and outline from YAML theme
		paper_color = bkchem_qt.themes.theme_loader.get_paper_color(self._theme_name)
		outline_color = bkchem_qt.themes.theme_loader.get_paper_outline(self._theme_name)

		# outline pen from YAML theme (visible paper border)
		paper_pen = PySide6.QtGui.QPen(PySide6.QtGui.QColor(outline_color))
		paper_pen.setWidthF(1.5)

		self._paper_item = self.addRect(
			paper_x, paper_y, PAPER_WIDTH, PAPER_HEIGHT,
			paper_pen,
			PySide6.QtGui.QBrush(PySide6.QtGui.QColor(paper_color)),
		)
		self._paper_item.setZValue(PAPER_Z_VALUE)

	#============================================
	def _build_grid(self) -> None:
		"""Create one paper-local hex-grid display item from OASA geometry."""
		grid_colors = bkchem_qt.themes.theme_loader.get_grid_colors(self._theme_name)
		overlay = HexGridOverlayItem(
			self._paper_item.rect(), self._grid_spacing_pt, grid_colors,
		)
		overlay.setZValue(GRID_Z_VALUE)
		overlay.setVisible(self._grid_visible)
		self.addItem(overlay)
		self._grid_overlay = overlay

	#============================================
	def apply_theme(self, theme_name: str) -> None:
		"""Update paper and grid colors from the named YAML theme.

		The single grid overlay changes pens and brushes in place without
		rebuilding its OASA-generated display geometry.

		Args:
			theme_name: 'dark' or 'light'.
		"""
		self._theme_name = theme_name
		# update paper color and outline
		paper_color = bkchem_qt.themes.theme_loader.get_paper_color(theme_name)
		outline_color = bkchem_qt.themes.theme_loader.get_paper_outline(theme_name)
		self._paper_item.setBrush(
			PySide6.QtGui.QBrush(PySide6.QtGui.QColor(paper_color))
		)
		paper_pen = PySide6.QtGui.QPen(PySide6.QtGui.QColor(outline_color))
		paper_pen.setWidthF(1.5)
		self._paper_item.setPen(paper_pen)
		# recolor grid items in place (no destroy+rebuild)
		self._recolor_grid(theme_name)

	#============================================
	def apply_paper_model(self, paper_model: object) -> None:
		"""Apply preserved CDML paper attributes without changing document data.

		CDML stores custom paper sizes in millimetres.  The scene uses points,
		so custom dimensions are converted using 72 points per inch.  Named
		legacy sizes use their physical dimensions before portrait/landscape
		orientation is applied.
		"""
		attributes = paper_model.attributes
		if not attributes:
			self._paper_attributes = {}
			scene_rect = self.sceneRect()
			paper_x = (scene_rect.width() - PAPER_WIDTH) / 2.0
			paper_y = (scene_rect.height() - PAPER_HEIGHT) / 2.0
			self._paper_item.setRect(paper_x, paper_y, PAPER_WIDTH, PAPER_HEIGHT)
			self._rebuild_grid()
			return
		self._paper_attributes = dict(attributes)
		catalog = {
			name.lower(): dimensions
			for name, dimensions in bkchem_qt.bridge.oasa_bridge.paper_catalog().items()
		}
		paper_type = attributes.get("type", "").lower()
		if paper_type == "custom":
			width_mm = _paper_dimension(attributes.get("size_x"))
			height_mm = _paper_dimension(attributes.get("size_y"))
			if width_mm is None or height_mm is None:
				self._reset_default_paper()
				return
		else:
			dimensions = catalog.get(paper_type)
			if dimensions is None:
				self._reset_default_paper()
				return
			width_mm, height_mm = dimensions
		orientation = attributes.get("orientation", "portrait").lower()
		if orientation == "landscape":
			width_mm, height_mm = height_mm, width_mm
		width = width_mm * 72.0 / 25.4
		height = height_mm * 72.0 / 25.4
		scene_rect = self.sceneRect()
		paper_x = (scene_rect.width() - width) / 2.0
		paper_y = (scene_rect.height() - height) / 2.0
		self._paper_item.setRect(paper_x, paper_y, width, height)
		self._rebuild_grid()

	#============================================
	def _reset_default_paper(self) -> None:
		"""Restore the visual default for incomplete or unknown raw paper XML."""
		scene_rect = self.sceneRect()
		paper_x = (scene_rect.width() - PAPER_WIDTH) / 2.0
		paper_y = (scene_rect.height() - PAPER_HEIGHT) / 2.0
		self._paper_item.setRect(paper_x, paper_y, PAPER_WIDTH, PAPER_HEIGHT)
		self._rebuild_grid()

	#============================================
	def _rebuild_grid(self) -> None:
		"""Update the one grid overlay after a paper rectangle change."""
		self._require_active_contents("rebuild the grid")
		if self._grid_overlay is None:
			self._build_grid()
			return
		self._grid_overlay.set_geometry(
			self._paper_item.rect(), self._grid_spacing_pt,
		)

	#============================================
	def _dispose_grid(
			self,
			reaper: bkchem_qt.canvas.graphics_retirement.DetachedGraphicsRetirementReaper | None = None,
			) -> None:
		"""Synchronously retire the one disposable grid overlay item."""
		self._require_active_contents("dispose the grid")
		overlay = self._grid_overlay
		self._grid_overlay = None
		if overlay is None:
			return
		coordinator = bkchem_qt.canvas.graphics_retirement.GraphicsRetirementCoordinator()
		coordinator.retire_scene_projection_items(self, [overlay], reaper=reaper)
		coordinator.raise_if_callback_failed("ChemScene grid retirement failed")

	#============================================
	def dispose_contents(
			self,
			reaper: bkchem_qt.canvas.graphics_retirement.DetachedGraphicsRetirementReaper | None = None,
			) -> None:
		"""Retire all graphics through this scene's terminal ownership transition."""
		if self._contents_lifecycle == "disposed":
			return
		if self._contents_lifecycle == "disposing":
			raise RuntimeError("ChemScene disposal is already in progress")
		if self._contents_lifecycle == "failed":
			raise RuntimeError("ChemScene disposal previously failed")
		self._contents_lifecycle = "disposing"
		paper = self._paper_item
		overlay = self._grid_overlay
		# Clear Python sentinels while locals retain their wrappers.  Qt ownership
		# changes below must never cause assignment to release a retired wrapper.
		self._paper_item = None
		self._grid_overlay = None
		try:
			decorations = [item for item in (overlay, paper) if item is not None]
			if decorations:
				coordinator = (
					bkchem_qt.canvas.graphics_retirement.GraphicsRetirementCoordinator()
				)
				coordinator.retire_scene_projection_items(
					self, decorations, reaper=reaper,
				)
			# Named decorations are gone; clear owns every anonymous remaining item.
			self.clear()
			if decorations:
				coordinator.raise_if_callback_failed(
					"ChemScene decoration retirement failed"
				)
		except Exception:
			self._contents_lifecycle = "failed"
			raise
		self._contents_lifecycle = "disposed"

	#============================================
	def _require_active_contents(self, operation: str) -> None:
		"""Reject live-grid work after the terminal scene transition begins."""
		if self._contents_lifecycle != "active":
			raise RuntimeError(
				f"Cannot {operation}; ChemScene is {self._contents_lifecycle}"
			)
	#============================================
	def _recolor_grid(self, theme_name: str) -> None:
		"""Recolor the existing grid overlay without regenerating geometry.

		Args:
			theme_name: 'dark' or 'light'.
		"""
		if self._grid_overlay is None:
			return
		grid_colors = bkchem_qt.themes.theme_loader.get_grid_colors(theme_name)
		self._grid_overlay.set_style(grid_colors)

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
		if self._grid_overlay is not None:
			self._grid_overlay.setVisible(visible)

	#============================================
	@property
	def grid_snap_enabled(self) -> bool:
		"""Whether snapping to the hex grid is currently enabled."""
		return self._grid_snap_enabled

	#============================================
	def set_grid_snap_enabled(self, enabled: bool) -> None:
		"""Enable or disable snapping to the hex grid."""
		self._grid_snap_enabled = bool(enabled)

	#============================================
	@property
	def grid_spacing_pt(self) -> float:
		"""Current hex-grid spacing in scene-space points."""
		return self._grid_spacing_pt

	#============================================
	def set_grid_spacing_pt(self, value: float) -> None:
		"""Set grid spacing and update the grid overlay geometry.

		Args:
			value: New spacing in scene-space points.
		"""
		self._require_active_contents("change grid spacing")
		new_spacing = float(value)
		if new_spacing <= 0.0:
			return
		if abs(new_spacing - self._grid_spacing_pt) < 1e-6:
			return
		self._grid_spacing_pt = new_spacing
		self._rebuild_grid()

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
			x, y, self._grid_spacing_pt,
		)
		return snapped


#============================================
def _paper_dimension(value: object) -> float | None:
	"""Return one finite positive raw CDML dimension without raising on input."""
	text = str(value).strip()
	if len(text) > 50 or _PAPER_NUMBER_RE.fullmatch(text) is None:
		return None
	dimension = float(text)
	if not math.isfinite(dimension) or dimension <= 0.0:
		return None
	return dimension
