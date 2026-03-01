"""Edit ribbon for element entry and bond type selection."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets


# bond type display names mapped to internal type characters
_BOND_TYPES = [
	("Normal", "n"),
	("Wedge", "w"),
	("Hatch", "h"),
	("Bold", "b"),
	("Wavy", "a"),
]


#============================================
class EditRibbon(PySide6.QtWidgets.QWidget):
	"""Context-sensitive edit panel for element entry and bond type selection.

	Shows an element symbol text field, a bond order combo box, and a
	bond type combo box. Emits signals when the user changes any value
	so the active draw mode can update its defaults.

	Args:
		parent: Optional parent widget.
	"""

	# emitted when the element symbol changes
	element_changed = PySide6.QtCore.Signal(str)
	# emitted when the bond order changes
	bond_order_changed = PySide6.QtCore.Signal(int)
	# emitted when the bond type changes
	bond_type_changed = PySide6.QtCore.Signal(str)

	#============================================
	def __init__(self, parent=None):
		"""Initialize the edit ribbon layout and widgets.

		Args:
			parent: Optional parent widget.
		"""
		super().__init__(parent)
		layout = PySide6.QtWidgets.QHBoxLayout(self)
		layout.setContentsMargins(4, 2, 4, 2)
		layout.setSpacing(8)
		# element symbol entry
		element_label = PySide6.QtWidgets.QLabel("Element:")
		layout.addWidget(element_label)
		self._element_edit = PySide6.QtWidgets.QLineEdit("C")
		self._element_edit.setMaximumWidth(50)
		self._element_edit.setToolTip("Element symbol for new atoms")
		layout.addWidget(self._element_edit)
		# bond order combo
		order_label = PySide6.QtWidgets.QLabel("Bond:")
		layout.addWidget(order_label)
		self._order_combo = PySide6.QtWidgets.QComboBox()
		self._order_combo.addItem("Single", 1)
		self._order_combo.addItem("Double", 2)
		self._order_combo.addItem("Triple", 3)
		self._order_combo.setToolTip("Bond order for new bonds")
		layout.addWidget(self._order_combo)
		# bond type combo
		type_label = PySide6.QtWidgets.QLabel("Type:")
		layout.addWidget(type_label)
		self._type_combo = PySide6.QtWidgets.QComboBox()
		for display_name, type_char in _BOND_TYPES:
			self._type_combo.addItem(display_name, type_char)
		self._type_combo.setToolTip("Bond type for new bonds")
		layout.addWidget(self._type_combo)
		# stretch to push widgets left
		layout.addStretch()
		# connect signals
		self._element_edit.editingFinished.connect(self._on_element_changed)
		self._order_combo.currentIndexChanged.connect(self._on_order_changed)
		self._type_combo.currentIndexChanged.connect(self._on_type_changed)

	# ------------------------------------------------------------------
	# Public accessors
	# ------------------------------------------------------------------

	#============================================
	def current_element(self) -> str:
		"""Return the current element symbol text.

		Returns:
			Element symbol string (e.g. 'C', 'N', 'O').
		"""
		text = self._element_edit.text().strip()
		return text

	#============================================
	def current_bond_order(self) -> int:
		"""Return the currently selected bond order.

		Returns:
			Integer bond order (1, 2, or 3).
		"""
		order = self._order_combo.currentData()
		return order

	#============================================
	def current_bond_type(self) -> str:
		"""Return the currently selected bond type character.

		Returns:
			Bond type character string (e.g. 'n', 'w', 'h').
		"""
		bond_type = self._type_combo.currentData()
		return bond_type

	# ------------------------------------------------------------------
	# Signal handlers
	# ------------------------------------------------------------------

	#============================================
	def _on_element_changed(self) -> None:
		"""Emit element_changed when the user finishes editing the element."""
		text = self._element_edit.text().strip()
		if text:
			self.element_changed.emit(text)

	#============================================
	def _on_order_changed(self, _index: int) -> None:
		"""Emit bond_order_changed when the combo box selection changes.

		Args:
			_index: New combo box index (unused, we read data instead).
		"""
		order = self._order_combo.currentData()
		if order is not None:
			self.bond_order_changed.emit(order)

	#============================================
	def _on_type_changed(self, _index: int) -> None:
		"""Emit bond_type_changed when the combo box selection changes.

		Args:
			_index: New combo box index (unused, we read data instead).
		"""
		bond_type = self._type_combo.currentData()
		if bond_type is not None:
			self.bond_type_changed.emit(bond_type)
