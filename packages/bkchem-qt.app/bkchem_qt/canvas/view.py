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
ZOOM_SNAP_LEVELS = (
	10.0,
	15.0,
	20.0,
	25.0,
	50.0,
	75.0,
	100.0,
	125.0,
	150.0,
	175.0,
	200.0,
	225.0,
	250.0,
	275.0,
	300.0,
	325.0,
	350.0,
	375.0,
	400.0,
	500.0,
	600.0,
	700.0,
	800.0,
	900.0,
	1000.0,
)


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
	def __init__(
			self, scene: ChemScene,
			parent: PySide6.QtWidgets.QWidget | None = None,
			) -> None:
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
		# direct-set zoom anchor to avoid path-dependent drift in percent sweeps
		self._direct_zoom_anchor_scene: PySide6.QtCore.QPointF | None = None

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

		# Window-level shortcuts are owned by KeybindingManager so user
		# preferences, menu display, and the active document session agree.

	#============================================
	def set_document(self, doc: object) -> None:
		"""Set the active document for this view.

		Args:
			doc: Document instance providing molecules and undo stack.
		"""
		self._document = doc

	#============================================
	@property
	def document(self) -> object:
		"""The active Document, or None if not set."""
		return self._document

	#============================================
	def set_mode_manager(self, manager: object) -> None:
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
		self._invalidate_direct_zoom_anchor()
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
			# right-click dispatches through mouse_press3 (Tk parity)
			if event.button() == PySide6.QtCore.Qt.MouseButton.RightButton:
				self._mode_manager.mouse_press3(scene_pos, event)
			else:
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
	def _viewport_center_scene_precise(self) -> PySide6.QtCore.QPointF:
		"""Return viewport center in scene coords using polygon mapping.

		Using a mapped viewport rect avoids integer-center quantization drift
		from repeated zoom operations (notably long direct-set sweeps).
		"""
		return self.mapToScene(self.viewport().rect()).boundingRect().center()

	#============================================
	def _invalidate_direct_zoom_anchor(self) -> None:
		"""Clear direct-set zoom anchor so next direct set captures fresh center."""
		self._direct_zoom_anchor_scene = None

	#============================================
	def _resolve_direct_zoom_anchor(self) -> PySide6.QtCore.QPointF:
		"""Return stable anchor for direct percent zoom sequences.

		Keeps a fixed scene-center target across consecutive
		``set_zoom_percent(...)`` calls to prevent cumulative drift from
		scrollbar quantization. Rebases if view center moved materially
		(e.g. user pan or non-direct zoom operation).
		"""
		current = self._viewport_center_scene_precise()
		if self._direct_zoom_anchor_scene is None:
			self._direct_zoom_anchor_scene = PySide6.QtCore.QPointF(current)
		else:
			dx = current.x() - self._direct_zoom_anchor_scene.x()
			dy = current.y() - self._direct_zoom_anchor_scene.y()
			if abs(dx) > 1.0 or abs(dy) > 1.0:
				self._direct_zoom_anchor_scene = PySide6.QtCore.QPointF(current)
		return PySide6.QtCore.QPointF(self._direct_zoom_anchor_scene)

	#============================================
	def _recenter_with_correction(self, target_center: PySide6.QtCore.QPointF) -> None:
		"""Center on ``target_center`` with one residual-correction pass."""
		self.centerOn(target_center)
		current_center = self._viewport_center_scene_precise()
		dx = target_center.x() - current_center.x()
		dy = target_center.y() - current_center.y()
		if abs(dx) <= 1e-9 and abs(dy) <= 1e-9:
			return
		self.centerOn(
			PySide6.QtCore.QPointF(
				target_center.x() + dx,
				target_center.y() + dy,
			)
		)

	#============================================
	def reset_zoom(self) -> None:
		"""Reset the view transform to identity (100% zoom)."""
		center_scene = self._viewport_center_scene_precise()
		self.resetTransform()
		self._recenter_with_correction(center_scene)
		self._ensure_upright_transform()
		self._invalidate_direct_zoom_anchor()
		self._zoom_percent = 100.0
		self.zoom_changed.emit(self._zoom_percent)

	#============================================
	def _scale_preserve_viewport_center(self, factor: float) -> None:
		"""Scale while preserving current viewport center in scene coordinates.

		This avoids anchor drift for toolbar/button zoom actions where no
		mouse-wheel cursor anchor is intended.

		Args:
			factor: Multiplicative scale factor.
		"""
		if abs(factor - 1.0) < 1e-12:
			return
		center_scene = self._viewport_center_scene_precise()
		prev_anchor = self.transformationAnchor()
		self.setTransformationAnchor(
			PySide6.QtWidgets.QGraphicsView.ViewportAnchor.AnchorViewCenter
		)
		self.scale(factor, factor)
		self.setTransformationAnchor(prev_anchor)
		self._recenter_with_correction(center_scene)
		self._ensure_upright_transform()

	#============================================
	def _ensure_upright_transform(self) -> None:
		"""Normalize transform to prevent accidental scene reflection/inversion.

		Qt zoom operations should not mirror chemistry content. If a platform
		or transform path introduces a negative axis scale, rebuild an upright
		transform with absolute axis scales while preserving viewport center.
		"""
		t = self.transform()
		if t.m11() >= 0.0 and t.m22() >= 0.0 and t.determinant() >= 0.0:
			return
		center_scene = self._viewport_center_scene_precise()
		sx = abs(t.m11()) if abs(t.m11()) > 1e-12 else 1.0
		sy = abs(t.m22()) if abs(t.m22()) > 1e-12 else 1.0
		self.resetTransform()
		self.scale(sx, sy)
		self._recenter_with_correction(center_scene)

	#============================================
	def _snap_zoom_down(self, percent: float) -> float:
		"""Snap zoom to the nearest configured level at or below ``percent``.

		Using a downward snap preserves fit guarantees for content-fit
		operations by never increasing beyond the computed fit zoom.

		Args:
			percent: Raw zoom percent to quantize.

		Returns:
			Snapped zoom percentage in [ZOOM_MIN_PERCENT, ZOOM_MAX_PERCENT].
		"""
		percent = max(ZOOM_MIN_PERCENT, min(percent, ZOOM_MAX_PERCENT))
		for level in reversed(ZOOM_SNAP_LEVELS):
			if level <= percent + 1e-9:
				return level
		return ZOOM_SNAP_LEVELS[0]

	#============================================
	def _snap_zoom_nearest(self, percent: float) -> float:
		"""Snap zoom to the nearest configured level.

		Args:
			percent: Raw zoom percentage.

		Returns:
			Nearest value from ``ZOOM_SNAP_LEVELS``.
		"""
		percent = max(ZOOM_MIN_PERCENT, min(percent, ZOOM_MAX_PERCENT))
		best = ZOOM_SNAP_LEVELS[0]
		best_diff = abs(best - percent)
		for level in ZOOM_SNAP_LEVELS[1:]:
			diff = abs(level - percent)
			# tie-break toward the larger level for a stable monotone ladder
			if diff < best_diff or (abs(diff - best_diff) < 1e-9 and level > best):
				best = level
				best_diff = diff
		return best

	#============================================
	def zoom_in(self) -> None:
		"""Zoom in by one notch, snapped to the discrete zoom ladder."""
		current = self._zoom_percent
		raw = current * ZOOM_FACTOR_PER_NOTCH
		raw = max(ZOOM_MIN_PERCENT, min(raw, ZOOM_MAX_PERCENT))
		target = self._snap_zoom_nearest(raw)
		if target <= current and current < ZOOM_MAX_PERCENT:
			for level in ZOOM_SNAP_LEVELS:
				if level > current:
					target = level
					break
		if abs(target - current) < 1e-9:
			return
		factor = target / current
		self._zoom_percent = target
		self._scale_preserve_viewport_center(factor)
		self._invalidate_direct_zoom_anchor()
		self.zoom_changed.emit(self._zoom_percent)

	#============================================
	def zoom_out(self) -> None:
		"""Zoom out by one notch, snapped to the discrete zoom ladder."""
		current = self._zoom_percent
		raw = current / ZOOM_FACTOR_PER_NOTCH
		raw = max(ZOOM_MIN_PERCENT, min(raw, ZOOM_MAX_PERCENT))
		target = self._snap_zoom_nearest(raw)
		if target >= current and current > ZOOM_MIN_PERCENT:
			for level in reversed(ZOOM_SNAP_LEVELS):
				if level < current:
					target = level
					break
		if abs(target - current) < 1e-9:
			return
		factor = target / current
		self._zoom_percent = target
		self._scale_preserve_viewport_center(factor)
		self._invalidate_direct_zoom_anchor()
		self.zoom_changed.emit(self._zoom_percent)

	#============================================
	def set_zoom_percent(self, percent: float) -> None:
		"""Set zoom to an exact percentage value.

		Args:
			percent: Target zoom percentage (e.g. 200 for 200%).
		"""
		percent = max(ZOOM_MIN_PERCENT, min(percent, ZOOM_MAX_PERCENT))
		center_scene = self._resolve_direct_zoom_anchor()
		self.resetTransform()
		scale_factor = percent / 100.0
		self.scale(scale_factor, scale_factor)
		self._recenter_with_correction(center_scene)
		self._ensure_upright_transform()
		self._zoom_percent = percent
		self.zoom_changed.emit(self._zoom_percent)

	#============================================
	def zoom_to_fit(self) -> None:
		"""Zoom and pan to fit the paper rectangle in the viewport."""
		self._invalidate_direct_zoom_anchor()
		scene = self.scene()
		if scene is None:
			return
		paper = scene.paper_rect
		self.fitInView(
			paper,
			PySide6.QtCore.Qt.AspectRatioMode.KeepAspectRatio,
		)
		self._ensure_upright_transform()
		# derive zoom percent from the resulting transform and snap down to
		# a stable ladder level without exceeding fit bounds.
		t = self.transform()
		raw_percent = abs(t.m11()) * 100.0
		snapped_percent = self._snap_zoom_down(raw_percent)
		if abs(snapped_percent - raw_percent) > 1e-6:
			self.set_zoom_percent(snapped_percent)
			return
		self._zoom_percent = raw_percent
		self.zoom_changed.emit(self._zoom_percent)

	#============================================
	def zoom_to_content(self) -> None:
		"""Zoom and pan to fit chemistry content (not paper/grid) with a margin.

		Filters scene items to only include chemistry types (atoms, bonds,
		arrows, text, marks). Falls back to zoom_to_fit if no chemistry
		items are found.
		"""
		import bkchem_qt.canvas.items.atom_item
		import bkchem_qt.canvas.items.bond_item
		import bkchem_qt.canvas.items.arrow_item
		import bkchem_qt.canvas.items.text_item
		import bkchem_qt.canvas.items.mark_item

		self._invalidate_direct_zoom_anchor()
		scene = self.scene()
		if scene is None:
			return

		# chemistry item types to include in content rect
		chem_types = (
			bkchem_qt.canvas.items.atom_item.AtomItem,
			bkchem_qt.canvas.items.bond_item.BondItem,
			bkchem_qt.canvas.items.arrow_item.ArrowItem,
			bkchem_qt.canvas.items.text_item.TextItem,
			bkchem_qt.canvas.items.mark_item.MarkItem,
		)

		# accumulate bounding rect of chemistry items only
		content_rect = PySide6.QtCore.QRectF()
		for item in scene.items():
			if isinstance(item, chem_types):
				item_rect = item.mapToScene(item.boundingRect()).boundingRect()
				content_rect = content_rect.united(item_rect)

		# fall back to paper zoom if no chemistry items found
		if content_rect.isEmpty():
			self.zoom_to_fit()
			return

		# add a 10% margin around content
		margin = max(content_rect.width(), content_rect.height()) * 0.1
		content_rect.adjust(-margin, -margin, margin, margin)
		self.fitInView(
			content_rect,
			PySide6.QtCore.Qt.AspectRatioMode.KeepAspectRatio,
		)
		self._ensure_upright_transform()
		# derive zoom percent from the resulting transform and snap to a
		# stable zoom ladder (downward only so content remains fully visible).
		t = self.transform()
		raw_percent = abs(t.m11()) * 100.0
		snapped_percent = self._snap_zoom_down(raw_percent)
		if abs(snapped_percent - raw_percent) > 1e-6:
			self.set_zoom_percent(snapped_percent)
			return
		self._zoom_percent = raw_percent
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
