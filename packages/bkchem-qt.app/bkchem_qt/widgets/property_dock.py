"""Dockable property panel for editing atom and bond properties."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.bond_presentation
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.models.document
import bkchem_qt.undo.commands


#============================================
class PropertyDock(PySide6.QtWidgets.QDockWidget):
	"""Dock widget showing editable properties for the selected scene item.

	Displays atom fields (symbol, charge, show label) when an AtomItem is
	selected, bond fields (order, type) when a BondItem is selected, or a
	brief document summary when nothing is selected. Uses a QStackedWidget
	to switch between the three panels.

	Args:
		document: The Document model for counting molecules and atoms.
		parent: Optional parent widget.
	"""

	#============================================
	def __init__(
			self, document: bkchem_qt.models.document.Document,
			parent: PySide6.QtWidgets.QWidget | None = None,
			) -> None:
		"""Initialize the property dock with atom, bond, and info panels.

		Args:
			document: Document model for document info display.
			parent: Optional parent widget.
		"""
		super().__init__("Properties", parent)
		self._document = document
		self._atom_properties_capture = None
		self._bond_properties_capture = None
		# prevent the dock from being closed by the user
		self.setFeatures(
			PySide6.QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable
			| PySide6.QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable
		)
		# track the currently displayed item to avoid redundant updates
		self._current_item = None
		# guard flag to suppress feedback loops during programmatic updates
		self._updating = False
		# build all three panel pages
		self._stack = PySide6.QtWidgets.QStackedWidget()
		self._build_info_panel()
		self._build_atom_panel()
		self._build_bond_panel()
		self.setWidget(self._stack)
		# set a reasonable fixed width so the dock does not consume too much space
		self.setMinimumWidth(200)
		self.setMaximumWidth(300)

	#============================================
	def set_document(
			self, document: bkchem_qt.models.document.Document | None,
			bond_properties_capture: object | None = None,
			atom_properties_capture: object | None = None,
			) -> None:
		"""Rebind the dock to a replacement Document or detach it.

		Args:
			document: The Document whose selection and undo stack to use,
				or None while its owning scene is being disposed.
			bond_properties_capture: Optional exact-session bond intent capture callback.
			atom_properties_capture: Optional exact-session atom intent capture callback.
		"""
		self._document = document
		self._bond_properties_capture = bond_properties_capture
		self._atom_properties_capture = atom_properties_capture
		self._current_item = None
		if document is None:
			self._info_label.setText("No document")
			self._stack.setCurrentIndex(0)
			return
		self.update_from_selection()

	# ------------------------------------------------------------------
	# Panel construction
	# ------------------------------------------------------------------

	#============================================
	def _build_info_panel(self) -> None:
		"""Build the document info panel shown when nothing is selected."""
		panel = PySide6.QtWidgets.QWidget()
		layout = PySide6.QtWidgets.QVBoxLayout(panel)
		layout.setContentsMargins(8, 8, 8, 8)
		# document summary label
		self._info_label = PySide6.QtWidgets.QLabel("No selection")
		self._info_label.setWordWrap(True)
		self._info_label.setAlignment(PySide6.QtCore.Qt.AlignmentFlag.AlignTop)
		layout.addWidget(self._info_label)
		layout.addStretch()
		# page index 0
		self._stack.addWidget(panel)

	#============================================
	def _build_atom_panel(self) -> None:
		"""Build the atom property editing panel."""
		panel = PySide6.QtWidgets.QWidget()
		layout = PySide6.QtWidgets.QFormLayout(panel)
		layout.setContentsMargins(8, 8, 8, 8)
		# section heading
		heading = PySide6.QtWidgets.QLabel("Atom Properties")
		heading.setStyleSheet("font-weight: bold;")
		layout.addRow(heading)
		# symbol field
		self._atom_symbol_edit = PySide6.QtWidgets.QLineEdit()
		self._atom_symbol_edit.setMaxLength(3)
		self._atom_symbol_edit.setToolTip("Element symbol (e.g. C, N, O)")
		self._atom_symbol_edit.editingFinished.connect(self._on_atom_symbol_changed)
		layout.addRow("Symbol:", self._atom_symbol_edit)
		# charge spin box
		self._atom_charge_spin = PySide6.QtWidgets.QSpinBox()
		self._atom_charge_spin.setRange(-9, 9)
		self._atom_charge_spin.setToolTip("Formal charge")
		self._atom_charge_spin.valueChanged.connect(self._on_atom_charge_changed)
		layout.addRow("Charge:", self._atom_charge_spin)
		# show label checkbox
		self._atom_show_check = PySide6.QtWidgets.QCheckBox("Show label")
		self._atom_show_check.setToolTip("Show or hide the atom symbol on the canvas")
		self._atom_show_check.stateChanged.connect(self._on_atom_show_changed)
		layout.addRow(self._atom_show_check)
		# page index 1
		self._stack.addWidget(panel)

	#============================================
	def _build_bond_panel(self) -> None:
		"""Build the bond property editing panel."""
		panel = PySide6.QtWidgets.QWidget()
		layout = PySide6.QtWidgets.QFormLayout(panel)
		layout.setContentsMargins(8, 8, 8, 8)
		# section heading
		heading = PySide6.QtWidgets.QLabel("Bond Properties")
		heading.setStyleSheet("font-weight: bold;")
		layout.addRow(heading)
		# order combo box
		self._bond_order_combo = PySide6.QtWidgets.QComboBox()
		self._bond_order_combo.addItem("1 (single)", 1)
		self._bond_order_combo.addItem("2 (double)", 2)
		self._bond_order_combo.addItem("3 (triple)", 3)
		self._bond_order_combo.setToolTip("Bond order")
		self._bond_order_combo.currentIndexChanged.connect(
			self._on_bond_order_changed
		)
		layout.addRow("Order:", self._bond_order_combo)
		# type combo box
		self._bond_type_combo = PySide6.QtWidgets.QComboBox()
		self._set_bond_type_choices()
		self._bond_type_combo.setToolTip("Bond type")
		self._bond_type_combo.currentIndexChanged.connect(
			self._on_bond_type_changed
		)
		layout.addRow("Type:", self._bond_type_combo)
		# page index 2
		self._stack.addWidget(panel)

	# ------------------------------------------------------------------
	# Public update slot
	# ------------------------------------------------------------------

	#============================================
	def update_from_selection(self) -> None:
		"""Update the dock contents based on the current scene selection.

		Reads the scene's selectedItems list and shows the appropriate
		panel. When a single AtomItem or BondItem is selected, its
		properties are loaded into the editing widgets. Otherwise,
		the info panel is displayed with a document summary.
		"""
		if self._document is None:
			self._current_item = None
			self._info_label.setText("No document")
			self._stack.setCurrentIndex(0)
			return
		scene = self._document._scene
		if scene is None:
			self._show_info_panel()
			return
		selected = scene.selectedItems()
		# filter to atoms and bonds only
		atoms = [
			item for item in selected
			if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
		]
		bonds = [
			item for item in selected
			if isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem)
		]
		# single atom selected
		if len(atoms) == 1 and len(bonds) == 0:
			self._show_atom_panel(atoms[0])
			return
		# single bond selected
		if len(bonds) == 1 and len(atoms) == 0:
			self._show_bond_panel(bonds[0])
			return
		# nothing selected or multi-selection: show document info
		self._current_item = None
		self._show_info_panel()

	# ------------------------------------------------------------------
	# Panel switching helpers
	# ------------------------------------------------------------------

	#============================================
	def _show_info_panel(self) -> None:
		"""Switch to the document info panel and update the summary text."""
		self._current_item = None
		# count molecules and total atoms across the document
		molecules = self._document.molecules
		n_molecules = len(molecules)
		n_atoms = sum(len(mol.atoms) for mol in molecules)
		if n_molecules == 0:
			text = "Empty document"
		else:
			text = f"{n_molecules} molecule(s), {n_atoms} atom(s)"
		self._info_label.setText(text)
		self._stack.setCurrentIndex(0)

	#============================================
	def _show_atom_panel(
			self, atom_item: bkchem_qt.canvas.items.atom_item.AtomItem,
			) -> None:
		"""Switch to the atom panel and populate fields from the AtomItem.

		Args:
			atom_item: The selected AtomItem whose model drives the fields.
		"""
		self._current_item = atom_item
		model = atom_item.atom_model
		# set guard flag to suppress change callbacks during population
		self._updating = True
		self._atom_symbol_edit.setText(model.symbol)
		self._atom_charge_spin.setValue(model.charge)
		self._atom_show_check.setChecked(model.show)
		self._updating = False
		self._stack.setCurrentIndex(1)

	#============================================
	def _show_bond_panel(
			self, bond_item: bkchem_qt.canvas.items.bond_item.BondItem,
			) -> None:
		"""Switch to the bond panel and populate fields from the BondItem.

		Args:
			bond_item: The selected BondItem whose model drives the fields.
		"""
		self._current_item = bond_item
		model = bond_item.bond_model
		# set guard flag to suppress change callbacks during population
		self._updating = True
		self._set_bond_type_choices(model.type)
		# find the combo index matching the current bond order
		order_index = self._bond_order_combo.findData(model.order)
		if order_index >= 0:
			self._bond_order_combo.setCurrentIndex(order_index)
		# find the combo index matching the current bond type
		type_index = self._bond_type_combo.findData(model.type)
		if type_index >= 0:
			self._bond_type_combo.setCurrentIndex(type_index)
		self._updating = False
		self._stack.setCurrentIndex(2)

	#============================================
	def _set_bond_type_choices(self, current_type: str | None = None) -> None:
		"""Populate generic styles and preserve an existing Haworth display.

		Args:
			current_type: Existing projected canonical style, if any.
		"""
		self._bond_type_combo.clear()
		for type_char, label in bkchem_qt.bond_presentation.choices_for_display(current_type):
			self._bond_type_combo.addItem(label, type_char)

	# ------------------------------------------------------------------
	# Widget change callbacks
	# ------------------------------------------------------------------

	#============================================
	def _on_atom_symbol_changed(self) -> None:
		"""Submit the edited symbol through the bound atom patch route."""
		if self._updating:
			return
		if not isinstance(
			self._current_item,
			bkchem_qt.canvas.items.atom_item.AtomItem,
		):
			return
		new_symbol = self._atom_symbol_edit.text().strip()
		if not new_symbol:
			return
		if self._submit_atom_patch((("element", new_symbol),)):
			return
		self._push_property_change(
			self._current_item.atom_model, "symbol", new_symbol, "Change Atom Symbol",
		)

	#============================================
	def _on_atom_charge_changed(self, value: int) -> None:
		"""Submit the edited charge through the bound atom patch route.

		Args:
			value: New charge value from the spin box.
		"""
		if self._updating:
			return
		if not isinstance(
			self._current_item,
			bkchem_qt.canvas.items.atom_item.AtomItem,
		):
			return
		if self._submit_atom_patch((("charge", value),)):
			return
		self._push_property_change(
			self._current_item.atom_model, "charge", value, "Change Atom Charge",
		)

	#============================================
	def _on_atom_show_changed(self, state: int) -> None:
		"""Submit the show/hide toggle through the bound atom patch route.

		Args:
			state: Qt check state integer.
		"""
		if self._updating:
			return
		if not isinstance(
			self._current_item,
			bkchem_qt.canvas.items.atom_item.AtomItem,
		):
			return
		checked = state == PySide6.QtCore.Qt.CheckState.Checked.value
		if self._submit_atom_patch((("show", checked),)):
			return
		self._push_property_change(
			self._current_item.atom_model, "show", checked, "Change Atom Label",
		)

	#============================================
	def _submit_atom_patch(self, changes: tuple[tuple[str, object], ...]) -> bool:
		"""Submit dock atom intent through the currently bound session callback.

		A synchronized dock always consumes the interaction: the target is either
		a durable direct atom submitted to OASA or an inert stale projection.  The
		Qt undo fallback remains solely for an isolated document with no callback.
		"""
		if not callable(self._atom_properties_capture):
			return False
		if not isinstance(self._current_item, bkchem_qt.canvas.items.atom_item.AtomItem):
			return True
		if self._document is None:
			return True
		model = self._current_item.atom_model
		atom_id = getattr(model, "backend_durable_id", None)
		molecule = next(
			(molecule for molecule in self._document.molecules if model in molecule.atoms),
			None,
		)
		molecule_id = getattr(molecule, "mol_id", None)
		if (
			not isinstance(molecule_id, str) or not molecule_id
			or not isinstance(atom_id, str) or not atom_id
		):
			return True
		captured = self._atom_properties_capture(molecule_id, atom_id)
		if (
			captured is None or type(captured) is not tuple or len(captured) != 2
			or type(captured[0]) is not int or not callable(captured[1])
		):
			self.update_from_selection()
			return True
		expected_revision, submit = captured
		outcome = submit(expected_revision, molecule_id, atom_id, changes)
		if getattr(outcome, "status", None) != "accepted":
			self.update_from_selection()
		return True

	#============================================
	def _on_bond_order_changed(self, index: int) -> None:
		"""Apply the edited order to the selected bond model.

		Args:
			index: New combo box index.
		"""
		if self._updating:
			return
		if not isinstance(
			self._current_item,
			bkchem_qt.canvas.items.bond_item.BondItem,
		):
			return
		order = self._bond_order_combo.itemData(index)
		if order is not None:
			if self._submit_bond_patch((("order", order),)):
				return
			self._push_property_change(
				self._current_item.bond_model, "order", order, "Change Bond Order",
			)

	#============================================
	def _on_bond_type_changed(self, index: int) -> None:
		"""Apply the edited type to the selected bond model.

		Args:
			index: New combo box index.
		"""
		if self._updating:
			return
		if not isinstance(
			self._current_item,
			bkchem_qt.canvas.items.bond_item.BondItem,
		):
			return
		bond_type = self._bond_type_combo.itemData(index)
		if bond_type is not None:
			if self._submit_bond_patch((("type", bond_type),)):
				return
			self._push_property_change(
				self._current_item.bond_model, "type", bond_type, "Change Bond Type",
			)

	#============================================
	def _submit_bond_patch(self, changes: tuple[tuple[str, object], ...]) -> bool:
		"""Submit dock bond intent through the currently bound session callback."""
		if not callable(self._bond_properties_capture):
			return False
		if not isinstance(self._current_item, bkchem_qt.canvas.items.bond_item.BondItem):
			return True
		model = self._current_item.bond_model
		bond_id = getattr(model, "backend_durable_id", None)
		molecule = next(
			(molecule for molecule in self._document.molecules if model in molecule.bonds),
			None,
		)
		molecule_id = getattr(molecule, "mol_id", None)
		if (
			not isinstance(molecule_id, str) or not molecule_id
			or not isinstance(bond_id, str) or not bond_id
		):
			return True
		captured = self._bond_properties_capture(molecule_id, bond_id)
		if (
			captured is None or type(captured) is not tuple or len(captured) != 2
			or type(captured[0]) is not int or not callable(captured[1])
		):
			self.update_from_selection()
			return True
		expected_revision, submit = captured
		outcome = submit(expected_revision, molecule_id, bond_id, changes)
		if getattr(outcome, "status", None) != "accepted":
			self.update_from_selection()
		return True

	#============================================
	def _push_property_change(self, model: object, property_name: str, new_value: object,
						text: str) -> None:
		"""Push one meaningful model mutation onto the document undo stack.

		Args:
			model: AtomModel or BondModel receiving the change.
			property_name: Name of the editable model property.
			new_value: Requested property value from the dock widget.
			text: User-facing undo command description.
		"""
		old_value = getattr(model, property_name)
		if new_value == old_value:
			return
		command = bkchem_qt.undo.commands.ChangePropertyCommand(
			model, property_name, old_value, new_value, text,
		)
		self._document.undo_stack.push(command)
