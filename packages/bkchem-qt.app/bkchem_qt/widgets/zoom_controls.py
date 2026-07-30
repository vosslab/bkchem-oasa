"""Zoom control widget with buttons, label, and slider."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# -- slider range constants --
SLIDER_MIN = 10
SLIDER_MAX = 1000
SLIDER_STEP = 5
SLIDER_DEFAULT = 100


#============================================
class ZoomControls(PySide6.QtWidgets.QWidget):
	"""Horizontal widget with zoom buttons, percentage label, and slider.

	Provides zoom in, zoom out, reset, page, and content buttons
	alongside a percentage label and a horizontal slider for
	continuous zoom adjustment.

	Signals:
		zoom_in_clicked: Emitted when the + button is clicked.
		zoom_out_clicked: Emitted when the - button is clicked.
		reset_zoom_clicked: Emitted when the 100% button is clicked.
		zoom_to_fit_clicked: Emitted when the Fit button is clicked.
		zoom_to_content_clicked: Emitted when the Content button is clicked.
		zoom_slider_changed: Emitted when the slider value changes, carries int.

	Args:
		parent: Optional parent widget.
	"""

	# -- signals --
	zoom_in_clicked = PySide6.QtCore.Signal()
	zoom_out_clicked = PySide6.QtCore.Signal()
	reset_zoom_clicked = PySide6.QtCore.Signal()
	zoom_to_fit_clicked = PySide6.QtCore.Signal()
	zoom_to_content_clicked = PySide6.QtCore.Signal()
	zoom_slider_changed = PySide6.QtCore.Signal(int)

	#============================================
	def __init__(self, parent: PySide6.QtWidgets.QWidget | None = None) -> None:
		"""Create the zoom controls layout with buttons, label, and slider.

		Args:
			parent: Optional parent widget.
		"""
		super().__init__(parent)

		layout = PySide6.QtWidgets.QHBoxLayout(self)
		layout.setContentsMargins(2, 0, 2, 0)
		layout.setSpacing(4)

		# zoom out button
		self._btn_zoom_out = PySide6.QtWidgets.QPushButton("-")
		self._btn_zoom_out.setFixedWidth(28)
		self._btn_zoom_out.setToolTip("Zoom out")
		self._btn_zoom_out.clicked.connect(self.zoom_out_clicked.emit)
		layout.addWidget(self._btn_zoom_out)

		# percentage label
		self._label = PySide6.QtWidgets.QLabel("100%")
		self._label.setMinimumWidth(48)
		self._label.setAlignment(
			PySide6.QtCore.Qt.AlignmentFlag.AlignCenter
		)
		layout.addWidget(self._label)

		# zoom in button
		self._btn_zoom_in = PySide6.QtWidgets.QPushButton("+")
		self._btn_zoom_in.setFixedWidth(28)
		self._btn_zoom_in.setToolTip("Zoom in")
		self._btn_zoom_in.clicked.connect(self.zoom_in_clicked.emit)
		layout.addWidget(self._btn_zoom_in)

		# reset button
		self._btn_reset = PySide6.QtWidgets.QPushButton("100%")
		self._btn_reset.setToolTip("Reset zoom to 100%")
		self._btn_reset.clicked.connect(self.reset_zoom_clicked.emit)
		layout.addWidget(self._btn_reset)

		# page button (zoom to fit paper)
		self._btn_fit = PySide6.QtWidgets.QPushButton("Page")
		self._btn_fit.setToolTip("Zoom to page")
		self._btn_fit.clicked.connect(self.zoom_to_fit_clicked.emit)
		layout.addWidget(self._btn_fit)

		# content button
		self._btn_content = PySide6.QtWidgets.QPushButton("Content")
		self._btn_content.setToolTip("Zoom to page content")
		self._btn_content.clicked.connect(
			self.zoom_to_content_clicked.emit
		)
		layout.addWidget(self._btn_content)

		# horizontal slider
		self._slider = PySide6.QtWidgets.QSlider(
			PySide6.QtCore.Qt.Orientation.Horizontal
		)
		self._slider.setRange(SLIDER_MIN, SLIDER_MAX)
		self._slider.setSingleStep(SLIDER_STEP)
		self._slider.setValue(SLIDER_DEFAULT)
		self._slider.setFixedWidth(120)
		self._slider.setToolTip("Drag to zoom")
		self._slider.valueChanged.connect(self._on_slider_changed)
		layout.addWidget(self._slider)

	#============================================
	def _on_slider_changed(self, value: int) -> None:
		"""Forward slider value changes as the zoom_slider_changed signal.

		Args:
			value: The new slider value (zoom percentage).
		"""
		self.zoom_slider_changed.emit(value)

	#============================================
	def update_zoom_display(self, percent: float) -> None:
		"""Update the label text and slider position to reflect zoom.

		Blocks the slider signal during the update to avoid a
		feedback loop between the slider and the view.

		Args:
			percent: Current zoom percentage (e.g. 150.0 for 150%).
		"""
		# update label text
		label_text = f"{percent:.0f}%"
		self._label.setText(label_text)
		# update slider without triggering valueChanged
		self._slider.blockSignals(True)
		clamped = max(SLIDER_MIN, min(int(round(percent)), SLIDER_MAX))
		self._slider.setValue(clamped)
		self._slider.blockSignals(False)
