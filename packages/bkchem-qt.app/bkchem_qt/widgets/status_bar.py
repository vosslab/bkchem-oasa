"""Application status bar with coordinate, mode, and zoom indicators."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# -- minimum label widths in pixels --
MIN_COORDS_WIDTH = 180
MIN_MODE_WIDTH = 140


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
		self.addWidget(self._message_label, 1)

		# coordinate display label
		self._coords_label = PySide6.QtWidgets.QLabel(self.tr("X: 0.0  Y: 0.0"))
		self._coords_label.setMinimumWidth(MIN_COORDS_WIDTH)

		# active mode label
		self._mode_label = PySide6.QtWidgets.QLabel(self.tr("Mode: Select"))
		self._mode_label.setMinimumWidth(MIN_MODE_WIDTH)

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

	#============================================
	def show_message(self, text: str, timeout: int = 3000) -> None:
		"""Show a temporary message in the left message area.

		Args:
			text: Message text to display.
			timeout: Milliseconds before clearing (0 for persistent).
		"""
		self._message_label.setText(text)
		if timeout > 0:
			PySide6.QtCore.QTimer.singleShot(
				timeout, lambda: self._message_label.setText("")
			)

	#============================================
	def update_mode(self, name: str) -> None:
		"""Update the active mode display.

		Args:
			name: Human-readable name of the current editing mode.
		"""
		text = f"Mode: {name}"
		self._mode_label.setText(text)
