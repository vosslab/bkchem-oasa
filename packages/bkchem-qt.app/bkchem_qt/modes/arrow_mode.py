"""Arrow drawing mode with frontend-only gesture policy."""

# Standard Library
import math

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.canvas.graphics_retirement
import bkchem_qt.canvas.items.render_ops_painter
import bkchem_qt.config.geometry_units
import bkchem_qt.modes.base_mode

_PREVIEW_PEN_WIDTH = 1.5
_PREVIEW_PEN_STYLE = PySide6.QtCore.Qt.PenStyle.DashLine
_ANGLE_STEPS = frozenset({1, 6, 18, 30})


#============================================
class ArrowMode(bkchem_qt.modes.base_mode.BaseMode):
	"""Create one backend-owned Arrow from a dragged interaction gesture."""

	#============================================
	def __init__(
			self, view: PySide6.QtWidgets.QGraphicsView,
			parent: PySide6.QtCore.QObject | None = None,
			) -> None:
		"""Initialize the Arrow gesture state and declared presentation settings."""
		super().__init__(view, parent)
		self._name = "Arrow"
		self._persistent_operation = None
		self._preview_line = None
		self._preview_scene = None
		self._start_point = None
		self._angle_step = 30
		self._fixed_length = True
		self._spline = False
		self._arrow_kind = "normal"
		self._cursor = PySide6.QtCore.Qt.CursorShape.CrossCursor

	#============================================
	@property
	def status_hint(self) -> str:
		"""Return an affirmative explanation of the current Arrow gesture."""
		length = "grid length" if self._fixed_length else "drawn length"
		shape = "spline" if self._spline else "straight"
		return f"Drag a {shape} {self._arrow_kind} arrow at {self._angle_step} degree steps; {length}"

	#============================================
	def set_persistent_operation(self, operation: object | None) -> None:
		"""Install or clear the generic immutable-request callback."""
		if operation is not None and not callable(operation):
			raise TypeError("Arrow persistent operation must be callable")
		self._persistent_operation = operation

	#============================================
	def on_submode_switch(self, submode_index: int, name: str) -> None:
		"""Apply one visible Arrow setting to future backend-bound requests."""
		if submode_index == 0:
			angle_step = int(name)
			if angle_step not in _ANGLE_STEPS:
				raise ValueError("Arrow angle step is unsupported")
			self._angle_step = angle_step
		elif submode_index == 1:
			self._fixed_length = name == "fixed"
		elif submode_index == 2:
			if name not in {"anormal", "spline"}:
				raise ValueError("Arrow shape is unsupported")
			self._spline = name == "spline"
		elif submode_index == 3:
			if name not in {"normal", "electron", "retro", "equilibrium", "equilibrium2"}:
				raise ValueError("Arrow type is unsupported")
			self._arrow_kind = name
		else:
			raise ValueError("Arrow submode group is unsupported")
		self._reset_gesture()
		self.status_message.emit(self.status_hint)

	#============================================
	def mouse_press(self, scene_pos: PySide6.QtCore.QPointF, event: object) -> None:
		"""Begin one Arrow drag from a transient scene point."""
		self._start_point = scene_pos
		self.status_message.emit("Drag to place the arrow endpoint")

	#============================================
	def mouse_move(self, scene_pos: PySide6.QtCore.QPointF, event: object) -> None:
		"""Update a disposable preview using the same interaction constraint."""
		if self._start_point is None:
			return
		end_point = self._constrained_end(scene_pos)
		self._retire_preview_line()
		scene = self._env.scene
		if scene is None:
			return
		color = bkchem_qt.canvas.items.render_ops_painter.get_canvas_color("preview")
		pen = PySide6.QtGui.QPen(PySide6.QtGui.QColor(color))
		pen.setWidthF(_PREVIEW_PEN_WIDTH)
		pen.setStyle(_PREVIEW_PEN_STYLE)
		self._preview_line = scene.addLine(
			self._start_point.x(), self._start_point.y(), end_point.x(), end_point.y(), pen,
		)
		self._preview_scene = scene

	#============================================
	def mouse_release(self, scene_pos: PySide6.QtCore.QPointF, event: object) -> None:
		"""Submit one immutable Arrow intent when its constrained span is nonzero."""
		start_point = self._start_point
		self._retire_preview_line()
		self._start_point = None
		if start_point is None or self._env.scene is None:
			return
		end_point = self._constrained_end(scene_pos, start_point)
		delta_x = end_point.x() - start_point.x()
		delta_y = end_point.y() - start_point.y()
		if delta_x * delta_x + delta_y * delta_y <= 25.0:
			self.status_message.emit("Drag farther to place an arrow")
			return
		if self._persistent_operation is None:
			self.status_message.emit("Document cannot accept a persistent edit")
			return
		from bkchem_qt.models import document_session
		request = document_session.PersistentOperationRequest(
			"arrow.add", "Add Arrow",
			(
				("kind", self._arrow_kind), ("spline", self._spline),
				("endpoints", ((start_point.x(), start_point.y()), (end_point.x(), end_point.y()))),
			),
		)
		outcome = self._persistent_operation(request)
		self.status_message.emit(outcome.message)

	#============================================
	def deactivate(self) -> None:
		"""Retire all preview state before another mode becomes active."""
		self._reset_gesture()
		super().deactivate()

	#============================================
	def _constrained_end(
			self, scene_pos: PySide6.QtCore.QPointF,
			start_point: PySide6.QtCore.QPointF | None = None,
			) -> PySide6.QtCore.QPointF:
		"""Return the declared snapped endpoint without mutating persistent state."""
		start = self._start_point if start_point is None else start_point
		if start is None:
			return scene_pos
		delta_x = scene_pos.x() - start.x()
		delta_y = scene_pos.y() - start.y()
		length = math.hypot(delta_x, delta_y)
		if length == 0.0:
			return scene_pos
		angle = math.atan2(delta_y, delta_x)
		step_radians = math.radians(self._angle_step)
		angle = round(angle / step_radians) * step_radians
		if self._fixed_length:
			scene = self._env.scene
			if scene is not None and hasattr(scene, "grid_spacing_pt"):
				length = float(scene.grid_spacing_pt)
			else:
				length = bkchem_qt.config.geometry_units.DEFAULT_BOND_LENGTH_PT
		end_point = PySide6.QtCore.QPointF(
			start.x() + math.cos(angle) * length,
			start.y() + math.sin(angle) * length,
		)
		return end_point

	#============================================
	def _reset_gesture(self) -> None:
		"""Discard transient preview and endpoint state without a backend request."""
		self._retire_preview_line()
		self._start_point = None

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
					preview_scene, [preview_line], reaper=self._graphics_retirement_reaper,
				)
			coordinator.raise_if_callback_failed("Arrow preview retirement failed")
		finally:
			self._preview_line = None
			self._preview_scene = None
