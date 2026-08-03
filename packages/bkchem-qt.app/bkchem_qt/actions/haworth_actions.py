"""Editable Haworth sugar insertion actions for BKChem-Qt."""

# Standard Library

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

import bkchem_qt.bridge.insertion_placement
import bkchem_qt.bridge.chemistry_preparation
import bkchem_qt.bridge.worker
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
class DirectGlycosidicHaworthDialog(PySide6.QtWidgets.QDialog):
	"""Collect a structural SMILES for one supported direct glycosidic layout."""

	#============================================
	def __init__(self, parent: object) -> None:
		"""Create the focused SMILES entry dialog.

		The request describes a drawing convention.  It does not infer or label
		alpha/beta/tetrahedral stereochemistry beyond the supplied structure.
		"""
		super().__init__(parent)
		self.setWindowTitle("Direct Glycosidic Haworth")
		form = PySide6.QtWidgets.QFormLayout(self)
		self._smiles = PySide6.QtWidgets.QLineEdit(self)
		self._smiles.setPlaceholderText("Structural SMILES for two directly linked sugar rings")
		form.addRow("SMILES:", self._smiles)
		help_text = PySide6.QtWidgets.QLabel(
			"Creates a two-ring Haworth drawing for a supported direct glycosidic structure.",
			self,
		)
		help_text.setWordWrap(True)
		form.addRow(help_text)
		buttons = PySide6.QtWidgets.QDialogButtonBox(
			PySide6.QtWidgets.QDialogButtonBox.StandardButton.Ok
			| PySide6.QtWidgets.QDialogButtonBox.StandardButton.Cancel,
			parent=self,
		)
		buttons.accepted.connect(self.accept)
		buttons.rejected.connect(self.reject)
		form.addRow(buttons)

	#============================================
	def smiles(self) -> str:
		"""Return normalized user-entered structural SMILES."""
		return self._smiles.text().strip()


#============================================
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
		proposal = bkchem_qt.bridge.chemistry_preparation.molecule_insertion_proposal(prepared)
		if proposal is None:
			message = "Haworth preparation returned invalid data"
			_show_haworth_error(self.app, message)
			return bkchem_qt.models.document_session.PersistentActionOutcome(
				"rejected", message, None, False,
			)
		if (
				proposal.expected_revision != self._expected_revision
				or proposal.expected_revision != self._target.backend_snapshot.revision
				):
			message = "Haworth result is stale; prepare it again."
			_show_haworth_error(self.app, message)
			return bkchem_qt.models.document_session.PersistentActionOutcome(
				"rejected", message, None, False,
			)
		request = bkchem_qt.bridge.chemistry_preparation.build_molecule_insertion_request(
			proposal, "Insert Haworth sugar",
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
		bkchem_qt.bridge.chemistry_preparation.prepare_haworth_insertion,
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
		bkchem_qt.bridge.chemistry_preparation.prepare_verified_sucrose_insertion,
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
def _start_direct_glycosidic_haworth_insert(app: object, smiles: str) -> None:
	"""Prepare one captured-session direct glycosidic Haworth insertion."""
	target = app._active_session
	try:
		bond_length_pt, insertion_anchor = _capture_haworth_geometry(target)
	except ValueError as error:
		_show_haworth_error(app, str(error))
		return
	token = target.begin_import_request()
	expected_revision = target.backend_snapshot.revision
	token_stem = "direct-glycosidic-haworth-r%s-i%s" % (expected_revision, token)
	worker = bkchem_qt.bridge.worker.OasaWorker(
		bkchem_qt.bridge.chemistry_preparation.prepare_direct_glycosidic_haworth_insertion,
		smiles,
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
	app.statusBar().showMessage("Preparing direct glycosidic Haworth drawing...", 0)
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
def insert_direct_glycosidic_haworth(app: object) -> None:
	"""Prompt for a supported two-ring direct glycosidic structural SMILES."""
	dialog = DirectGlycosidicHaworthDialog(app)
	if dialog.exec() != PySide6.QtWidgets.QDialog.DialogCode.Accepted:
		return
	smiles = dialog.smiles()
	if not smiles:
		_show_haworth_error(app, "Enter a structural SMILES.")
		return
	_start_direct_glycosidic_haworth_insert(app, smiles)


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
		id="insert.direct_glycosidic_haworth",
		label_key="Direct Glycosidic Haworth from SMILES...",
		help_key="Insert a supported two-ring direct glycosidic Haworth drawing",
		accelerator=None,
		handler=lambda: insert_direct_glycosidic_haworth(app),
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
