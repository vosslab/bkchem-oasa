"""Focused backend-authority behavior checks for the PySide6 Draw mode."""

# PIP3 modules
import PySide6.QtCore
import pytest

# local repo modules
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.main_window
import bkchem_qt.models.document_session
import bkchem_qt.modes.draw_mode
import oasa.cdml_document
import oasa.safe_xml


_LEGACY_IDLESS_JOIN_TARGET_CDML = (
	'<cdml version="0.15"><molecule id="m1">'
	'<atom id="a1" name="C"><point x="1cm" y="1cm"/></atom>'
	'<atom name="O"><point x="3cm" y="1cm"/></atom>'
	'</molecule></cdml>'
)


#============================================
#============================================
def _install_projection_port(session: object, deliver: object) -> None:
	"""Install one fresh typed projection lifecycle port for this session."""
	port = bkchem_qt.models.document_session.SessionProjectionLifecyclePort(session, deliver)
	session.install_projection_lifecycle_port(port)


#============================================
def _projection_unavailable(snapshot: object) -> object:
	"""Report one deliberately unavailable typed projection outcome."""
	return bkchem_qt.models.document_session.ProjectionLifecycleResult(
		bkchem_qt.models.document_session.ProjectionLifecycleStatus.PREPARATION_UNAVAILABLE,
		bkchem_qt.models.document_session.ProjectionLifecyclePhase.PREPARATION,
	)


def _active_session(main_window: object) -> object:
	"""Return the open session owning the window's public document and scene."""
	for session in main_window.sessions:
		if session.document is main_window.document and session.scene is main_window.scene:
			return session
	raise AssertionError("Main window has no session for its active document and scene")


#============================================
def _draw_mode(session: object) -> bkchem_qt.modes.draw_mode.DrawMode:
	"""Activate and return the session-owned Draw mode."""
	session.mode_manager.set_mode("draw")
	mode = session.mode_manager.current_mode
	if not isinstance(mode, bkchem_qt.modes.draw_mode.DrawMode):
		raise AssertionError("DrawMode did not activate")
	return mode


#============================================
def _new_private_native_session(
		main_window: bkchem_qt.main_window.MainWindow, cdml_text: str,
		) -> object:
	"""Create one synchronized private session from inline complete CDML."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(
		cdml_text,
	)
	session = bkchem_qt.models.document_session.DocumentSession(
		parent=main_window,
		theme_manager=main_window._theme_manager,
		prefs=main_window._prefs,
		mode_host=main_window,
		prepared_native_cdml=prepared,
	)
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	projection = session.retry_current_backend_projection()
	if projection.status != "accepted":
		raise RuntimeError("Draw authority test session did not project its backend snapshot")
	return session


#============================================
def _dispose_private_session(session: object) -> None:
	"""Transfer a private session to the MainWindow lifecycle reaper."""
	owner = session.parent()
	if not isinstance(owner, bkchem_qt.main_window.MainWindow):
		raise TypeError("Draw authority test session has no MainWindow owner")
	owner._dispose_session_later(session)


#============================================
def _draw_at(mode: object, x: float, y: float) -> None:
	"""Complete one non-drag Draw gesture at a fixed scene position."""
	position = PySide6.QtCore.QPointF(x, y)
	mode.mouse_press(position, None)
	mode.mouse_release(position, None)


#============================================
def _direct_children(element: object, name: str) -> tuple[object, ...]:
	"""Return direct compatibility-DOM children with one local CDML name."""
	return tuple(
		child for child in element.childNodes
		if getattr(child, "localName", None) == name
	)


#============================================
def _canonical_draw_facts(complete_cdml: str) -> dict[str, dict[str, object]]:
	"""Return direct-root Draw facts after the owning CDML boundary accepts XML."""
	accepted = oasa.cdml_document.CDMLDocumentSession.load(complete_cdml).snapshot().cdml
	document = oasa.safe_xml.parse_dom_from_string(accepted)
	facts = {}
	for molecule in _direct_children(document.documentElement, "molecule"):
		molecule_id = molecule.getAttribute("id")
		atoms = frozenset(
			atom.getAttribute("id") for atom in _direct_children(molecule, "atom")
		)
		bonds = {
			bond.getAttribute("id"): {
				"type": bond.getAttribute("type"),
				"endpoints": frozenset((bond.getAttribute("start"), bond.getAttribute("end"))),
			}
			for bond in _direct_children(molecule, "bond")
		}
		facts[molecule_id] = {"atoms": atoms, "bonds": bonds}
	return facts


#============================================
def _new_root_pair(session: object, mode: object, x: float, y: float) -> tuple[str, dict[str, object]]:
	"""Draw once and return its newly allocated direct-root molecule facts."""
	before = _canonical_draw_facts(session.backend_snapshot.cdml)
	_draw_at(mode, x, y)
	after = _canonical_draw_facts(session.backend_snapshot.cdml)
	for molecule_id, facts in after.items():
		if molecule_id not in before:
			return molecule_id, facts
	raise AssertionError("Draw gesture did not create a canonical molecule root")


#============================================
def _atom_item_by_id(scene: object, atom_id: str) -> object:
	"""Return the current projection item for one durable atom ID."""
	for item in scene.items():
		if (
			isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
			and item.atom_model.atom_id == atom_id
		):
			return item
	raise AssertionError("Current projection has no requested durable atom")


#============================================
def _atom_item_by_backend_durable_id(scene: object, atom_id: str | None) -> object:
	"""Return one live atom projection using only its backend-issued identity."""
	for item in scene.items():
		if (
			isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
			and item.atom_model.backend_durable_id == atom_id
		):
			return item
	raise AssertionError("Current projection has no requested backend atom identity")


#============================================
def _bond_item_by_id(scene: object, bond_id: str) -> object:
	"""Return the current projection item for one durable bond ID."""
	for item in scene.items():
		if (
			isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem)
			and item.bond_model.bond_id == bond_id
		):
			return item
	raise AssertionError("Current projection has no requested durable bond")


#============================================
class _DrawOperationRecorder:
	"""Expose one session-like revision source while recording Draw requests."""

	def __init__(self, backend_snapshot: object) -> None:
		"""Retain the public backend snapshot that Draw reads before submission."""
		self.backend_snapshot = backend_snapshot
		self.requests: list[object] = []

	#============================================
	def submit(self, request: object) -> object:
		"""Record any unexpected request from an ID-less join target."""
		self.requests.append(request)
		raise AssertionError("ID-less join target reached persistent-operation callback")


#============================================
def _has_durable_bonded_pair(facts: dict[str, object]) -> bool:
	"""Return whether a root owns a bond between two distinct durable atom IDs."""
	atoms = facts["atoms"]
	return any(
		bond_id
		and len(bond["endpoints"]) == 2
		and all(bond["endpoints"])
		and bond["endpoints"] <= atoms
		for bond_id, bond in facts["bonds"].items()
	)


#============================================
@pytest.mark.parametrize(
	("submode", "canonical_type"),
	(
		("normal", "n1"), ("wedge", "w1"), ("hashed", "h1"), ("adder", "a1"),
		("bbold", "b1"), ("dash", "d1"), ("dotted", "o1"), ("wavy", "s1"),
	),
)
def test_draw_submodes_persist_canonical_cdml_bond_types(
		main_window: object, submode: str, canonical_type: str,
		) -> None:
	"""Each selected Draw bond style persists its documented canonical CDML type."""
	session = _active_session(main_window)
	mode = _draw_mode(session)
	mode.set_submode(submode)
	_draw_at(mode, 120.0, 160.0)
	facts = _canonical_draw_facts(session.backend_snapshot.cdml)

	assert canonical_type in {
		bond["type"] for root in facts.values() for bond in root["bonds"].values()
	}


#============================================
def test_blank_gestures_create_distinct_backend_root_pairs(main_window: object) -> None:
	"""Each blank release creates a distinct canonical root with a bonded pair."""
	session = _active_session(main_window)
	mode = _draw_mode(session)
	first_root_id, first_root = _new_root_pair(session, mode, 120.0, 160.0)
	second_root_id, second_root = _new_root_pair(session, mode, 360.0, 160.0)

	assert (
		first_root_id != second_root_id
		and _has_durable_bonded_pair(first_root)
		and _has_durable_bonded_pair(second_root)
	)


#============================================
def test_atom_extension_and_join_use_reprojected_backend_models(main_window: object) -> None:
	"""Extension and same-root join persist the intended durable backend topology."""
	session = _active_session(main_window)
	mode = _draw_mode(session)
	root_id, initial_root = _new_root_pair(session, mode, 120.0, 260.0)
	first_atom_id = next(iter(initial_root["atoms"]))
	other_atom_id = next(
		atom_id for atom_id in initial_root["atoms"] if atom_id != first_atom_id
	)
	first_item = _atom_item_by_id(session.scene, first_atom_id)
	_draw_at(mode, first_item.atom_model.x, first_item.atom_model.y)
	after_extension = _canonical_draw_facts(session.backend_snapshot.cdml)[root_id]
	new_atom_id = next(
		atom_id for atom_id in after_extension["atoms"] if atom_id not in initial_root["atoms"]
	)
	new_item = _atom_item_by_id(session.scene, new_atom_id)
	other_item = _atom_item_by_id(session.scene, other_atom_id)
	start = PySide6.QtCore.QPointF(new_item.atom_model.x, new_item.atom_model.y)
	target = PySide6.QtCore.QPointF(other_item.atom_model.x, other_item.atom_model.y)
	mode.mouse_press(start, None)
	mode.mouse_move(target, None)
	mode.mouse_release(target, None)
	final_root = _canonical_draw_facts(session.backend_snapshot.cdml)[root_id]

	assert {
		frozenset((first_atom_id, new_atom_id)), frozenset((other_atom_id, new_atom_id)),
	} <= {bond["endpoints"] for bond in final_root["bonds"].values()}


#============================================
def test_join_target_without_backend_atom_id_is_inert(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A legacy projection ID never enters a persistent same-root join request."""
	session = _new_private_native_session(main_window, _LEGACY_IDLESS_JOIN_TARGET_CDML)
	try:
		mode = _draw_mode(session)
		source_item = _atom_item_by_backend_durable_id(session.scene, "a1")
		target_item = _atom_item_by_backend_durable_id(session.scene, None)
		source_position = PySide6.QtCore.QPointF(
			source_item.atom_model.x, source_item.atom_model.y,
		)
		target_position = PySide6.QtCore.QPointF(
			target_item.atom_model.x, target_item.atom_model.y,
		)
		before_snapshot = session.backend_snapshot
		before_undo_count = session.document.undo_stack.count()
		before_dirty = session.document.dirty
		recorder = _DrawOperationRecorder(before_snapshot)
		mode.set_persistent_operation(recorder.submit)
		mode.mouse_press(source_position, None)
		mode.mouse_move(target_position, None)
		mode.mouse_release(target_position, None)
		# Release graphics wrappers before the test's owned session enters retirement.
		del source_item, target_item

		assert (
			not recorder.requests
			and session.backend_snapshot.cdml == before_snapshot.cdml
			and session.backend_snapshot.revision == before_snapshot.revision
			and session.document.undo_stack.count() == before_undo_count
			and session.document.dirty == before_dirty
			and session.backend_projection_synchronized
			and session.can_write_authoritative_snapshot
		)
	finally:
		_dispose_private_session(session)


#============================================
def test_bond_click_updates_canonical_backend_bond(main_window: object) -> None:
	"""A bond click applies its documented canonical depiction transition by ID."""
	session = _active_session(main_window)
	mode = _draw_mode(session)
	root_id, root = _new_root_pair(session, mode, 120.0, 360.0)
	bond_id = next(iter(root["bonds"]))
	before_type = root["bonds"][bond_id]["type"]
	bond_item = _bond_item_by_id(session.scene, bond_id)
	first_atom, second_atom = bond_item.bond_model.atom1, bond_item.bond_model.atom2
	midpoint = PySide6.QtCore.QPointF(
		(first_atom.x + second_atom.x) / 2.0,
		(first_atom.y + second_atom.y) / 2.0,
	)
	mode.mouse_press(midpoint, None)
	mode.mouse_release(midpoint, None)
	after_type = _canonical_draw_facts(session.backend_snapshot.cdml)[root_id]["bonds"][bond_id]["type"]

	assert (before_type, after_type) == ("n1", "n2")


#============================================
def test_draw_gesture_replaces_the_projection_from_its_backend_snapshot(
		main_window: object,
		) -> None:
	"""A gesture changes backend CDML and installs a fresh public session projection."""
	session = _active_session(main_window)
	mode = _draw_mode(session)
	before_snapshot = session.backend_snapshot
	before_document = session.document

	_draw_at(mode, 120.0, 460.0)

	assert (
		session.backend_snapshot.cdml != before_snapshot.cdml
		and session.document is not before_document
		and session.backend_projection_synchronized
	)


#============================================
def test_projection_failure_retries_the_accepted_draw_snapshot(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A failed Draw projection recovers only by installing its accepted snapshot."""
	session = _active_session(main_window)
	mode = _draw_mode(session)
	before_snapshot = session.backend_snapshot
	install_projection = session._install_prepared_projection
	failure_pending = True
	failed_snapshot = None
	retried_snapshot = None

	def fail_first_projection_install(
			prepared: object, selected_keys: object, file_path: object,
			projected_snapshot: object,
			) -> None:
		"""Reject only the accepted Draw candidate's first projection install."""
		nonlocal failure_pending, failed_snapshot, retried_snapshot
		if failure_pending:
			failure_pending = False
			failed_snapshot = projected_snapshot
			raise RuntimeError("one-time projection installation failure")
		retried_snapshot = projected_snapshot
		install_projection(prepared, selected_keys, file_path, projected_snapshot)

	monkeypatch.setattr(
		session,
		"_install_prepared_projection",
		fail_first_projection_install,
	)
	_draw_at(mode, 120.0, 560.0)
	accepted_snapshot = session.backend_snapshot
	accepted_cdml = accepted_snapshot.cdml
	assert (
		accepted_snapshot.cdml != before_snapshot.cdml
		and failed_snapshot == accepted_snapshot
		and not session.backend_projection_synchronized
		and main_window.document is session.document
		and main_window.scene is session.scene
		and main_window.view is session.view
	)
	projection_before_retry = session.document
	retry = session.retry_current_backend_projection()
	assert (
		retry.status == "accepted"
		and retried_snapshot == accepted_snapshot
		and session.backend_snapshot == accepted_snapshot
		and session.backend_snapshot.cdml == accepted_cdml
		and session.document is not projection_before_retry
		and session.backend_projection_synchronized
		and main_window.document is session.document
		and main_window.scene is session.scene
		and main_window.view is session.view
	)
