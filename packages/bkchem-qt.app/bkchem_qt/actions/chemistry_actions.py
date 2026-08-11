"""Chemistry menu action registrations for BKChem-Qt."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.bridge.insertion_placement
import bkchem_qt.bridge.chemistry_preparation
import bkchem_qt.bridge.oasa_bridge
import bkchem_qt.actions.identifier_actions
import bkchem_qt.dialogs.molecule_info_dialog
import bkchem_qt.models.fragment_model
import bkchem_qt.models.document_session
import bkchem_qt.undo.commands
from bkchem_qt.actions.action_registry import MenuAction


# Legacy linear-form fragments use this compact display spacing in scene units.
_LINEAR_FORM_BOND_LENGTH = 10.0
_LINEAR_FORM_PROPERTY_TYPE = "IntType"
_LINEAR_FORM_LABEL_PADDING = 2.0


#============================================
def _chemistry_info(app: object) -> None:
	"""Display exact OASA chemistry facts for selected authoritative molecules."""
	session = _active_smiles_document_session(app)
	if session is None:
		PySide6.QtWidgets.QMessageBox.warning(
			app, "Molecule Information",
			"Molecule information requires an active synchronized document session.",
		)
		return
	if not session.can_write_authoritative_snapshot:
		PySide6.QtWidgets.QMessageBox.warning(
			app, "Molecule Information",
			"Molecule information is unavailable until the document projection recovers.",
		)
		return
	molecule_ids = session.document.selected_direct_root_molecule_ids
	if not molecule_ids:
		PySide6.QtWidgets.QMessageBox.information(
			app, "Molecule Information",
			"Select one or more molecules without artwork, then choose Chemistry > Info.",
		)
		return
	response = bkchem_qt.bridge.oasa_bridge.query_molecule_summary(
		session, session.backend_snapshot.revision, molecule_ids,
	)
	if response.failure is not None:
		message = response.failure.message
		if response.failure.kind == "revision-conflict":
			message = "The document changed before calculation. Try again.\n\n" + message
		elif response.failure.kind == "projection-unavailable":
			message = "The document projection is unavailable. Recover it and try again."
		else:
			message = "OASA could not calculate the selected molecule information.\n\n" + message
		PySide6.QtWidgets.QMessageBox.warning(
			app, "Molecule Information", message,
		)
		return
	if response.value is None:
		PySide6.QtWidgets.QMessageBox.warning(
			app, "Molecule Information", "OASA returned no molecule information.",
		)
		return
	dialog = bkchem_qt.dialogs.molecule_info_dialog.MoleculeInfoDialog(
		response.value, app,
	)
	dialog.exec()


#============================================
def _chemistry_check(app: object) -> None:
	"""Check selected molecules for valency violations.

	For each selected molecule, checks each atom's free_valency.
	Reports any atoms with free_valency < 0 in a QMessageBox.

	Args:
		app: MainWindow instance.
	"""
	session = _active_smiles_document_session(app)
	if session is not None:
		if not session.can_write_authoritative_snapshot:
			PySide6.QtWidgets.QMessageBox.warning(
				app, "Check Chemistry",
				"Chemistry check is unavailable until the document projection recovers.",
			)
			return
		_selected_chemistry_check(app, session)
		return
	mols = app.document.selected_mols
	if not mols:
		PySide6.QtWidgets.QMessageBox.information(
			app, "Check Chemistry", "No molecules selected."
		)
		return
	# check each atom in each molecule
	problems = []
	for mol in mols:
		chemistry = bkchem_qt.bridge.oasa_bridge.standalone_atom_chemistry(mol)
		for atom_model in mol.atoms:
			free_val, _oxidation_number = chemistry[id(atom_model)]
			if free_val < 0:
				msg = (
					f"Atom {atom_model.symbol} "
					f"(charge={atom_model.charge}): "
					f"free valency = {free_val}"
				)
				problems.append(msg)
	if problems:
		result_text = "Valency violations found:\n\n" + "\n".join(problems)
	else:
		result_text = "All atoms pass valency check."
	PySide6.QtWidgets.QMessageBox.information(
		app, "Check Chemistry", result_text
	)


#============================================
def _selected_chemistry_check(app: object, session: object) -> None:
	"""Render one synchronized complete-graph valency observation."""
	molecule_ids = session.document.selected_direct_root_molecule_ids
	if not molecule_ids:
		PySide6.QtWidgets.QMessageBox.information(
			app, "Check Chemistry", "No molecules selected.",
		)
		return
	response = bkchem_qt.bridge.oasa_bridge.observe_atom_chemistry_facts(
		session, session.backend_snapshot.revision,
	)
	if response.failure is not None:
		message = response.failure.message
		if response.failure.kind == "revision-conflict":
			message = "Document changed; try again.\n%s" % message
		PySide6.QtWidgets.QMessageBox.warning(app, "Check Chemistry", message)
		return
	observation = response.value
	if observation is None:
		return
	selected = set(molecule_ids)
	problems = [
		"Atom %s: free valency = %d" % (_atom_chemistry_display_label(record), record.free_valency)
		for record in observation.records
		if record.molecule_id in selected and record.disposition == "usable"
		and record.free_valency is not None and record.free_valency < 0
	]
	unavailable = [record for record in observation.records
		if record.molecule_id in selected and record.disposition != "usable"]
	if problems:
		text = "Valency violations found:\n\n" + "\n".join(problems)
	elif unavailable:
		text = "Chemistry check is unavailable for one or more selected atoms."
	else:
		text = "All selected atoms pass the OASA complete-graph valency check."
	PySide6.QtWidgets.QMessageBox.information(app, "Check Chemistry", text)


#============================================
def _expand_groups(app: object) -> None:
	"""Expand one current implicit group through the owning backend session."""
	session = _active_smiles_document_session(app)
	document = getattr(app, "document", None)
	if session is None or not session.can_write_authoritative_snapshot or document is None:
		return
	groups = tuple(document.selected_groups)
	if len(groups) != 1:
		return
	item = groups[0]
	model = getattr(item, "group_model", None)
	molecule = model.parent() if model is not None else None
	if (
		not document.is_current_projection_item(item)
		or model is None
		or not model.implicit_expandable
		or type(model.group_id) is not str or not model.group_id
		or molecule not in document.molecules
		or type(getattr(molecule, "mol_id", None)) is not str or not molecule.mol_id
	):
		return
	expected_revision = session.backend_snapshot.revision
	molecule_id = molecule.mol_id
	group_id = model.group_id
	submit = session.submit_implicit_group_expand
	del groups
	del item
	del model
	del molecule
	del document
	outcome = submit(expected_revision, molecule_id, group_id)
	if outcome.status != "accepted":
		PySide6.QtWidgets.QMessageBox.warning(app, "Expand Group", outcome.message)


#============================================
def _int_to_roman_oxidation(n: int) -> str:
	"""Convert an integer to a signed Roman numeral oxidation state string.

	Standard chemistry convention: +III, -II, 0, etc.

	Args:
		n: Integer oxidation number.

	Returns:
		Signed Roman numeral string (e.g. -2 -> '-II', +3 -> '+III', 0 -> '0').
	"""
	if n == 0:
		return "0"
	# build the roman numeral from the absolute value
	abs_n = abs(n)
	roman_pairs = [
		(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
		(100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
		(10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
	]
	parts = []
	for value, numeral in roman_pairs:
		while abs_n >= value:
			parts.append(numeral)
			abs_n -= value
	sign = "+" if n > 0 else "-"
	roman_str = sign + "".join(parts)
	return roman_str


#============================================
def _atom_chemistry_display_label(record: object) -> str:
	"""Return a plain backend-owned label without consulting Qt atom state."""
	symbol = record.symbol or "atom"
	identifier = record.atom_id or "unnamed"
	label = "%s (%s)" % (symbol, identifier)
	if record.charge is not None and record.charge != 0:
		label += ", charge=%+d" % record.charge
	return label


#============================================
def _oxidation_number(app: object) -> None:
	"""Compute and display oxidation numbers for atoms in selected molecules.

	For each selected molecule, iterates atoms and computes the oxidation
	number via the OASA electronegativity-based algorithm. Results are
	displayed in a QMessageBox with per-molecule headings.

	Args:
		app: MainWindow instance.
	"""
	session = _active_smiles_document_session(app)
	if session is not None:
		if not session.can_write_authoritative_snapshot:
			PySide6.QtWidgets.QMessageBox.warning(
				app, "Oxidation Number",
				"Oxidation results are unavailable until the document projection recovers.",
			)
			return
		_selected_oxidation_number(app, session)
		return
	mols = app.document.selected_mols
	if not mols:
		PySide6.QtWidgets.QMessageBox.information(
			app, "Oxidation Number", "No molecules selected."
		)
		return
	# build result text for each molecule
	lines = []
	for idx, mol in enumerate(mols, start=1):
		mol_name = mol.name if mol.name else f"Molecule {idx}"
		lines.append(f"--- {mol_name} ---")
		chemistry = bkchem_qt.bridge.oasa_bridge.standalone_atom_chemistry(mol)
		for atom_model in mol.atoms:
			_free_valency, ox_num = chemistry[id(atom_model)]
			roman = _int_to_roman_oxidation(ox_num)
			lines.append(f"  {atom_model.symbol}: {roman}")
		lines.append("")
	result_text = "\n".join(lines)
	PySide6.QtWidgets.QMessageBox.information(
		app, "Oxidation Number", result_text
	)


#============================================
def _selected_oxidation_number(app: object, session: object) -> None:
	"""Render one synchronized OASA-derived oxidation observation."""
	molecule_ids = session.document.selected_direct_root_molecule_ids
	if not molecule_ids:
		PySide6.QtWidgets.QMessageBox.information(
			app, "Oxidation Number", "No molecules selected.",
		)
		return
	response = bkchem_qt.bridge.oasa_bridge.observe_atom_chemistry_facts(
		session, session.backend_snapshot.revision,
	)
	if response.failure is not None:
		message = response.failure.message
		if response.failure.kind == "revision-conflict":
			message = "Document changed; try again.\n%s" % message
		PySide6.QtWidgets.QMessageBox.warning(app, "Oxidation Number", message)
		return
	observation = response.value
	if observation is None:
		return
	selected = set(molecule_ids)
	lines = ["OASA-derived electronegativity results (not universal formal assignments):"]
	for record in observation.records:
		if record.molecule_id not in selected or record.disposition != "usable":
			continue
		if record.oxidation_number is not None:
			lines.append("  %s: %s" % (
				_atom_chemistry_display_label(record), _int_to_roman_oxidation(record.oxidation_number),
			))
	if len(lines) == 1:
		lines.append("  No selected atoms have an available complete-graph result.")
	PySide6.QtWidgets.QMessageBox.information(
		app, "Oxidation Number", "\n".join(lines),
	)


#============================================
def _read_smiles(app: object) -> None:
	"""Prompt for a SMILES string and import as a molecule.

	Parses the SMILES via OASA, generates 2D coordinates, converts
	to a MoleculeModel, and adds it to the scene.

	Args:
		app: MainWindow instance.
	"""
	text, ok = PySide6.QtWidgets.QInputDialog.getText(
		app, "Import SMILES", "Enter SMILES string:"
	)
	if not ok or not text.strip():
		return
	smiles_string = text.strip()
	_start_text_import(
		app,
		"smiles",
		smiles_string,
		"SMILES",
		"Imported SMILES molecule",
		_show_smiles_import_error,
	)


#============================================
class _MoleculeInsertionResultRelay(PySide6.QtCore.QObject):
	"""Deliver one plain molecule proposal only to its live source tab."""

	#============================================
	def __init__(
			self, target: object, worker: PySide6.QtCore.QThread,
			delivery: "MoleculeInsertionDelivery",
			) -> None:
		"""Retain frontend lifecycle facts until the worker has stopped."""
		super().__init__(delivery.app)
		self._target = target
		self._worker = worker
		self._delivery = delivery

	#============================================
	@PySide6.QtCore.Slot(object)
	def on_result(self, prepared: object) -> None:
		"""Submit one immutable proposal through the public session operation seam."""
		self._delivery.deliver(prepared)

	#============================================
	@PySide6.QtCore.Slot(object)
	def on_error(self, message: object) -> None:
		"""Show preparation failure only while the source request remains current."""
		self._delivery.report_error(message)

	#============================================
	@PySide6.QtCore.Slot()
	def on_thread_finished(self) -> None:
		"""Release through the window's terminal-safe worker owner."""
		self._delivery.app._release_import_worker(self._worker)
		self.deleteLater()


#============================================
def _start_text_import(
		app: object, codec_name: str, source_text: str, source_label: str,
		success_message: str, error_handler: object,
		) -> None:
	"""Start one backend-authoritative text molecule insertion.

	The source tab, revision, and scalar placement are captured before worker
	startup.  The worker returns a frozen CDML proposal; delivery can therefore
	commit only through the session's authoritative molecule-insertion route.
	"""
	target = app._active_session
	try:
		target_mean_bond_length, insertion_anchor = (
			bkchem_qt.bridge.insertion_placement.capture_insertion_placement(target)
		)
	except ValueError as error:
		error_handler(app, error)
		return
	request_token = target.begin_import_request()
	expected_revision = target.backend_snapshot.revision
	token_stem = "%s-r%s-i%s" % (codec_name, expected_revision, request_token)
	worker = bkchem_qt.bridge.chemistry_preparation.create_text_molecule_insertion_worker(
		codec_name, source_text, expected_revision, token_stem,
		target_mean_bond_length, insertion_anchor, success_message,
	)
	delivery = MoleculeInsertionDelivery(
		app, target, request_token, expected_revision, source_label,
		success_message, error_handler,
	)
	relay = _MoleculeInsertionResultRelay(target, worker, delivery)
	worker._result_relay = relay
	connection_type = PySide6.QtCore.Qt.ConnectionType.QueuedConnection
	worker.result.connect(relay.on_result, connection_type)
	worker.error.connect(relay.on_error, connection_type)
	worker.finished.connect(relay.on_thread_finished, connection_type)
	target.track_import_worker(worker)
	app.statusBar().showMessage("Loading %s..." % source_label, 0)
	worker.start()


#============================================
class MoleculeInsertionDelivery:
	"""Deliver one text-derived proposal to its captured backend session.

	This frontend-local controller owns the source-tab fence and user feedback.
	It delegates request construction to the named bridge and exposes only
	persistent-operation outcomes, never backend handles or OASA graph objects.
	"""

	#============================================
	def __init__(
			self, app: object, target: object, request_token: int,
			expected_revision: int, source_label: str, success_message: str,
			error_handler: object,
			) -> None:
		"""Capture one source tab and immutable preparation generation."""
		self.app = app
		self._target = target
		self._request_token = request_token
		self._expected_revision = expected_revision
		self._source_label = source_label
		self._success_message = success_message
		self._error_handler = error_handler

	#============================================
	def is_current(self) -> bool:
		"""Return whether this request may still affect its source tab."""
		return (
			self._target in self.app.sessions
			and self._target.import_request_is_current(self._request_token)
		)

	#============================================
	def _discarded_outcome(
			self, message: str,
			) -> bkchem_qt.models.document_session.PersistentActionOutcome:
		"""Return a uniform inert result for a stale source request."""
		return bkchem_qt.models.document_session.PersistentActionOutcome(
			"discarded", message, None, False,
		)

	#============================================
	def deliver(
			self, prepared: object,
			) -> bkchem_qt.models.document_session.PersistentActionOutcome:
		"""Submit one current plain proposal through the persistent action seam."""
		if not self.is_current():
			return self._discarded_outcome(
				"%s import request is no longer current" % self._source_label,
			)
		proposal = bkchem_qt.bridge.chemistry_preparation.molecule_insertion_proposal(
			prepared,
		)
		if proposal is None:
			message = "%s preparation returned invalid data" % self._source_label
			self._error_handler(self.app, message)
			return bkchem_qt.models.document_session.PersistentActionOutcome(
				"rejected", message, None, False,
			)
		if proposal.expected_revision != self._expected_revision:
			message = "%s preparation revision changed" % self._source_label
			self._error_handler(self.app, message)
			return bkchem_qt.models.document_session.PersistentActionOutcome(
				"rejected", message, None, False,
			)
		request = bkchem_qt.bridge.chemistry_preparation.build_molecule_insertion_request(
			proposal, self._success_message,
		)
		outcome = self._target.submit_persistent_operation(request)
		if outcome.status == "accepted":
			self.app.statusBar().showMessage(outcome.message, 3000)
		elif outcome.submitted:
			self.app.statusBar().showMessage(outcome.message, 5000)
		elif outcome.status == "rejected":
			self._error_handler(self.app, outcome.message)
		return outcome

	#============================================
	def report_error(self, message: object) -> bool:
		"""Show one worker error only while its source request remains current."""
		if not self.is_current():
			return False
		self._error_handler(self.app, message)
		return True


#============================================
def _show_smiles_import_error(app: object, message: object) -> None:
	"""Report a current worker failure through the SMILES dialog vocabulary."""
	PySide6.QtWidgets.QMessageBox.warning(
		app, "SMILES Error", f"Failed to parse SMILES:\n{message}",
	)


#============================================
def _show_inchi_import_error(app: object, message: object) -> None:
	"""Report an InChI preparation error with the legacy dialog vocabulary."""
	stage, detail = _text_import_error_stage(message)
	if stage == "coordinates":
		title = "Coordinate Error"
		body = "Failed to generate coordinates:\n%s" % detail
	else:
		title = "InChI Error"
		body = "Failed to parse InChI:\n%s" % detail
	PySide6.QtWidgets.QMessageBox.warning(app, title, body)


#============================================
def _show_peptide_import_error(app: object, message: object) -> None:
	"""Report peptide preparation errors with parser-specific labels."""
	stage, detail = _text_import_error_stage(message)
	if stage == "coordinates":
		title = "Coordinate Error"
		body = "Failed to generate coordinates:\n%s" % detail
	elif stage == "peptide-smiles":
		title = "SMILES Error"
		body = "Failed to parse peptide SMILES:\n%s" % detail
	elif stage == "peptide":
		title = "Peptide Sequence Error"
		body = "Failed to convert peptide sequence:\n%s" % detail
	elif stage == "peptide-validation":
		title = "Peptide Sequence Error"
		body = detail
	else:
		title = "Peptide Sequence Error"
		body = "Failed to import peptide sequence:\n%s" % detail
	PySide6.QtWidgets.QMessageBox.warning(app, title, body)


#============================================
def _text_import_error_stage(message: object) -> tuple[str, str]:
	"""Recover a preparation stage carried by a worker exception string."""
	facts = bkchem_qt.bridge.chemistry_preparation.text_import_failure_facts(message)
	return facts.stage, facts.message


#============================================
def _read_inchi(app: object) -> None:
	"""Prompt for an InChI string and import as a molecule.

	Parses the InChI via OASA, generates 2D coordinates, converts
	to a MoleculeModel, and adds it to the scene.

	Args:
		app: MainWindow instance.
	"""
	text, ok = PySide6.QtWidgets.QInputDialog.getText(
		app, "Import InChI", "Enter InChI string:"
	)
	if not ok or not text.strip():
		return
	_start_text_import(
		app,
		"inchi",
		text.strip(),
		"InChI",
		"Imported InChI molecule",
		_show_inchi_import_error,
	)


#============================================
def _read_peptide(app: object) -> None:
	"""Prompt for a peptide sequence and import as a molecule.

	Validates single-letter amino acid codes, converts the sequence
	to SMILES via OASA, generates 2D coordinates, converts to a
	MoleculeModel, and adds it to the scene.

	Args:
		app: MainWindow instance.
	"""
	# build prompt listing supported amino acid codes
	supported = bkchem_qt.bridge.chemistry_preparation.supported_peptide_codes()
	supported_str = ", ".join(supported)
	prompt_text = (
		"Enter a single-letter amino acid sequence (e.g. ANKLE):\n"
		f"Supported: {supported_str}"
	)
	text, ok = PySide6.QtWidgets.QInputDialog.getText(
		app, "Import Peptide Sequence", prompt_text
	)
	if not ok or not text.strip():
		return
	# Normalization is UI-only; validation, conversion, parsing, and layout run
	# together in the session-owned OASA worker.
	sequence = text.strip().upper()
	_start_text_import(
		app,
		"peptide",
		sequence,
		"Peptide Sequence",
		f"Imported peptide sequence '{sequence}'",
		_show_peptide_import_error,
	)


#============================================
def _active_smiles_document_session(app: object) -> object | None:
	"""Return the live registered session that owns the active projection."""
	session = getattr(app, "_active_session", None)
	document = getattr(app, "document", None)
	scene = getattr(app, "scene", None)
	view = getattr(app, "view", None)
	sessions = getattr(app, "sessions", ())
	if session is None or document is None or scene is None or view is None:
		return None
	if session.is_disposed or session not in sessions:
		return None
	if (
		session.document is not document
		or session.scene is not scene
		or session.view is not view
	):
		return None
	return session


#============================================
def _gen_smiles(app: object) -> None:
	"""Retain the established test and extension seam for SMILES export."""
	bkchem_qt.actions.identifier_actions._gen_smiles(app)


#============================================
def _set_name(app: object) -> None:
	"""Set one selected direct-root molecule name through its backend session."""
	session = _active_smiles_document_session(app)
	if session is None or not session.can_write_authoritative_snapshot:
		PySide6.QtWidgets.QMessageBox.warning(
			app, "Set Molecule Name",
			"Set molecule name requires an active synchronized document session.",
		)
		return
	molecule_ids = session.document.selected_direct_root_molecule_ids
	if len(molecule_ids) != 1:
		PySide6.QtWidgets.QMessageBox.warning(
			app, "Set Molecule Name", "Please select exactly one molecule.",
		)
		return
	molecule_id = molecule_ids[0]
	mol = next(
		(molecule for molecule in session.document.molecules if molecule.mol_id == molecule_id),
		None,
	)
	if mol is None:
		PySide6.QtWidgets.QMessageBox.warning(
			app, "Set Molecule Name", "Selected molecule is unavailable in this projection.",
		)
		return
	current_name = mol.name or ""
	new_name, ok = PySide6.QtWidgets.QInputDialog.getText(
		app, "Set Molecule Name", "Molecule name:",
		text=current_name
	)
	if not ok:
		return
	snapshot = session.backend_snapshot
	request = bkchem_qt.models.document_session.build_molecule_name_request(
		snapshot.revision, molecule_id, new_name,
	)
	outcome = session.submit_persistent_operation(request)
	if outcome.status != "accepted":
		PySide6.QtWidgets.QMessageBox.warning(
			app, "Set Molecule Name", outcome.message,
		)


#============================================
def _ordered_fragment_selection(app: object) -> tuple[object, list[object], list[object]] | None:
	"""Resolve one selected molecule and its members in canonical model order."""
	atom_items = app.document.selected_atoms
	bond_items = app.document.selected_bonds
	selected_items = [*atom_items, *bond_items]
	molecules = {
		app.document.molecule_for_graphics_item(item)
		for item in selected_items
	}
	if not selected_items or None in molecules or len(molecules) != 1:
		PySide6.QtWidgets.QMessageBox.warning(
			app, "Create Fragment",
			"Select atoms and bonds from exactly one molecule."
		)
		return
	molecule = next(iter(molecules))
	selected_atom_models = {id(item.atom_model) for item in atom_items}
	selected_bond_models = {id(item.bond_model) for item in bond_items}
	bond_models = [
		bond_model for bond_model in molecule.bonds
		if id(bond_model) in selected_bond_models
	]
	if len(bond_models) != len(selected_bond_models):
		PySide6.QtWidgets.QMessageBox.warning(
			app, "Create Fragment", "Selected objects are unavailable in the authoritative document.",
		)
		return
	member_atom_models = set(selected_atom_models)
	for bond_model in bond_models:
		if bond_model.atom1 is not None:
			member_atom_models.add(id(bond_model.atom1))
		if bond_model.atom2 is not None:
			member_atom_models.add(id(bond_model.atom2))
	atom_models = [
		atom_model for atom_model in molecule.atoms
		if id(atom_model) in member_atom_models
	]
	if len(atom_models) != len(member_atom_models):
		PySide6.QtWidgets.QMessageBox.warning(
			app, "Create Fragment", "Selected objects are unavailable in the authoritative document.",
		)
		return
	if not atom_models:
		PySide6.QtWidgets.QMessageBox.warning(
			app, "Create Fragment", "A fragment must contain at least one atom."
		)
		return None
	return molecule, atom_models, bond_models


#============================================
def _capture_fragment_create_submit(
		app: object, origin_session: object,
		) -> tuple[int, object, str, tuple[str, ...], tuple[str, ...]] | None:
	"""Capture one synchronized fragment intent with no projection wrappers."""
	selection = _ordered_fragment_selection(app)
	if selection is None:
		return None
	molecule, atom_models, bond_models = selection
	molecule_id = molecule.mol_id
	atom_ids = tuple(
		atom_model.backend_durable_id for atom_model in atom_models
		if atom_model.backend_durable_id is not None
	)
	bond_ids = tuple(
		bond_model.backend_durable_id for bond_model in bond_models
		if bond_model.backend_durable_id is not None
	)
	if len(atom_ids) != len(atom_models) or len(bond_ids) != len(bond_models) or not molecule_id:
		PySide6.QtWidgets.QMessageBox.warning(
			app, "Create Fragment", "Selected objects are unavailable in the authoritative document.",
		)
		return None
	try:
		submit = app.persistent_operation_capability_for(origin_session)
	except ValueError:
		return None
	return origin_session.backend_snapshot.revision, submit, molecule_id, atom_ids, bond_ids


#============================================
def _create_fragment(app: object) -> None:
	"""Create durable metadata for one selected molecular subgraph.

	Args:
		app: MainWindow instance.
	"""
	origin_session = getattr(app, "_active_session", None)
	captured = None
	if origin_session is not None and origin_session.can_commit_persistent_action:
		captured = _capture_fragment_create_submit(app, origin_session)
		if captured is None:
			return
	else:
		selection = _ordered_fragment_selection(app)
		if selection is None:
			return
		molecule, atom_models, bond_models = selection
	name, accepted = PySide6.QtWidgets.QInputDialog.getText(
		app, "Create Fragment", "Fragment name:"
	)
	if not accepted or not name.strip():
		return
	fragment_type, accepted = PySide6.QtWidgets.QInputDialog.getItem(
		app, "Create Fragment", "Fragment type:",
		["explicit", "implicit"], 0, False,
	)
	if not accepted:
		return
	if captured is not None:
		origin_revision, origin_submit, molecule_id, atom_ids, bond_ids = captured
		request = bkchem_qt.models.document_session.build_fragment_create_request(
			origin_revision, molecule_id, name.strip(), fragment_type, atom_ids, bond_ids,
		)
		outcome = origin_submit(request)
		if outcome.status != "accepted":
			PySide6.QtWidgets.QMessageBox.warning(app, "Create Fragment", outcome.message)
		return
	atom_id_changes, bond_id_changes = app.document.planned_fragment_id_changes(
		molecule,
	)
	fragment = bkchem_qt.models.fragment_model.FragmentModel(
		fragment_id=app.document.unique_cdml_id("fragment"),
		fragment_type=fragment_type,
		name=name.strip(),
		atom_ids=tuple(
			after_id for atom_model, _before_id, after_id in atom_id_changes
			if atom_model in atom_models
		),
		bond_ids=tuple(
			after_id for bond_model, _before_id, after_id in bond_id_changes
			if bond_model in bond_models
		),
	)
	app.document.undo_stack.push(bkchem_qt.undo.commands.AddFragmentCommand(
		molecule, fragment, atom_id_changes, bond_id_changes,
	))


#============================================
def _fragment_choices(app: object) -> tuple[list[tuple[str, str, str, int]], list[str]]:
	"""Read current fragment labels into plain durable dialog data."""
	choices = []
	raw_entries = []
	for molecule_position, molecule in enumerate(app.document.molecules, start=1):
		molecule_label = molecule.name or molecule.mol_id or "Molecule %d" % molecule_position
		for fragment in molecule.fragments:
			label = "%s: %s [%s; %s]" % (
				molecule_label, fragment.name or "unnamed", fragment.fragment_type,
				fragment.fragment_id,
			)
			choices.append((label, molecule.mol_id, fragment.fragment_id, molecule_position - 1))
		for notice in molecule.fragment_notices:
			raw_entries.append("%s: %s" % (molecule_label, notice))
		if molecule.unsupported_fragment_xml:
			raw_entries.append("%s: imported fragment metadata is read-only." % molecule_label)
	return choices, raw_entries


#============================================
def _view_fragments(app: object) -> None:
	"""Display one molecule's fragments and delete editable metadata on request.

	Args:
		app: MainWindow instance.
	"""
	choices, raw_entries = _fragment_choices(app)
	if not choices:
		message = "No editable fragments are defined."
		if raw_entries:
			message += "\n\nRetained imported fragments are read-only:\n%s" % (
				"\n".join(raw_entries),
			)
		PySide6.QtWidgets.QMessageBox.information(app, "View Fragments", message)
		return
	origin_session = getattr(app, "_active_session", None)
	origin_revision = None
	origin_submit = None
	if origin_session is not None and origin_session.can_commit_persistent_action:
		origin_revision = origin_session.backend_snapshot.revision
		try:
			origin_submit = app.persistent_operation_capability_for(origin_session)
		except ValueError:
			return
	choice_map = {
		label: (molecule_id, fragment_id, molecule_position)
		for label, molecule_id, fragment_id, molecule_position in choices
	}
	labels = ["Keep fragments unchanged", *choice_map]
	prompt = "Choose a fragment to delete:"
	if raw_entries:
		prompt += "\n\nRead-only imported fragments:\n%s" % "\n".join(raw_entries)
	choice, accepted = PySide6.QtWidgets.QInputDialog.getItem(
		app, "View Fragments", prompt, labels, 0, False,
	)
	if not accepted or choice == labels[0]:
		return
	molecule_id, fragment_id, molecule_position = choice_map[choice]
	if origin_submit is not None and origin_revision is not None:
		if not molecule_id:
			PySide6.QtWidgets.QMessageBox.warning(
				app, "View Fragments", "The selected molecule is unavailable in the authoritative document.",
			)
			return
		request = bkchem_qt.models.document_session.build_fragment_delete_request(
			origin_revision, molecule_id, fragment_id,
		)
		outcome = origin_submit(request)
		if outcome.status != "accepted":
			PySide6.QtWidgets.QMessageBox.warning(app, "View Fragments", outcome.message)
		return
	if not 0 <= molecule_position < len(app.document.molecules):
		return
	molecule = app.document.molecules[molecule_position]
	if (
			molecule.mol_id != molecule_id
			or not any(fragment.fragment_id == fragment_id for fragment in molecule.fragments)
		):
		return
	app.document.undo_stack.push(bkchem_qt.undo.commands.RemoveFragmentCommand(
		molecule, fragment_id,
	))


#============================================
def _capture_linear_form_submit(
		app: object, origin_session: object,
		) -> tuple[int, object, str, tuple[str, ...]] | None:
	"""Capture one origin-bound linear-form intent without retaining Qt wrappers."""
	atom_items = tuple(app.document.selected_atoms)
	bond_items = tuple(app.document.selected_bonds)
	items = (*atom_items, *bond_items)
	molecules = {
		app.document.molecule_for_graphics_item(item)
		for item in items
	}
	if not items or None in molecules or len(molecules) != 1:
		_linear_warning(app, "Select atoms and bonds from exactly one molecule.")
		return None
	molecule = next(iter(molecules))
	selected_models = {item.atom_model for item in atom_items}
	for item in bond_items:
		if item.bond_model.atom1 is not None:
			selected_models.add(item.bond_model.atom1)
		if item.bond_model.atom2 is not None:
			selected_models.add(item.bond_model.atom2)
	atom_ids = tuple(
		atom.backend_durable_id for atom in molecule.atoms
		if atom in selected_models and atom.backend_durable_id is not None
	)
	if not molecule.mol_id or len(atom_ids) != len(selected_models):
		_linear_warning(app, "Selected atoms are unavailable in the authoritative document.")
		return None
	try:
		submit = app.persistent_operation_capability_for(origin_session)
	except ValueError:
		return None
	return origin_session.backend_snapshot.revision, submit, molecule.mol_id, atom_ids


#============================================
def _convert_to_linear(app: object) -> None:
	"""Convert one selected unbranched component into a linear fragment.

	The legacy action records a ``linear_form`` fragment rather than replacing
	the molecular graph.  Qt keeps that contract, but computes every affected
	coordinate before it pushes a macro so an invalid selection cannot leave a
	partly moved molecule behind.

	Args:
		app: MainWindow instance.
	"""
	origin_session = getattr(app, "_active_session", None)
	if origin_session is not None:
		if not origin_session.can_commit_persistent_action:
			_linear_warning(app, "Document cannot accept a persistent edit.")
			return
		captured = _capture_linear_form_submit(app, origin_session)
		if captured is None:
			return
		origin_revision, submit, molecule_id, atom_ids = captured
		request = bkchem_qt.models.document_session.build_linear_form_convert_request(
			origin_revision, molecule_id, atom_ids,
		)
		outcome = submit(request)
		if outcome.status != "accepted":
			_linear_warning(app, outcome.message)
		return
	selection = _linear_selection(app)
	if selection is None:
		return
	molecule, path, path_bonds = selection
	coordinate_plan = _linear_coordinate_changes(molecule, path, path_bonds)
	if coordinate_plan is None:
		_linear_warning(
			app, "The selected chain has an external component attached to more than one selected atom.",
		)
		return
	atom_changes, bond_length = coordinate_plan
	atom_id_changes, bond_id_changes = app.document.planned_fragment_id_changes(
		molecule,
	)
	if not _linear_id_normalization_is_safe(
		molecule, atom_id_changes, bond_id_changes,
	):
		_linear_warning(
			app, "This conversion would renumber atoms or bonds referenced by an existing fragment.",
		)
		return
	atom_ids = _fragment_ids_for_models(path, atom_id_changes)
	bond_ids = _fragment_ids_for_models(path_bonds, bond_id_changes)
	fragment = bkchem_qt.models.fragment_model.FragmentModel(
		fragment_id=app.document.unique_cdml_id("fragment"),
		fragment_type="linear_form",
		name="",
		atom_ids=atom_ids,
		bond_ids=bond_ids,
		properties=(bkchem_qt.models.fragment_model.FragmentProperty(
				name="bond_length", value=f"{bond_length:.6f}",
				type_name=_LINEAR_FORM_PROPERTY_TYPE,
		),),
	)
	# A macro makes geometry, explicit-hydrogen display, stable IDs, and the
	# fragment metadata one undo/redo operation and one dirty transition.
	undo_stack = app.document.undo_stack
	undo_stack.beginMacro("Convert to Linear Form")
	if atom_changes:
		undo_stack.push(bkchem_qt.undo.commands.TransformGeometryCommand(
				atom_changes, [], "Linear Form Geometry",
		))
	for atom_model in path:
		if not atom_model.show_hydrogens:
			undo_stack.push(bkchem_qt.undo.commands.ChangePropertyCommand(
					atom_model, "show_hydrogens", False, True,
					"Show Linear Form Hydrogens",
			))
	undo_stack.push(bkchem_qt.undo.commands.AddFragmentCommand(
			molecule, fragment, atom_id_changes, bond_id_changes,
			"Create Linear Form Fragment",
	))
	undo_stack.endMacro()
	app.statusBar().showMessage("Converted selection to linear form", 3000)


#============================================
def _linear_warning(app: object, message: str) -> None:
	"""Show one safe, non-mutating conversion rejection message."""
	PySide6.QtWidgets.QMessageBox.warning(app, "Convert to Linear Form", message)


#============================================
def _linear_selection(app: object) -> tuple[object, tuple[object, ...], tuple[object, ...]] | None:
	"""Return one selected path and its induced bonds, or report why not.

	Selected bonds contribute both endpoints, matching the legacy selection
	semantics.  The selected vertices must induce a single unbranched path (or
	a single atom); a ring and a fork cannot safely become a linear formula.
	"""
	atom_items = app.document.selected_atoms
	bond_items = app.document.selected_bonds
	items = [*atom_items, *bond_items]
	molecules = {
		app.document.molecule_for_graphics_item(item)
		for item in items
	}
	if not items or None in molecules or len(molecules) != 1:
		_linear_warning(app, "Select atoms and bonds from exactly one molecule.")
		return None
	molecule = next(iter(molecules))
	selected_atoms = {item.atom_model for item in atom_items}
	for item in bond_items:
		if item.bond_model.atom1 is not None:
			selected_atoms.add(item.bond_model.atom1)
		if item.bond_model.atom2 is not None:
			selected_atoms.add(item.bond_model.atom2)
	if not selected_atoms:
		_linear_warning(app, "Select at least one atom or bond to make a linear form.")
		return None
	induced_bonds = tuple(
		bond for bond in molecule.bonds
		if bond.atom1 in selected_atoms and bond.atom2 in selected_atoms
	)
	neighbors = {atom: [] for atom in selected_atoms}
	for bond in induced_bonds:
		neighbors[bond.atom1].append(bond.atom2)
		neighbors[bond.atom2].append(bond.atom1)
	if any(len(atom_neighbors) > 2 for atom_neighbors in neighbors.values()):
		_linear_warning(app, "The selection is not linear because it contains a branch.")
		return None
	path = _ordered_linear_path(neighbors)
	if path is None:
		_linear_warning(
			app, "The selected atoms must form one connected chain, not a ring or split selection.",
		)
		return None
	path_bonds = _ordered_path_bonds(path, induced_bonds)
	return molecule, path, path_bonds


#============================================
def _ordered_linear_path(neighbors: dict[object, list[object]]) -> tuple[object, ...] | None:
	"""Order a connected path from its leftmost endpoint without mutation."""
	if len(neighbors) == 1:
		path = tuple(neighbors)
		return path
	ends = [atom for atom, atom_neighbors in neighbors.items()
			if len(atom_neighbors) == 1]
	if len(ends) != 2:
		return None
	start = min(ends, key=lambda atom: (atom.x, atom.y, id(atom)))
	path = []
	previous = None
	current = start
	while current is not None:
		path.append(current)
		next_atoms = [atom for atom in neighbors[current] if atom is not previous]
		if len(next_atoms) > 1:
			return None
		previous, current = current, next_atoms[0] if next_atoms else None
	if len(path) != len(neighbors):
		return None
	return tuple(path)


#============================================
def _ordered_path_bonds(
		path: tuple[object, ...], bonds: tuple[object, ...],
		) -> tuple[object, ...]:
	"""Return path edges in the same semantic order as their vertices."""
	ordered = []
	for first, second in zip(path, path[1:]):
		for bond in bonds:
			if {bond.atom1, bond.atom2} == {first, second}:
				ordered.append(bond)
				break
		else:
			raise ValueError("linear path is missing an induced bond")
	result = tuple(ordered)
	return result


#============================================
def _linear_id_normalization_is_safe(
		molecule: object, atom_id_changes: tuple[tuple[object, str, str], ...],
		bond_id_changes: tuple[tuple[object, str, str], ...],
		) -> bool:
	"""Reject ID rewrites that could invalidate pre-existing fragment XML.

	``AddFragmentCommand`` changes atom and bond IDs atomically with the new
	fragment.  Existing editable or losslessly retained fragment metadata may
	refer to those IDs, however, so this action refuses the conversion before
	any command is pushed instead of creating dangling references.
	"""
	id_changes = [*atom_id_changes, *bond_id_changes]
	requires_rewrite = any(before != after for _model, before, after in id_changes)
	if not requires_rewrite:
		return True
	safe = not molecule.fragments and not molecule.unsupported_fragment_xml
	return safe


#============================================
def _linear_coordinate_changes(
		molecule: object, path: tuple[object, ...], path_bonds: tuple[object, ...],
		) -> tuple[list[tuple[object, tuple[float, float], tuple[float, float]]], float] | None:
	"""Plan linear-path and attached-component translations without mutation."""
	path_set = set(path)
	path_bond_set = set(path_bonds)
	start_x, start_y = path[0].x, path[0].y
	bond_length = _linear_label_safe_spacing(path)
	deltas = {
		atom: (
			start_x + index * bond_length - atom.x,
			start_y - atom.y,
		)
		for index, atom in enumerate(path)
	}
	# Every external component can follow exactly one selected anchor.  An
	# external bridge between two selected atoms has no single coherent offset.
	component_offsets: dict[object, tuple[float, float]] = {}
	visited_external = set()
	for anchor in path:
		for bond in molecule.bonds:
			if bond in path_bond_set:
				continue
			other = _other_bond_atom(bond, anchor)
			if other is None or other in path_set:
				continue
			component = _external_component(molecule, other, path_set)
			component_key = frozenset(component)
			if component_key in visited_external:
				if any(component_offsets[atom] != deltas[anchor] for atom in component):
					return None
				continue
			visited_external.add(component_key)
			for atom in component:
				component_offsets[atom] = deltas[anchor]
	changes = []
	for atom in [*path, *component_offsets]:
		before = (atom.x, atom.y)
		dx, dy = deltas[atom] if atom in path_set else component_offsets[atom]
		after = (before[0] + dx, before[1] + dy)
		if after != before:
			changes.append((atom, before, after))
	return changes, bond_length


#============================================
def _linear_label_safe_spacing(path: tuple[object, ...]) -> float:
	"""Return uniform spacing that keeps adjacent rendered atom labels apart."""
	spacing = _LINEAR_FORM_BOND_LENGTH
	for first, second in zip(path, path[1:]):
		_first_left, first_right = _linear_label_bounds(first)
		second_left, _second_right = _linear_label_bounds(second)
		required = first_right - second_left + _LINEAR_FORM_LABEL_PADDING
		if required > spacing:
			spacing = required
	return spacing


#============================================
def _linear_label_bounds(atom_model: object) -> tuple[float, float]:
	"""Measure one atom label's horizontal glyph bounds relative to its atom."""
	return bkchem_qt.bridge.oasa_bridge.legacy_atom_text_bounds(atom_model)


#============================================
def _other_bond_atom(bond: object, atom: object) -> object | None:
	"""Return the opposite endpoint when ``bond`` touches ``atom``."""
	if bond.atom1 is atom:
		return bond.atom2
	if bond.atom2 is atom:
		return bond.atom1
	return None


#============================================
def _external_component(molecule: object, start: object, selected: set[object]) -> set[object]:
	"""Return unselected atoms reachable from one selected-path attachment."""
	component = set()
	pending = [start]
	while pending:
		atom = pending.pop()
		if atom in component or atom in selected:
			continue
		component.add(atom)
		for bond in molecule.bonds:
			other = _other_bond_atom(bond, atom)
			if other is not None and other not in component and other not in selected:
				pending.append(other)
	return component


#============================================
def _fragment_ids_for_models(
		models: tuple[object, ...], id_changes: tuple[tuple[object, str, str], ...],
		) -> tuple[str, ...]:
	"""Return each selected model's planned durable CDML identifier."""
	planned_ids = {model: after for model, _before, after in id_changes}
	ids = tuple(planned_ids[model] for model in models)
	return ids


#============================================
def register_chemistry_actions(registry: object, app: object) -> None:
	"""Register all Chemistry menu actions.

	Args:
		registry: ActionRegistry instance to register actions with.
		app: The main BKChem-Qt application object providing handler methods.
	"""
	# predicates
	def has_selection() -> bool:
		"""Return True when the document has selected items."""
		return app.document is not None and app.document.has_selection

	def one_mol_selected() -> bool:
		"""Return True when exactly one molecule is selected."""
		return app.document is not None and app.document.one_mol_selected

	def one_synchronized_direct_root_molecule_selected() -> bool:
		"""Return whether a root-only molecule operation has one durable target."""
		session = _active_smiles_document_session(app)
		return bool(
			session is not None
			and session.can_write_authoritative_snapshot
			and len(session.document.selected_direct_root_molecule_ids) == 1
		)

	def synchronized_direct_root_molecules_selected() -> bool:
		"""Return whether Info has at least one authoritative molecule target."""
		session = _active_smiles_document_session(app)
		return bool(
			session is not None
			and session.can_write_authoritative_snapshot
			and session.document.selected_direct_root_molecule_ids
		)

	def groups_selected() -> bool:
		"""Return whether one current implicit group has a writable backend route."""
		session = _active_smiles_document_session(app)
		if session is None or not session.can_write_authoritative_snapshot:
			return False
		groups = tuple(app.document.selected_groups) if app.document is not None else ()
		if len(groups) != 1:
			return False
		item = groups[0]
		model = getattr(item, "group_model", None)
		molecule = model.parent() if model is not None else None
		return bool(
			app.document.is_current_projection_item(item)
			and model is not None and model.implicit_expandable
			and type(model.group_id) is str and model.group_id
			and molecule in app.document.molecules
			and type(getattr(molecule, "mol_id", None)) is str and molecule.mol_id
		)

	# display summary info on selected molecules
	registry.register(MenuAction(
		id='chemistry.info',
		label_key='Info',
		help_key='Display summary formula and other info on all selected molecules',
		accelerator=None,
		handler=lambda: _chemistry_info(app),
		enabled_when=synchronized_direct_root_molecules_selected,
	))

	# check if selected objects have chemical meaning
	registry.register(MenuAction(
		id='chemistry.check',
		label_key='Check chemistry',
		help_key='Check if the selected objects have chemical meaning',
		accelerator=None,
		handler=lambda: _chemistry_check(app),
		enabled_when=has_selection,
	))

	# expand one supported implicit group through its backend session
	registry.register(MenuAction(
		id='chemistry.expand_groups',
		label_key='Expand groups',
		help_key='Expand one selected implicit group through OASA',
		accelerator=None,
		handler=lambda: _expand_groups(app),
		enabled_when=groups_selected,
	))

	# compute and display oxidation number
	registry.register(MenuAction(
		id='chemistry.oxidation_number',
		label_key='Compute oxidation number',
		help_key='Compute and display the oxidation number of selected atoms',
		accelerator=None,
		handler=lambda: _oxidation_number(app),
		enabled_when=has_selection,
	))

	# import a SMILES string as structure
	registry.register(MenuAction(
		id='chemistry.read_smiles',
		label_key='Import SMILES',
		help_key='Import a SMILES string and convert it to structure',
		accelerator=None,
		handler=lambda: _read_smiles(app),
		enabled_when=None,
	))

	# import an InChI string as structure
	registry.register(MenuAction(
		id='chemistry.read_inchi',
		label_key='Import InChI',
		help_key='Import an InChI string and convert it to structure',
		accelerator=None,
		handler=lambda: _read_inchi(app),
		enabled_when=None,
	))

	# import a peptide amino acid sequence as structure
	registry.register(MenuAction(
		id='chemistry.read_peptide',
		label_key='Import Peptide Sequence',
		help_key='Import a peptide amino acid sequence and convert it to structure',
		accelerator=None,
		handler=lambda: _read_peptide(app),
		enabled_when=None,
	))

	# set the name of the selected molecule
	registry.register(MenuAction(
		id='chemistry.set_name',
		label_key='Set molecule name',
		help_key='Set the name of the selected molecule',
		accelerator=None,
		handler=lambda: _set_name(app),
		enabled_when=one_synchronized_direct_root_molecule_selected,
	))

	# create a fragment from the selected part of the molecule
	registry.register(MenuAction(
		id='chemistry.create_fragment',
		label_key='Create fragment',
		help_key='Create a fragment from the selected part of the molecule',
		accelerator=None,
		handler=lambda: _create_fragment(app),
		enabled_when=has_selection,
	))

	# show already defined fragments
	registry.register(MenuAction(
		id='chemistry.view_fragments',
		label_key='View fragments',
		help_key='Show already defined fragments',
		accelerator=None,
		handler=lambda: _view_fragments(app),
		enabled_when=None,
	))

	# convert selected part of chain to linear fragment
	registry.register(MenuAction(
		id='chemistry.convert_to_linear',
		label_key='Convert selection to linear form',
		help_key='Convert selected part of chain to linear fragment',
		accelerator=None,
		handler=lambda: _convert_to_linear(app),
		enabled_when=has_selection,
	))
