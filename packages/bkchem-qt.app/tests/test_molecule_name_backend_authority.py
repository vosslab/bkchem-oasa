"""Focused Qt coverage for backend-owned molecule display-name edits."""

# Standard Library
import types

# PIP3 modules
import pytest
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.actions.chemistry_actions
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.modes.draw_mode
import bkchem_qt.models.document_session
import oasa.cdml_document


#============================================
def _active_session(main_window: object) -> object:
	"""Return the session owning the current public projection."""
	for session in main_window.sessions:
		if session.document is main_window.document and session.scene is main_window.scene:
			return session
	raise AssertionError("Main window has no active document session")


#============================================
def _draw_one_molecule(session: object) -> str:
	"""Create one authoritative direct-root molecule and return its durable ID."""
	session.mode_manager.set_mode("draw")
	mode = session.mode_manager.current_mode
	if not isinstance(mode, bkchem_qt.modes.draw_mode.DrawMode):
		raise AssertionError("DrawMode did not activate")
	position = PySide6.QtCore.QPointF(120.0, 160.0)
	mode.mouse_press(position, None)
	mode.mouse_release(position, None)
	for molecule in session.document.molecules:
		if molecule.mol_id:
			return molecule.mol_id
	raise AssertionError("Draw did not create a durable molecule")


#============================================
def _select_one_atom(session: object) -> object:
	"""Select one live child atom for its owning direct-root molecule."""
	for item in session.scene.items():
		if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
			item.setSelected(True)
			return item
	raise AssertionError("Draw did not project an atom")


#============================================
def _molecule_name(session: object, molecule_id: str) -> str:
	"""Return the current projected name for one durable direct root."""
	for molecule in session.document.molecules:
		if molecule.mol_id == molecule_id:
			return molecule.name
	raise AssertionError("Molecule projection did not retain its durable ID")


#============================================
def _capture_warnings(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
	"""Record non-modal action warnings for one focused interaction test."""
	warnings = []

	def record_warning(_parent: object, title: str, text: str) -> None:
		"""Retain one warning without opening a modal dialog."""
		warnings.append((title, text))

	monkeypatch.setattr(PySide6.QtWidgets.QMessageBox, "warning", record_warning)
	return warnings


#============================================
def test_molecule_name_operation_uses_backend_undo_redo_and_reprojection(
		main_window: object,
		) -> None:
	"""A name edit accepts once and backend history restores the canonical name."""
	session = _active_session(main_window)
	molecule_id = _draw_one_molecule(session)
	before_document = session.document
	request = bkchem_qt.models.document_session.build_molecule_name_request(
		session.backend_snapshot.revision, molecule_id, "Product A",
	)
	outcome = session.submit_persistent_operation(request)
	changed_name = next(
		molecule.name for molecule in session.document.molecules
		if molecule.mol_id == molecule_id
	)
	undo = session.undo_backend()
	redo = session.redo_backend()

	assert outcome.status == "accepted" and session.document is not before_document
	assert changed_name == "Product A" and undo.status == "accepted" and redo.status == "accepted"


#============================================
def test_molecule_name_same_value_is_an_authoritative_session_noop(
		main_window: object,
		) -> None:
	"""An unchanged backend snapshot leaves history and projection untouched."""
	session = _active_session(main_window)
	molecule_id = _draw_one_molecule(session)
	before_snapshot = session.backend_snapshot
	before_document = session.document
	before_history = session._backend_history
	before_generation = session.document.persistent_generation
	before_dirty = session.document.dirty
	before_save_eligibility = session.can_write_authoritative_snapshot
	request = bkchem_qt.models.document_session.build_molecule_name_request(
		before_snapshot.revision, molecule_id, "",
	)
	outcome = session.submit_persistent_operation(request)

	assert (
		outcome.status == "accepted"
		and outcome.submitted
		and outcome.commit is None
		and session.backend_snapshot == before_snapshot
		and session.document is before_document
		and session._backend_history == before_history
		and session.document.persistent_generation == before_generation
		and session.document.dirty == before_dirty
		and session.can_write_authoritative_snapshot == before_save_eligibility
	)


#============================================
def test_set_molecule_name_action_commits_child_selection_through_backend_history(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""The menu action resolves an atom child to its durable root before commit."""
	session = _active_session(main_window)
	molecule_id = _draw_one_molecule(session)
	_select_one_atom(session)
	before_document = session.document
	monkeypatch.setattr(
		PySide6.QtWidgets.QInputDialog, "getText",
		lambda *_args, **_kwargs: ("Product A", True),
	)
	bkchem_qt.actions.chemistry_actions._set_name(main_window)
	undo = session.undo_backend()
	redo = session.redo_backend()

	assert _molecule_name(session, molecule_id) == "Product A" and session.document is not before_document
	assert undo.status == "accepted" and redo.status == "accepted"


#============================================
def test_set_molecule_name_action_same_input_is_a_noop(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""The interactive same-name result preserves its installed projection."""
	session = _active_session(main_window)
	_draw_one_molecule(session)
	_select_one_atom(session)
	before_snapshot = session.backend_snapshot
	before_document = session.document
	before_history = session._backend_history
	before_generation = session.document.persistent_generation
	before_dirty = session.document.dirty
	before_save_eligibility = session.can_write_authoritative_snapshot
	warnings = _capture_warnings(monkeypatch)
	monkeypatch.setattr(
		PySide6.QtWidgets.QInputDialog, "getText",
		lambda *_args, **_kwargs: ("", True),
	)
	bkchem_qt.actions.chemistry_actions._set_name(main_window)

	assert (
		session.backend_snapshot == before_snapshot
		and session.document is before_document
		and session._backend_history == before_history
		and session.document.persistent_generation == before_generation
		and session.document.dirty == before_dirty
		and session.can_write_authoritative_snapshot == before_save_eligibility
		and not warnings
	)


#============================================
def test_set_molecule_name_cancel_preserves_the_authoritative_projection(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Cancelling the input dialog never starts a persistent submission."""
	session = _active_session(main_window)
	_draw_one_molecule(session)
	_select_one_atom(session)
	before_snapshot = session.backend_snapshot
	before_document = session.document
	before_history = session._backend_history
	monkeypatch.setattr(
		PySide6.QtWidgets.QInputDialog, "getText",
		lambda *_args, **_kwargs: ("ignored", False),
	)
	bkchem_qt.actions.chemistry_actions._set_name(main_window)

	assert (
		session.backend_snapshot == before_snapshot
		and session.document is before_document
		and session._backend_history == before_history
	)


#============================================
def test_set_molecule_name_rejects_an_unregistered_active_session_alias(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""An alias cannot mutate the active projection without session ownership."""
	session = _active_session(main_window)
	_draw_one_molecule(session)
	_select_one_atom(session)
	before_snapshot = session.backend_snapshot
	before_document = session.document
	before_history = session._backend_history
	warnings = _capture_warnings(monkeypatch)

	def dialog_must_not_open(*_args: object, **_kwargs: object) -> tuple[str, bool]:
		"""Expose an attempt to use an unregistered session alias."""
		raise AssertionError("unregistered session alias opened a name dialog")

	false_alias = types.SimpleNamespace(
		document=session.document,
		scene=session.scene,
		view=session.view,
		is_disposed=False,
		can_write_authoritative_snapshot=True,
	)
	monkeypatch.setattr(PySide6.QtWidgets.QInputDialog, "getText", dialog_must_not_open)
	main_window._active_session = false_alias
	try:
		bkchem_qt.actions.chemistry_actions._set_name(main_window)
	finally:
		main_window._active_session = session

	assert (
		session.backend_snapshot == before_snapshot
		and session.document is before_document
		and session._backend_history == before_history
		and warnings == [(
			"Set Molecule Name",
			"Set molecule name requires an active synchronized document session.",
		)]
	)


#============================================
@pytest.mark.parametrize(
	"error_type",
	(
		oasa.cdml_document.CDMLRevisionConflictError,
		oasa.cdml_document.CDMLMoleculeNameEditError,
	),
)
def test_set_molecule_name_typed_backend_failure_preserves_local_state(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		error_type: type[Exception],
		) -> None:
	"""A stale or typed backend rejection retains the current projection exactly."""
	session = _active_session(main_window)
	_draw_one_molecule(session)
	_select_one_atom(session)
	before_snapshot = session.backend_snapshot
	before_document = session.document
	before_history = session._backend_history
	warnings = _capture_warnings(monkeypatch)

	def raise_backend_failure(*_args: object) -> object:
		"""Model a typed rejected name request after the action captures its target."""
		raise error_type("typed name failure")

	monkeypatch.setattr(
		PySide6.QtWidgets.QInputDialog, "getText",
		lambda *_args, **_kwargs: ("blocked", True),
	)
	monkeypatch.setattr(session._backend_session, "set_molecule_name", raise_backend_failure)
	bkchem_qt.actions.chemistry_actions._set_name(main_window)

	assert (
		session.backend_snapshot == before_snapshot
		and session.document is before_document
		and session._backend_history == before_history
		and warnings == [("Set Molecule Name", "typed name failure")]
	)


#============================================
def test_molecule_name_operation_rejects_unsynchronized_session(
		main_window: object,
		) -> None:
	"""An unsynchronized projection submits no persistent molecule-name change."""
	session = _active_session(main_window)
	molecule_id = _draw_one_molecule(session)
	before = session.backend_snapshot
	session._backend_projection_synchronized = False
	request = bkchem_qt.models.document_session.build_molecule_name_request(
		before.revision, molecule_id, "blocked",
	)
	outcome = session.submit_persistent_operation(request)

	assert outcome.status != "accepted" and session.backend_snapshot == before
