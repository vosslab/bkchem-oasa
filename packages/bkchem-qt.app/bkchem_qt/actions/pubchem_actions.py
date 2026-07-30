"""Explicit PubChem lookup and insertion actions for BKChem-Qt."""

# Standard Library
import dataclasses

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import oasa.coords_generator
import oasa.cdml_writer
import oasa.pubchem
import oasa.pubchem_http
import oasa.smiles_lib
import bkchem_qt.bridge.worker
import bkchem_qt.bridge.insertion_placement
import bkchem_qt.models.document_session
from bkchem_qt.actions.action_registry import MenuAction


@dataclasses.dataclass(frozen=True)
class PreparedPubChemLookup:
	"""Immutable PubChem display data plus one backend insertion proposal."""

	compound: oasa.pubchem.PubChemCompound
	insertion: bkchem_qt.bridge.worker.PreparedMoleculeInsertion


#============================================
class PubChemLookupDialog(PySide6.QtWidgets.QDialog):
	"""Look up one PubChem compound before explicitly inserting it."""

	lookup_requested = PySide6.QtCore.Signal(str, str)

	#============================================
	def __init__(self, parent: object) -> None:
		"""Build the compact lookup form and immutable result display."""
		super().__init__(parent)
		self.setWindowTitle("PubChem Lookup")
		self._closed = False
		self._prepared = None
		self._target_session = None
		self._result_session = None
		self._result_token = None
		layout = PySide6.QtWidgets.QVBoxLayout(self)
		form = PySide6.QtWidgets.QFormLayout()
		self._kind = PySide6.QtWidgets.QComboBox(self)
		self._kind.addItems(["Name", "CID", "InChI", "InChIKey"])
		self._query = PySide6.QtWidgets.QLineEdit(self)
		self._lookup_button = PySide6.QtWidgets.QPushButton("Lookup", self)
		form.addRow("Lookup by:", self._kind)
		form.addRow("Query:", self._query)
		form.addRow(self._lookup_button)
		layout.addLayout(form)
		result_form = PySide6.QtWidgets.QFormLayout()
		self._result_fields = {}
		for label, key in (
				("Name:", "name"), ("CID:", "cid"),
				("Formula:", "formula"), ("Weight:", "weight"),
				("InChIKey:", "inchikey"), ("SMILES:", "smiles"),
				):
			field = PySide6.QtWidgets.QLineEdit(self)
			field.setReadOnly(True)
			self._result_fields[key] = field
			result_form.addRow(label, field)
		layout.addLayout(result_form)
		self._status = PySide6.QtWidgets.QLabel("Enter a query to look up PubChem.", self)
		self._status.setWordWrap(True)
		layout.addWidget(self._status)
		buttons = PySide6.QtWidgets.QDialogButtonBox(parent=self)
		self._insert_button = buttons.addButton(
			"Insert", PySide6.QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole,
		)
		buttons.addButton(PySide6.QtWidgets.QDialogButtonBox.StandardButton.Close)
		self._insert_button.setEnabled(False)
		layout.addWidget(buttons)
		self._lookup_button.clicked.connect(self._request_lookup)
		self._query.returnPressed.connect(self._request_lookup)
		self._insert_button.clicked.connect(self._insert_requested)
		buttons.rejected.connect(self.close)

	#============================================
	def _request_lookup(self) -> None:
		"""Validate user input before emitting one explicit lookup request."""
		query = self._query.text().strip()
		if not query:
			self._status.setText("Enter a PubChem query.")
			return
		self._clear_result()
		self._status.setText("Looking up PubChem record...")
		self._lookup_button.setEnabled(False)
		self.lookup_requested.emit(self._kind.currentText(), query)

	#============================================
	def _insert_requested(self) -> None:
		"""Request insertion only when a valid result is available."""
		parent = self.parent()
		insert = getattr(parent, "_insert_pubchem_dialog_result", None)
		if callable(insert):
			insert(self)

	#============================================
	def _clear_result(self) -> None:
		"""Forget a prior result before a new request starts."""
		self._prepared = None
		self._result_session = None
		self._result_token = None
		self._insert_button.setEnabled(False)
		for field in self._result_fields.values():
			field.clear()

	#============================================
	@PySide6.QtCore.Slot()
	def _source_session_disposed(self) -> None:
		"""Detach a ready result when its captured document session closes."""
		self._clear_result()
		self._target_session = None
		self._status.setText("PubChem source tab is closed.")
		self._lookup_button.setEnabled(False)

	#============================================
	def set_lookup_result(
			self, prepared: PreparedPubChemLookup, session: object, token: int,
			) -> None:
		"""Display one immutable prepared result without mutating a document."""
		self._prepared = prepared
		self._result_session = session
		self._result_token = token
		compound = prepared.compound
		values = {
			"name": compound.display_name or "; ".join(compound.synonyms[:1]),
			"cid": str(compound.cid),
			"formula": compound.molecular_formula,
			"weight": "%.6g" % compound.molecular_weight,
			"inchikey": compound.inchikey,
			"smiles": compound.smiles,
		}
		for key, value in values.items():
			self._result_fields[key].setText(value)
		self._status.setText("PubChem record is ready to insert.")
		self._lookup_button.setEnabled(True)
		self._insert_button.setEnabled(bool(prepared.insertion.proposal_cdml))

	#============================================
	def set_lookup_error(self, message: object) -> None:
		"""Show a current lookup failure inline without changing the document."""
		self._clear_result()
		self._status.setText("PubChem lookup failed: %s" % message)
		self._lookup_button.setEnabled(True)

	#============================================
	def closeEvent(self, event: object) -> None:
		"""Mark late worker deliveries ineligible before Qt destroys the dialog."""
		self._closed = True
		super().closeEvent(event)


#============================================
def _prepare_pubchem_lookup(
		kind: str, query: str, transport: object, expected_revision: int,
		token_stem: str, target_mean_bond_length: float,
		insertion_anchor: tuple[float, float],
		) -> PreparedPubChemLookup:
	"""Prepare one frozen PubChem display result and molecule-only proposal."""
	if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
		raise ValueError("PubChem insertion revision must be an integer")
	lookup_by_kind = {
		"Name": oasa.pubchem.lookup_by_name,
		"CID": oasa.pubchem.lookup_by_cid,
		"InChI": oasa.pubchem.lookup_by_inchi,
		"InChIKey": oasa.pubchem.lookup_by_inchikey,
	}
	lookup = lookup_by_kind.get(kind)
	if lookup is None:
		raise ValueError("Unsupported PubChem lookup type: %s" % kind)
	if kind == "CID":
		try:
			query_value = int(query)
		except ValueError as exc:
			raise ValueError("PubChem CID must be a positive integer") from exc
	else:
		query_value = query
	compound = lookup(query_value, transport)
	molecule = oasa.smiles_lib.text_to_mol(compound.smiles)
	oasa.coords_generator.calculate_coords(molecule, bond_length=1.0, force=1)
	if molecule.is_connected():
		molecules = [molecule]
	else:
		molecules = list(molecule.get_disconnected_subgraphs())
	oasa.insertion_geometry.place_molecules_for_insertion(
		molecules, target_mean_bond_length, insertion_anchor,
	)
	proposal_cdml = oasa.cdml_writer.molecules_to_insertion_proposal(
		molecules, token_stem=token_stem,
	)
	insertion = bkchem_qt.bridge.worker.PreparedMoleculeInsertion(
		proposal_cdml, expected_revision, "Insert PubChem structure",
	)
	return PreparedPubChemLookup(compound, insertion)


#============================================
class _PubChemLookupRelay(PySide6.QtCore.QObject):
	"""Deliver one PubChem worker result safely on the GUI thread."""

	#============================================
	def __init__(
			self, app: object, dialog: PubChemLookupDialog, target: object,
			token: int, worker: PySide6.QtCore.QThread,
			) -> None:
		"""Retain source session, dialog, and worker until completion."""
		super().__init__(app)
		self._app = app
		self._dialog = dialog
		self._target = target
		self._token = token
		self._worker = worker

	#============================================
	def _is_current(self) -> bool:
		"""Return whether delivery still belongs to this live dialog and tab."""
		return (
			not self._app._shutdown_prepared
			and self._target in self._app.sessions
			and self._target.import_request_is_current(self._token)
			and not self._dialog._closed
		)

	#============================================
	@PySide6.QtCore.Slot(object)
	def on_result(self, prepared: object) -> None:
		"""Display a current immutable worker result without Qt model conversion."""
		if not self._is_current():
			return
		if (
			not isinstance(prepared, PreparedPubChemLookup)
			or not isinstance(prepared.compound, oasa.pubchem.PubChemCompound)
			):
			self._dialog.set_lookup_error("PubChem preparation returned invalid data")
			return
		if not isinstance(
				prepared.insertion, bkchem_qt.bridge.worker.PreparedMoleculeInsertion,
				):
			self._dialog.set_lookup_error("PubChem preparation returned invalid data")
			return
		self._dialog.set_lookup_result(prepared, self._target, self._token)

	#============================================
	@PySide6.QtCore.Slot(object)
	def on_error(self, message: object) -> None:
		"""Display a current worker failure inline in its originating dialog."""
		if self._is_current():
			self._dialog.set_lookup_error(message)

	#============================================
	@PySide6.QtCore.Slot()
	def on_thread_finished(self) -> None:
		"""Release through the window's terminal-safe worker owner."""
		self._app._release_import_worker(self._worker)
		self.deleteLater()


#============================================
def _create_pubchem_lookup_worker(
		app: object, dialog: PubChemLookupDialog, kind: str, query: str,
		transport: object,
		) -> PySide6.QtCore.QThread | None:
	"""Connect one explicit PubChem worker without starting its thread."""
	target = dialog._target_session
	if target is None or target not in app.sessions:
		dialog.set_lookup_error("The source document is no longer open.")
		return None
	token = target.begin_import_request()
	expected_revision = target.backend_snapshot.revision
	token_stem = "pubchem-r%s-i%s" % (expected_revision, token)
	try:
		target_mean_bond_length, insertion_anchor = (
			bkchem_qt.bridge.insertion_placement.capture_insertion_placement(target)
		)
	except ValueError as error:
		dialog.set_lookup_error(error)
		return None
	worker = bkchem_qt.bridge.worker.OasaWorker(
		_prepare_pubchem_lookup, kind, query, transport, expected_revision, token_stem,
		target_mean_bond_length, insertion_anchor,
	)
	relay = _PubChemLookupRelay(app, dialog, target, token, worker)
	worker._result_relay = relay
	connection = PySide6.QtCore.Qt.ConnectionType.QueuedConnection
	worker.result.connect(relay.on_result, connection)
	worker.error.connect(relay.on_error, connection)
	worker.finished.connect(relay.on_thread_finished, connection)
	target.track_import_worker(worker)
	return worker


#============================================
def _start_pubchem_lookup(
		app: object, dialog: PubChemLookupDialog, kind: str, query: str,
		transport: object,
		) -> PySide6.QtCore.QThread | None:
	"""Start one explicit PubChem request for its origin session and dialog."""
	worker = _create_pubchem_lookup_worker(app, dialog, kind, query, transport)
	if worker is None:
		return None
	worker.start()
	return worker


#============================================
def _insert_dialog_result(app: object, dialog: PubChemLookupDialog) -> bool:
	"""Submit one current PubChem proposal through backend authority."""
	target = dialog._target_session
	prepared = dialog._prepared
	if dialog._closed or not isinstance(prepared, PreparedPubChemLookup):
		return False
	if (
			target is None or target not in app.sessions
			or target.is_disposed
			):
		# A closed tab owns no valid document, undo stack, or Qt projection.
		dialog._clear_result()
		dialog._target_session = None
		dialog._status.setText("PubChem source tab is closed.")
		dialog._lookup_button.setEnabled(False)
		return False
	if (
			dialog._result_session is not target
			or not target.import_request_is_current(dialog._result_token)
			):
		dialog._clear_result()
		dialog._status.setText("PubChem result is stale; look it up again.")
		dialog._lookup_button.setEnabled(True)
		return False
	insertion = prepared.insertion
	if (
			not isinstance(insertion, bkchem_qt.bridge.worker.PreparedMoleculeInsertion)
			or insertion.expected_revision != target.backend_snapshot.revision
			):
		dialog._clear_result()
		dialog._status.setText("PubChem result is stale; look it up again.")
		dialog._lookup_button.setEnabled(True)
		return False
	request = bkchem_qt.models.document_session.PersistentOperationRequest(
		operation_key="molecule.insert",
		label=insertion.label or "Insert PubChem structure",
		payload=(
			("expected_revision", insertion.expected_revision),
			("proposal_cdml", insertion.proposal_cdml),
		),
		target_keys=frozenset(),
	)
	outcome = target.submit_persistent_operation(request)
	if outcome.submitted:
		# Acceptance is final even if Qt cannot project it.  Recovery may only
		# reproject the current backend snapshot, never submit this candidate again.
		dialog._clear_result()
		dialog._status.setText(outcome.message)
		return True
	if outcome.status == "rejected":
		dialog._clear_result()
		dialog._status.setText("PubChem insert failed: %s" % outcome.message)
		dialog._lookup_button.setEnabled(True)
	return False


#============================================
def open_pubchem_lookup(
		app: object, transport: object = oasa.pubchem_http.fetch_json,
		) -> PubChemLookupDialog:
	"""Show a modeless, user-initiated PubChem lookup dialog."""
	dialog = PubChemLookupDialog(app)
	dialog._target_session = app._active_session
	dialog._target_session.disposed.connect(dialog._source_session_disposed)
	dialog.lookup_requested.connect(
		lambda kind, query: _start_pubchem_lookup(
			app, dialog, kind, query, transport,
		),
	)
	app._insert_pubchem_dialog_result = lambda source: _insert_dialog_result(app, source)
	active_dialogs = getattr(app, "_pubchem_lookup_dialogs", set())
	active_dialogs.add(dialog)
	app._pubchem_lookup_dialogs = active_dialogs
	dialog.finished.connect(lambda _result: active_dialogs.discard(dialog))
	dialog.show()
	return dialog


#============================================
def register_pubchem_actions(registry: object, app: object) -> None:
	"""Register the explicit Chemistry > Lookup PubChem action."""
	registry.register(MenuAction(
		id="chemistry.lookup_pubchem",
		label_key="Lookup PubChem...",
		help_key="Look up one PubChem compound before inserting its structure",
		accelerator=None,
		handler=lambda: open_pubchem_lookup(app),
		enabled_when=None,
	))
