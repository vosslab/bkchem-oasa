"""Arrow drawing mode."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.canvas.graphics_retirement
import bkchem_qt.canvas.items.render_ops_painter
import bkchem_qt.modes.base_mode

_PREVIEW_PEN_WIDTH = 1.5
_PREVIEW_PEN_STYLE = PySide6.QtCore.Qt.PenStyle.DashLine


#============================================
class ArrowMode(bkchem_qt.modes.base_mode.BaseMode):
	"""Mode for drawing reaction arrows.

	Click to set the start point, drag to preview, and release to
	create the arrow. The preview is shown as a dashed line while
	dragging.

	Args:
		view: The ChemView widget that owns this mode.
		parent: Optional parent QObject.
	"""

	#============================================
	def __init__(
			self,
			view: PySide6.QtWidgets.QGraphicsView,
			parent: PySide6.QtCore.QObject | None = None,
			) -> None:
		"""Initialize the arrow mode.

		Args:
			view: The ChemView widget that dispatches events.
			parent: Optional parent QObject.
		"""
		super().__init__(view, parent)
		self._name = "Arrow"
		self._persistent_operation = None
		# preview line item shown during drag
		self._preview_line = None
		self._preview_scene = None
		# start point in scene coordinates
		self._start_point = None
		self._cursor = PySide6.QtCore.Qt.CursorShape.CrossCursor

	#============================================
	def set_persistent_operation(self, operation: object | None) -> None:
		"""Install or clear the generic immutable-request callback."""
		if operation is not None and not callable(operation):
			raise TypeError("Arrow persistent operation must be callable")
		self._persistent_operation = operation

	#============================================
	def mouse_press(
			self,
			scene_pos: PySide6.QtCore.QPointF,
			event: object,
			) -> None:
		"""Set the arrow start point.

		Args:
			scene_pos: Position in scene coordinates where the arrow begins.
			event: The mouse event.
		"""
		self._start_point = scene_pos
		self.status_message.emit("Drag to set arrow endpoint")

	#============================================
	def mouse_move(
			self,
			scene_pos: PySide6.QtCore.QPointF,
			event: object,
			) -> None:
		"""Update the preview arrow line during drag.

		Creates a dashed line from the start point to the current
		mouse position to show where the arrow will be placed.

		Args:
			scene_pos: Current position in scene coordinates.
			event: The mouse event.
		"""
		if self._start_point is None:
			return
		# A preview is terminal feedback, never undo-owned graphics.
		self._retire_preview_line()
		scene = self._env.scene
		if scene is None:
			return
		# create a new preview line
		color = bkchem_qt.canvas.items.render_ops_painter.get_canvas_color("preview")
		pen = PySide6.QtGui.QPen(PySide6.QtGui.QColor(color))
		pen.setWidthF(_PREVIEW_PEN_WIDTH)
		pen.setStyle(_PREVIEW_PEN_STYLE)
		self._preview_line = scene.addLine(
			self._start_point.x(), self._start_point.y(),
			scene_pos.x(), scene_pos.y(),
			pen,
		)
		self._preview_scene = scene

	#============================================
	def mouse_release(
			self,
			scene_pos: PySide6.QtCore.QPointF,
			event: object,
			) -> None:
		"""Commit a persistent arrow candidate and clean up the preview.

		The live line is transient feedback only.  A session-owned frontend
		action converts plain coordinates to complete CDML and rebuilds this Qt
		projection from the accepted backend snapshot.

		Args:
			scene_pos: End position in scene coordinates.
			 event: The mouse event.
		"""
		self._retire_preview_line()
		scene = self._env.scene
		if scene is None:
			self._start_point = None
			return
		message = "Arrow mode active"
		# only create the arrow if we have a start point and some distance
		if self._start_point is not None:
			dx = scene_pos.x() - self._start_point.x()
			dy = scene_pos.y() - self._start_point.y()
			# minimum distance threshold to avoid accidental zero-length arrows
			if (dx * dx + dy * dy) > 25.0:
				if self._persistent_operation is None:
					message = "Document cannot accept a persistent edit"
				else:
					from bkchem_qt.models import document_session
					request = document_session.PersistentOperationRequest(
						"arrow.add", "Arrow",
						(
							("start", (self._start_point.x(), self._start_point.y())),
							("end", (scene_pos.x(), scene_pos.y())),
						),
					)
					outcome = self._persistent_operation(request)
					message = outcome.message
		self._start_point = None
		self.status_message.emit(message)

	#============================================
	def deactivate(self) -> None:
		"""Clean up the preview line when leaving arrow mode."""
		self._retire_preview_line()
		self._start_point = None
		super().deactivate()

	#============================================
	def _retire_preview_line(self) -> None:
		"""Terminally retire the known preview line before releasing its wrapper."""
		preview_line = self._preview_line
		preview_scene = self._preview_scene
		if preview_line is None:
			return
		try:
			coordinator = bkchem_qt.canvas.graphics_retirement.GraphicsRetirementCoordinator()
			if preview_scene is None:
				coordinator.retire_detached_projection_items(
					[preview_line], reaper=self._graphics_retirement_reaper,
				)
			else:
				coordinator.retire_scene_projection_items(
					preview_scene, [preview_line],
					reaper=self._graphics_retirement_reaper,
				)
			coordinator.raise_if_callback_failed("Arrow preview retirement failed")
		finally:
			self._preview_line = None
			self._preview_scene = None
