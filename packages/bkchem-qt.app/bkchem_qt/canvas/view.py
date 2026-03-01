"""Chemistry view with zoom and pan for the BKChem Qt canvas."""

# Standard Library
from __future__ import annotations

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules -- type hint only
from bkchem_qt.canvas.scene import ChemScene  # noqa: F401 (used in type hints)

# -- zoom limits as percentage values --
ZOOM_MIN_PERCENT = 10.0
ZOOM_MAX_PERCENT = 1000.0
ZOOM_FACTOR_PER_NOTCH = 1.15


#============================================
class ChemView(PySide6.QtWidgets.QGraphicsView):
	"""QGraphicsView subclass with mouse-wheel zoom and middle-click pan.

	Provides cursor-centered zoom, middle-click drag panning,
	Alt+left-click panning for macOS trackpads, and Ctrl+0 zoom reset.

	Signals:
		zoom_changed: Emitted when zoom level changes, carries percentage.
		mouse_moved: Emitted on mouse move, carries scene x and y.

	Args:
		scene: The ChemScene to display.
		parent: Optional parent widget.
	"""

	# -- signals --
	zoom_changed = PySide6.QtCore.Signal(float)
	mouse_moved = PySide6.QtCore.Signal(float, float)

	#============================================
	def __init__(self, scene: ChemScene, parent: PySide6.QtWidgets.QWidget = None):
		"""Initialize the view with rendering hints and key bindings.

		Args:
			scene: The ChemScene instance to display.
			parent: Optional parent widget.
		"""
		super().__init__(scene, parent)

		# current zoom percentage
		self._zoom_percent: float = 100.0

		# track alt+left-click panning state
		self._alt_panning: bool = False

		# mode manager for dispatching mouse/key events to active mode
		self._mode_manager = None

		# active document reference (set by MainWindow via set_document)
		self._document = None

		# rendering quality
		self.setRenderHint(PySide6.QtGui.QPainter.RenderHint.Antialiasing, True)
		self.setViewportUpdateMode(
			PySide6.QtWidgets.QGraphicsView.ViewportUpdateMode.SmartViewportUpdate
		)

		# zoom anchors under cursor
		self.setTransformationAnchor(
			PySide6.QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse
		)

		# enable mouse tracking so mouseMoveEvent fires without button held
		self.setMouseTracking(True)

		# keyboard shortcut: Ctrl+0 resets zoom
		shortcut = PySide6.QtGui.QShortcut(
			PySide6.QtGui.QKeySequence(self.tr("Ctrl+0")),
			self,
		)
		shortcut.activated.connect(self.reset_zoom)

	#============================================
	def set_document(self, doc) -> None:
		"""Set the active document for this view.

		Args:
			doc: Document instance providing molecules and undo stack.
		"""
		self._document = doc

	#============================================
	@property
	def document(self):
		"""The active Document, or None if not set."""
		return self._document

	#============================================
	def set_mode_manager(self, manager) -> None:
		"""Set the mode manager for event dispatch.

		Args:
			manager: ModeManager instance that handles mouse/key events.
		"""
		self._mode_manager = manager

	#============================================
	def wheelEvent(self, event: PySide6.QtGui.QWheelEvent) -> None:
		"""Zoom in or out centered on the cursor position.

		Args:
			event: The wheel event with angle delta.
		"""
		degrees = event.angleDelta().y()
		if degrees == 0:
			return

		# compute number of standard notches (120 units per notch)
		notches = degrees / 120.0

		if notches > 0:
			factor = ZOOM_FACTOR_PER_NOTCH ** notches
		else:
			factor = (1.0 / ZOOM_FACTOR_PER_NOTCH) ** abs(notches)

		# clamp zoom to allowed range
		proposed = self._zoom_percent * factor
		if proposed < ZOOM_MIN_PERCENT:
			factor = ZOOM_MIN_PERCENT / self._zoom_percent
		elif proposed > ZOOM_MAX_PERCENT:
			factor = ZOOM_MAX_PERCENT / self._zoom_percent

		self._zoom_percent *= factor
		self.scale(factor, factor)
		self.zoom_changed.emit(self._zoom_percent)

	#============================================
	def mousePressEvent(self, event: PySide6.QtGui.QMouseEvent) -> None:
		"""Start panning on middle-click or Alt+left-click.

		Args:
			event: The mouse press event.
		"""
		# middle-click pan
		if event.button() == PySide6.QtCore.Qt.MouseButton.MiddleButton:
			self.setDragMode(
				PySide6.QtWidgets.QGraphicsView.DragMode.ScrollHandDrag
			)
			# synthesize a left press so the drag mode activates
			fake = PySide6.QtGui.QMouseEvent(
				event.type(),
				event.position(),
				event.globalPosition(),
				PySide6.QtCore.Qt.MouseButton.LeftButton,
				PySide6.QtCore.Qt.MouseButton.LeftButton,
				event.modifiers(),
			)
			super().mousePressEvent(fake)
			return

		# alt+left-click pan (macOS trackpad alternative)
		if (event.button() == PySide6.QtCore.Qt.MouseButton.LeftButton
				and event.modifiers() & PySide6.QtCore.Qt.KeyboardModifier.AltModifier):
			self._alt_panning = True
			self.setDragMode(
				PySide6.QtWidgets.QGraphicsView.DragMode.ScrollHandDrag
			)
			super().mousePressEvent(event)
			return

		# dispatch to active mode
		if self._mode_manager is not None:
			scene_pos = self.mapToScene(event.position().toPoint())
			self._mode_manager.mouse_press(scene_pos, event)
		super().mousePressEvent(event)

	#============================================
	def mouseReleaseEvent(self, event: PySide6.QtGui.QMouseEvent) -> None:
		"""Stop panning on middle-button or Alt+left-button release.

		Args:
			event: The mouse release event.
		"""
		if event.button() == PySide6.QtCore.Qt.MouseButton.MiddleButton:
			# synthesize left release to end the scroll-hand drag
			fake = PySide6.QtGui.QMouseEvent(
				event.type(),
				event.position(),
				event.globalPosition(),
				PySide6.QtCore.Qt.MouseButton.LeftButton,
				PySide6.QtCore.Qt.MouseButton.NoButton,
				event.modifiers(),
			)
			super().mouseReleaseEvent(fake)
			self.setDragMode(
				PySide6.QtWidgets.QGraphicsView.DragMode.NoDrag
			)
			return

		if (event.button() == PySide6.QtCore.Qt.MouseButton.LeftButton
				and self._alt_panning):
			self._alt_panning = False
			super().mouseReleaseEvent(event)
			self.setDragMode(
				PySide6.QtWidgets.QGraphicsView.DragMode.NoDrag
			)
			return

		# dispatch to active mode
		if self._mode_manager is not None:
			scene_pos = self.mapToScene(event.position().toPoint())
			self._mode_manager.mouse_release(scene_pos, event)
		super().mouseReleaseEvent(event)

	#============================================
	def mouseMoveEvent(self, event: PySide6.QtGui.QMouseEvent) -> None:
		"""Emit scene coordinates as the mouse moves.

		Args:
			event: The mouse move event.
		"""
		scene_pos = self.mapToScene(event.position().toPoint())
		self.mouse_moved.emit(scene_pos.x(), scene_pos.y())
		# dispatch to active mode
		if self._mode_manager is not None:
			self._mode_manager.mouse_move(scene_pos, event)
		super().mouseMoveEvent(event)

	#============================================
	def mouseDoubleClickEvent(self, event: PySide6.QtGui.QMouseEvent) -> None:
		"""Forward double-click to the active mode.

		Args:
			event: The mouse double-click event.
		"""
		if self._mode_manager is not None:
			scene_pos = self.mapToScene(event.position().toPoint())
			self._mode_manager.mouse_double_click(scene_pos, event)
		super().mouseDoubleClickEvent(event)

	#============================================
	def keyPressEvent(self, event: PySide6.QtGui.QKeyEvent) -> None:
		"""Forward key press to the active mode.

		Args:
			event: The key press event.
		"""
		if self._mode_manager is not None:
			self._mode_manager.key_press(event)
		super().keyPressEvent(event)

	#============================================
	def keyReleaseEvent(self, event: PySide6.QtGui.QKeyEvent) -> None:
		"""Forward key release to the active mode.

		Args:
			event: The key release event.
		"""
		if self._mode_manager is not None:
			self._mode_manager.key_release(event)
		super().keyReleaseEvent(event)

	#============================================
	def reset_zoom(self) -> None:
		"""Reset the view transform to identity (100% zoom)."""
		self.resetTransform()
		self._zoom_percent = 100.0
		self.zoom_changed.emit(self._zoom_percent)

	#============================================
	def set_background_color(self, color: str) -> None:
		"""Set the viewport background color.

		Uses a drawBackground override because QGraphicsView's
		setBackgroundBrush does not reliably affect viewport rendering
		on macOS with Qt 6. The color is stored and applied via
		drawBackground on every paint.

		Args:
			color: CSS hex color string (e.g. '#1e1e2e').
		"""
		self._bg_color = PySide6.QtGui.QColor(color)
		# force a full viewport repaint so the new color takes effect
		self.viewport().update()

	#============================================
	def drawBackground(self, painter: PySide6.QtGui.QPainter, rect: PySide6.QtCore.QRectF) -> None:
		"""Paint the viewport background before scene items.

		Fills the exposed rect with the custom background color if set,
		then delegates to the base class for default scene rendering.

		Args:
			painter: The painter for the viewport.
			rect: The exposed scene rect to paint.
		"""
		if hasattr(self, '_bg_color'):
			painter.fillRect(rect, self._bg_color)
		else:
			super().drawBackground(painter, rect)

	#============================================
	@property
	def zoom_percent(self) -> float:
		"""Current zoom level as a percentage."""
		return self._zoom_percent
