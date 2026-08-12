"""Application status bar with coordinate, mode, and zoom indicators."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# -- label widths in pixels --
#
# Permanent status widgets must be allowed to yield space to the zoom controls
# when a window is narrow.  Their text remains available through the tooltip
# and accessibility API if the painted label is clipped by Qt.
MIN_COORDS_WIDTH = 110
MIN_MODE_WIDTH = 120
PREFERRED_COORDS_WIDTH = 180
PREFERRED_MODE_WIDTH = 140


#============================================
class StatusBar(PySide6.QtWidgets.QStatusBar):
	"""Status bar showing cursor coordinates, active mode, and zoom level.

	Three permanent labels are always visible on the right side of the bar.
	Update them with ``update_coords`` and ``update_mode``.

	Args:
		parent: Optional parent widget.
	"""

	#============================================
	def __init__(self, parent: PySide6.QtWidgets.QWidget | None = None) -> None:
		"""Create the status bar with message area and permanent labels."""
		super().__init__(parent)

		# stretch message label on the left for status messages
		self._message_label = PySide6.QtWidgets.QLabel("")
		self._message_label.setMinimumWidth(0)
		self._message_label.setSizePolicy(
			PySide6.QtWidgets.QSizePolicy.Policy.Ignored,
			PySide6.QtWidgets.QSizePolicy.Policy.Preferred,
		)
		self.addWidget(self._message_label, 1)
		self._context_message = ""
		self._transient_message = ""
		self._message_timer = PySide6.QtCore.QTimer(self)
		self._message_timer.setSingleShot(True)
		self._message_timer.timeout.connect(self.clearMessage)

		# coordinate display label
		self._coords_label = PySide6.QtWidgets.QLabel(self.tr("X: 0.0  Y: 0.0"))
		self._coords_label.setObjectName("cursor-coordinates")
		self._coords_label.setMinimumWidth(MIN_COORDS_WIDTH)
		self._coords_label.setMaximumWidth(PREFERRED_COORDS_WIDTH)
		self._coords_label.setSizePolicy(
			PySide6.QtWidgets.QSizePolicy.Policy.Preferred,
			PySide6.QtWidgets.QSizePolicy.Policy.Preferred,
		)
		self._coords_label.setAccessibleName(self.tr("Cursor coordinates"))
		self._coords_label.setToolTip(self._coords_label.text())

		# active mode label
		self._mode_label = PySide6.QtWidgets.QLabel(self.tr("Mode: Select"))
		self._mode_label.setObjectName("active-editing-mode")
		self._mode_label.setMinimumWidth(MIN_MODE_WIDTH)
		self._mode_label.setMaximumWidth(PREFERRED_MODE_WIDTH)
		self._mode_label.setSizePolicy(
			PySide6.QtWidgets.QSizePolicy.Policy.Preferred,
			PySide6.QtWidgets.QSizePolicy.Policy.Preferred,
		)
		self._mode_label.setAccessibleName(self.tr("Active editing mode"))
		self._mode_label.setToolTip(self._mode_label.text())

		# add as permanent widgets so they stay visible at all times
		self.addPermanentWidget(self._coords_label)
		self.addPermanentWidget(self._mode_label)

	#============================================
	def update_coords(self, x: float, y: float) -> None:
		"""Update the coordinate display.

		Args:
			x: Current cursor x position in scene coordinates.
			y: Current cursor y position in scene coordinates.
		"""
		text = f"X: {x:.1f}  Y: {y:.1f}"
		self._coords_label.setText(text)
		self._coords_label.setToolTip(text)

	#============================================
	@property
	def context_message(self) -> str:
		"""Return the persistent interaction guidance behind transient results."""
		return self._context_message

	#============================================
	@property
	def visible_message(self) -> str:
		"""Return the one message currently painted in the status area."""
		return self._message_label.text()

	#============================================
	def set_context_message(self, text: str) -> None:
		"""Set guidance that reappears after Qt hides a transient message."""
		self._context_message = text
		if not self._transient_message:
			self._message_label.setText(text)

	#============================================
	def showMessage(self, text: str, timeout: int = 0) -> None:
		"""Show one transient result, replacing any earlier transient result."""
		self._message_timer.stop()
		self._transient_message = text
		self._message_label.setText(text)
		self.messageChanged.emit(text)
		if timeout > 0:
			self._message_timer.start(timeout)

	#============================================
	def clearMessage(self) -> None:
		"""Clear the transient result and restore persistent context guidance."""
		self._message_timer.stop()
		if not self._transient_message:
			return
		self._transient_message = ""
		self._message_label.setText(self._context_message)
		self.messageChanged.emit("")

	#============================================
	def currentMessage(self) -> str:
		"""Return the active transient result, matching QStatusBar semantics."""
		return self._transient_message

	#============================================
	def show_message(self, text: str, timeout: int = 3000) -> None:
		"""Show a transient result without replacing interaction guidance.

		Args:
			text: Message text to display.
			timeout: Milliseconds before clearing (0 for persistent).
		"""
		self.showMessage(text, timeout)

	#============================================
	def update_mode(self, name: str) -> None:
		"""Update the active mode display.

		Args:
			name: Human-readable name of the current editing mode.
		"""
		text = f"Mode: {name}"
		self._mode_label.setText(text)
		self._mode_label.setToolTip(text)
