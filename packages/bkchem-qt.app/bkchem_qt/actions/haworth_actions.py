"""Editable Haworth sugar insertion actions for BKChem-Qt."""

# Standard Library

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import oasa.coords_generator
import oasa.cdml_writer
import oasa.haworth.layout
import oasa.haworth.verified_sucrose
import oasa.insertion_geometry
import oasa.smiles_lib
import oasa.sugar_code
import oasa.sugar_code_smiles
import bkchem_qt.bridge.worker
import bkchem_qt.bridge.insertion_placement
import bkchem_qt.models.document_session
from bkchem_qt.actions.action_registry import MenuAction


#============================================
class HaworthInsertDialog(PySide6.QtWidgets.QDialog):
	"""Collect one monosaccharide Haworth insertion request."""

	#============================================
	def __init__(self, ring_type: str, parent: object) -> None:
		"""Create a short form with the menu-selected ring type.

		Args:
			ring_type: ``pyranose`` or ``furanose`` chosen by the menu action.
			parent: Main window that owns this modal dialog.
		"""
		super().__init__(parent)
		self.setWindowTitle("Insert Haworth Sugar")
		form = PySide6.QtWidgets.QFormLayout(self)
		self._code = PySide6.QtWidgets.QLineEdit("ARLRDM", self)
		self._anomeric = PySide6.QtWidgets.QComboBox(self)
		self._anomeric.addItems(["alpha", "beta"])
		form.addRow("Sugar code:", self._code)
		form.addRow("Ring form:", PySide6.QtWidgets.QLabel(ring_type, self))
		form.addRow("Anomeric form:", self._anomeric)
		buttons = PySide6.QtWidgets.QDialogButtonBox(
			PySide6.QtWidgets.QDialogButtonBox.StandardButton.Ok
			| PySide6.QtWidgets.QDialogButtonBox.StandardButton.Cancel,
			parent=self,
		)
		buttons.accepted.connect(self.accept)
		buttons.rejected.connect(self.reject)
		form.addRow(buttons)

	#============================================
	def request(self, ring_type: str) -> tuple[str, str, str]:
		"""Return the normalized user request after dialog acceptance."""
		return (
			self._code.text().strip(), ring_type,
			self._anomeric.currentText(),
		)


#============================================
def _prepare_haworth_sugar(
		sugar_code: str, ring_type: str, anomeric: str,
		bond_length: float = 1.0,
		) -> list:
	"""Build one positioned, editable OASA sugar molecule off the GUI thread.

	The sugar code determines D/L configuration, so the dialog deliberately
	does not present a second, potentially contradictory configuration control.

	Args:
		sugar_code: Compact OASA sugar code, such as ``ARLRDM`` for D-glucose.
		ring_type: Requested ``pyranose`` or ``furanose`` projection.
		anomeric: Requested ``alpha`` or ``beta`` configuration.
		bond_length: OASA coordinate-space bond length before Qt bridge scaling.

	Returns:
		A one-item list containing an OASA molecule ready for GUI conversion.
	"""
	parsed = oasa.sugar_code.parse(sugar_code)
	series_by_config = {"DEXTER": "D", "LAEVUS": "L"}
	series = series_by_config.get(parsed.config)
	if series is None:
		raise ValueError(
			"Haworth insertion requires a D or L sugar code; got '%s'."
			% parsed.sugar_code
		)
	smiles_text = oasa.sugar_code_smiles.sugar_code_to_smiles(
		sugar_code, ring_type, anomeric,
	)
	molecule = oasa.smiles_lib.text_to_mol(smiles_text)
	oasa.coords_generator.calculate_coords(
		molecule, bond_length=bond_length, force=1,
	)
	oasa.haworth.layout.build_haworth(
		molecule,
		mode=ring_type,
		bond_length=bond_length,
		series=series,
		stereo=anomeric,
	)
	return [molecule]


#============================================
def _prepare_haworth_insertion(
		sugar_code: str, ring_type: str, anomeric: str, expected_revision: int,
		token_stem: str, bond_length_pt: float, insertion_anchor: tuple[float, float],
		) -> bkchem_qt.bridge.worker.PreparedMoleculeInsertion:
	"""Serialize one detached Haworth graph as a frozen backend proposal."""
	if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
		raise ValueError("Haworth insertion revision must be an integer")
	molecules = _prepare_haworth_sugar(sugar_code, ring_type, anomeric)
	oasa.insertion_geometry.place_molecules_for_insertion(
		molecules, bond_length_pt, insertion_anchor,
	)
	proposal_cdml = oasa.cdml_writer.molecules_to_insertion_proposal(
		molecules, token_stem=token_stem,
	)
	return bkchem_qt.bridge.worker.PreparedMoleculeInsertion(
		proposal_cdml, expected_revision, "Insert Haworth sugar",
	)


#============================================
def _prepare_verified_sucrose_insertion(
		expected_revision: int, token_stem: str, bond_length_pt: float,
		insertion_anchor: tuple[float, float],
		) -> bkchem_qt.bridge.worker.PreparedMoleculeInsertion:
	"""Serialize the one backend-owned fixed sucrose Haworth preset."""
	if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
		raise ValueError("Verified sucrose insertion revision must be an integer")
	molecule = oasa.haworth.verified_sucrose.prepare_verified_sucrose_haworth()
	oasa.insertion_geometry.place_molecules_for_insertion(
		[molecule], bond_length_pt, insertion_anchor,
	)
	proposal_cdml = oasa.cdml_writer.molecules_to_insertion_proposal(
		[molecule], token_stem=token_stem,
	)
	return bkchem_qt.bridge.worker.PreparedMoleculeInsertion(
		proposal_cdml, expected_revision, "Insert verified sucrose Haworth",
	)


#============================================
def _capture_haworth_geometry(target: object) -> tuple[float, tuple[float, float]]:
	"""Capture active scene insertion geometry as immutable built-in worker data."""
	return bkchem_qt.bridge.insertion_placement.capture_insertion_placement(target)


#============================================
class HaworthInsertionDelivery:
	"""Submit one prepared Haworth proposal to its captured source session."""

	#============================================
	def __init__(
			self, app: object, target: object, request_token: int,
			expected_revision: int,
			) -> None:
		"""Capture the session, revision, and provisional request generation."""
		self.app = app
		self._target = target
		self._request_token = request_token
		self._expected_revision = expected_revision

	#============================================
	def is_current(self) -> bool:
		"""Return whether the origin session can receive this worker result."""
		return (
			not self.app._shutdown_prepared
			and self._target in self.app.sessions
			and self._target.import_request_is_current(self._request_token)
		)

	#============================================
	def _discarded_outcome(
			self, message: str,
			) -> bkchem_qt.models.document_session.PersistentActionOutcome:
		"""Return the inert outcome used for a stale or closed source request."""
		return bkchem_qt.models.document_session.PersistentActionOutcome(
			"discarded", message, None, False,
		)

	#============================================
	def deliver(
			self, prepared: object,
			) -> bkchem_qt.models.document_session.PersistentActionOutcome:
		"""Commit one current frozen proposal through backend molecule insertion."""
		if not self.is_current():
			return self._discarded_outcome("Haworth insert request is no longer current")
		if not isinstance(prepared, bkchem_qt.bridge.worker.PreparedMoleculeInsertion):
			message = "Haworth preparation returned invalid data"
			_show_haworth_error(self.app, message)
			return bkchem_qt.models.document_session.PersistentActionOutcome(
				"rejected", message, None, False,
			)
		if (
				prepared.expected_revision != self._expected_revision
				or prepared.expected_revision != self._target.backend_snapshot.revision
				):
			message = "Haworth result is stale; prepare it again."
			_show_haworth_error(self.app, message)
			return bkchem_qt.models.document_session.PersistentActionOutcome(
				"rejected", message, None, False,
			)
		request = bkchem_qt.models.document_session.PersistentOperationRequest(
			operation_key="molecule.insert",
			label=prepared.label or "Insert Haworth sugar",
			payload=(
				("expected_revision", prepared.expected_revision),
				("proposal_cdml", prepared.proposal_cdml),
			),
			target_keys=frozenset(),
		)
		outcome = self._target.submit_persistent_operation(request)
		if outcome.submitted:
			self.app.statusBar().showMessage(outcome.message, 5000)
		elif outcome.status == "rejected":
			_show_haworth_error(self.app, outcome.message)
		return outcome

	#============================================
	def report_error(self, message: object) -> bool:
		"""Report a preparation failure only while the origin request is current."""
		if not self.is_current():
			return False
		_show_haworth_error(self.app, str(message))
		return True


#============================================
class _HaworthPreparedResultRelay(PySide6.QtCore.QObject):
	"""Deliver one frozen Haworth proposal and retire its terminal worker."""

	#============================================
	def __init__(
			self, worker: PySide6.QtCore.QThread,
			delivery: HaworthInsertionDelivery,
			) -> None:
		"""Retain only plain delivery state until worker completion."""
		super().__init__(delivery.app)
		self._worker = worker
		self._delivery = delivery

	#============================================
	@PySide6.QtCore.Slot(object)
	def on_result(self, prepared: object) -> None:
		"""Submit a worker proposal without constructing a Qt molecule model."""
		self._delivery.deliver(prepared)

	#============================================
	@PySide6.QtCore.Slot(object)
	def on_error(self, message: object) -> None:
		"""Route a current worker failure through the Haworth error surface."""
		self._delivery.report_error(message)

	#============================================
	@PySide6.QtCore.Slot()
	def on_thread_finished(self) -> None:
		"""Release through the window-owned terminal worker finalizer."""
		self._delivery.app._release_import_worker(self._worker)
		self.deleteLater()


#============================================
def _show_haworth_error(app: object, message: str) -> None:
	"""Report an invalid sugar code or unrepresentable layout without mutation."""
	PySide6.QtWidgets.QMessageBox.warning(
		app, "Haworth Sugar Error", "Could not insert Haworth sugar:\n%s" % message,
	)


#============================================
def _start_haworth_insert(
		app: object, sugar_code: str, ring_type: str, anomeric: str,
		) -> None:
	"""Start a session-owned Haworth preparation worker."""
	target = app._active_session
	try:
		bond_length_pt, insertion_anchor = _capture_haworth_geometry(target)
	except ValueError as error:
		_show_haworth_error(app, str(error))
		return
	token = target.begin_import_request()
	expected_revision = target.backend_snapshot.revision
	token_stem = "haworth-r%s-i%s" % (expected_revision, token)
	worker = bkchem_qt.bridge.worker.OasaWorker(
		_prepare_haworth_insertion,
		sugar_code,
		ring_type,
		anomeric,
		expected_revision,
		token_stem,
		bond_length_pt,
		insertion_anchor,
	)
	delivery = HaworthInsertionDelivery(app, target, token, expected_revision)
	relay = _HaworthPreparedResultRelay(worker, delivery)
	worker._result_relay = relay
	connection = PySide6.QtCore.Qt.ConnectionType.QueuedConnection
	worker.result.connect(relay.on_result, connection)
	worker.error.connect(relay.on_error, connection)
	worker.finished.connect(relay.on_thread_finished, connection)
	target.track_import_worker(worker)
	app.statusBar().showMessage("Preparing Haworth sugar...", 0)
	worker.start()


#============================================
def _start_verified_sucrose_insert(app: object) -> None:
	"""Start preparation of the named fixed preset for the captured session."""
	target = app._active_session
	try:
		bond_length_pt, insertion_anchor = _capture_haworth_geometry(target)
	except ValueError as error:
		_show_haworth_error(app, str(error))
		return
	token = target.begin_import_request()
	expected_revision = target.backend_snapshot.revision
	token_stem = "verified-sucrose-r%s-i%s" % (expected_revision, token)
	worker = bkchem_qt.bridge.worker.OasaWorker(
		_prepare_verified_sucrose_insertion,
		expected_revision,
		token_stem,
		bond_length_pt,
		insertion_anchor,
	)
	delivery = HaworthInsertionDelivery(app, target, token, expected_revision)
	relay = _HaworthPreparedResultRelay(worker, delivery)
	worker._result_relay = relay
	connection = PySide6.QtCore.Qt.ConnectionType.QueuedConnection
	worker.result.connect(relay.on_result, connection)
	worker.error.connect(relay.on_error, connection)
	worker.finished.connect(relay.on_thread_finished, connection)
	target.track_import_worker(worker)
	app.statusBar().showMessage("Preparing verified sucrose Haworth...", 0)
	worker.start()


#============================================
def insert_haworth(app: object, ring_type: str) -> None:
	"""Prompt for one sugar code and insert the requested Haworth ring form."""
	dialog = HaworthInsertDialog(ring_type, app)
	if dialog.exec() != PySide6.QtWidgets.QDialog.DialogCode.Accepted:
		return
	sugar_code, requested_ring, anomeric = dialog.request(ring_type)
	if not sugar_code:
		_show_haworth_error(app, "Enter a sugar code.")
		return
	_start_haworth_insert(app, sugar_code, requested_ring, anomeric)


#============================================
def insert_verified_sucrose_haworth(app: object) -> None:
	"""Insert the one fixed alpha-glucose/beta-fructose Haworth depiction."""
	_start_verified_sucrose_insert(app)


#============================================
def register_haworth_actions(registry: object, app: object) -> None:
	"""Register Haworth insertion actions selected from the Insert menu."""
	registry.register(MenuAction(
		id="insert.haworth_pyranose",
		label_key="Haworth pyranose",
		help_key="Insert an editable pyranose Haworth projection",
		accelerator=None,
		handler=lambda: insert_haworth(app, "pyranose"),
		enabled_when=None,
	))
	registry.register(MenuAction(
		id="insert.verified_sucrose_haworth",
		label_key="Verified sucrose Haworth",
		help_key="Insert the fixed alpha-glucose beta-fructose Haworth depiction",
		accelerator=None,
		handler=lambda: insert_verified_sucrose_haworth(app),
		enabled_when=None,
	))
	registry.register(MenuAction(
		id="insert.haworth_furanose",
		label_key="Haworth furanose",
		help_key="Insert an editable furanose Haworth projection",
		accelerator=None,
		handler=lambda: insert_haworth(app, "furanose"),
		enabled_when=None,
	))
