"""Behavioral coverage for the temporary Qt-to-backend CDML session seam."""

# Standard Library
import errno
import math
import os
import pathlib
import re
import stat

# PIP3 modules
import pytest
import shiboken6
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.canvas.graphics_retirement
import bkchem_qt.canvas.document_projection
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.io.cdml_document_io
import bkchem_qt.actions.file_actions
import bkchem_qt.actions.repair_actions
import bkchem_qt.bridge.oasa_bridge
import bkchem_qt.config.preferences
import bkchem_qt.main_window
import bkchem_qt.models.document
import bkchem_qt.models.document_object
import bkchem_qt.models.document_session
import bkchem_qt.models.projection_lifecycle
import bkchem_qt.modes.template_mode
import bkchem_qt.setup.mode_setup
import oasa.cdml_document
import oasa.template_placement
import oasa.cdml_writer


_ARROW_CDML = '<cdml version="0.15"><arrow id="arrow-1"/></cdml>'
_PROVISIONAL_ARROW = "__bkchem_new__arrow"
_OPEN_ARROW_CDML = (
	'<cdml version="0.15"><arrow id="arrow-1">'
	'<point x="1cm" y="1cm"/><point x="3cm" y="1cm"/>'
	'</arrow></cdml>'
)
_REPAIR_CDML = (
	'<cdml version="26.07"><molecule id="m1">'
	'<atom id="a1" name="C"><point x="1cm" y="1cm"/></atom>'
	'<atom id="a2" name="O"><point x="4cm" y="1cm"/></atom>'
	'<bond id="b1" start="a1" end="a2" type="n1"/>'
	'</molecule><arrow id="arrow1"><point x="1cm" y="2cm"/>'
	'<point x="3cm" y="2cm"/></arrow></cdml>'
)
_ANGLE_REPAIR_CDML = (
	'<cdml version="26.07"><molecule id="m1">'
	'<atom id="a1" name="C"><point x="1cm" y="1cm"/></atom>'
	'<atom id="a2" name="C"><point x="4cm" y="1cm"/></atom>'
	'<atom id="a3" name="O"><point x="3cm" y="3cm"/></atom>'
	'<bond id="b1" start="a1" end="a2" type="n1"/>'
	'<bond id="b2" start="a1" end="a3" type="n1"/>'
	'</molecule></cdml>'
)
_STRAIGHTEN_REPAIR_CDML = (
	'<cdml version="26.07"><molecule id="m1">'
	'<atom id="a1" name="C"><point x="1cm" y="1cm"/></atom>'
	'<atom id="a2" name="O"><point x="4cm" y="2cm"/></atom>'
	'<bond id="b1" start="a1" end="a2" type="n1"/>'
	'</molecule></cdml>'
)
_RING_REPAIR_CDML = (
	'<cdml version="26.07"><molecule id="m1">'
	'<atom id="a1" name="C"><point x="0cm" y="0cm"/></atom>'
	'<atom id="a2" name="C"><point x="2cm" y="0cm"/></atom>'
	'<atom id="a3" name="C"><point x="1.5cm" y="1cm"/></atom>'
	'<atom id="a4" name="C"><point x="0cm" y="1cm"/></atom>'
	'<bond id="rb1" start="a1" end="a2" type="n1"/>'
	'<bond id="rb2" start="a2" end="a3" type="n1"/>'
	'<bond id="rb3" start="a3" end="a4" type="n1"/>'
	'<bond id="rb4" start="a4" end="a1" type="n1"/>'
	'</molecule></cdml>'
)
_DELETE_CDML = (
	'<cdml version="26.07"><molecule id="m1">'
	'<atom id="a1" name="C"><point x="1cm" y="1cm"/></atom>'
	'</molecule><arrow id="arrow1"><point x="1cm" y="2cm"/>'
	'<point x="3cm" y="2cm"/></arrow></cdml>'
)
_ELEMENT_CDML = (
	'<cdml version="26.07"><molecule id="m1">'
	'<atom id="a1" name="C" charge="1"><point x="1cm" y="1cm"/></atom>'
	'<atom id="a2" name="O"><point x="3cm" y="1cm"/></atom>'
	'<bond id="b1" start="a1" end="a2" type="n1"/>'
	'</molecule><arrow id="arrow1"><point x="1cm" y="2cm"/>'
	'<point x="3cm" y="2cm"/></arrow></cdml>'
)
_ALIGN_CDML = (
	'<cdml version="26.07"><molecule id="m1">'
	'<atom id="a1" name="C"><point x="1cm" y="1cm"/></atom>'
	'<atom id="a2" name="O"><point x="3cm" y="5cm"/></atom>'
	'<bond id="b1" start="a1" end="a2" type="w1"/>'
	'</molecule></cdml>'
)
_MOLFILE = """Imported ethane
  BKChem

  2  1  0  0  0  0  0  0  0  0999 V2000
    0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    1.5000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
  1  2  1  0  0  0  0
M  END
"""
_MULTI_COMPONENT_SDF = _MOLFILE + "$$$$\n" + """Imported oxygen
  BKChem

  1  0  0  0  0  0  0  0  0  0999 V2000
    4.0000    0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
M  END
$$$$
"""


#============================================
#============================================
def _install_projection_port(session: object, deliver: object) -> None:
	"""Install one fresh typed projection lifecycle port for this session."""
	port = bkchem_qt.models.projection_lifecycle.SessionProjectionLifecyclePort(session, deliver)
	session.install_projection_lifecycle_port(port)


#============================================
def _projection_unavailable(snapshot: object) -> object:
	"""Report one deliberately unavailable typed projection outcome."""
	return bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult(
		bkchem_qt.models.projection_lifecycle.ProjectionLifecycleStatus.PREPARATION_UNAVAILABLE,
		bkchem_qt.models.projection_lifecycle.ProjectionLifecyclePhase.PREPARATION,
	)


#============================================
def _projection_installed(snapshot: object) -> object:
	"""Report an installed typed projection outcome without a real replacement."""
	return bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult(
		bkchem_qt.models.projection_lifecycle.ProjectionLifecycleStatus.INSTALLED,
		bkchem_qt.models.projection_lifecycle.ProjectionLifecyclePhase.COMPLETE,
	)


def _arrow_candidate(identifier: str = _PROVISIONAL_ARROW) -> str:
	"""Return one complete CDML candidate with a frontend arrow token."""
	return '<cdml version="0.15"><arrow id="%s"/></cdml>' % identifier


#============================================
def _new_tab(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> bkchem_qt.models.document_session.DocumentSession:
	"""Create one fresh tab without changing the module fixture's initial tab."""
	main_window._on_new()
	session = main_window.sessions[-1]
	return session


#============================================
def _close_tab(
		main_window: bkchem_qt.main_window.MainWindow,
		session: bkchem_qt.models.document_session.DocumentSession,
		) -> None:
	"""Dispose a temporary tab without entering a user-confirmation dialog."""
	assert main_window._remove_session(session)


#============================================
def _new_synchronized_session(
		main_window: bkchem_qt.main_window.MainWindow,
		prepared_native_cdml: bkchem_qt.models.document_session.PreparedNativeCDML,
		) -> bkchem_qt.models.document_session.DocumentSession:
	"""Install one prepared native CDML transfer into a private session."""
	session = bkchem_qt.models.document_session.DocumentSession(
		parent=main_window,
		theme_manager=main_window._theme_manager,
		prefs=main_window._prefs,
		mode_host=main_window,
		prepared_native_cdml=prepared_native_cdml,
	)
	return session


#============================================
def _new_native_session(
		main_window: bkchem_qt.main_window.MainWindow, cdml_text: str = _ARROW_CDML,
		) -> bkchem_qt.models.document_session.DocumentSession:
	"""Create an unregistered session projected from one backend CDML value."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(
		cdml_text,
	)
	return _new_synchronized_session(main_window, prepared)


#============================================
def _wait_for_async_import_terminal(
		qtbot: object,
		main_window: bkchem_qt.main_window.MainWindow,
		target: bkchem_qt.models.document_session.DocumentSession,
		) -> None:
	"""Wait for the session-owned worker relay to finish without sleeps."""
	qtbot.waitUntil(
		lambda: not target._import_workers and not main_window._retired_import_workers,
		timeout=3000,
	)


#============================================
def _persistent_ids_and_bond_endpoints(cdml_text: str) -> tuple[set[str], set[str]]:
	"""Return durable identifiers and recognized bond endpoints from canonical CDML."""
	oasa.cdml_document.CDMLDocument.parse(cdml_text, validation="strict")
	identifiers = set(re.findall(r'\sid="([^"]+)"', cdml_text))
	endpoint_ids = set(re.findall(r'\s(?:start|end)="([^"]+)"', cdml_text))
	return identifiers, endpoint_ids


#============================================
def _centimeters(value: str) -> float:
	"""Return one fixture coordinate expressed in the CDML centimeter unit."""
	if not value.endswith("cm"):
		raise ValueError("fixture coordinate is not in centimeters")
	return float(value.removesuffix("cm"))


#============================================
def _backend_atom_coordinates(
		cdml_text: str, atom_ids: tuple[str, ...],
		) -> tuple[tuple[float, float], ...]:
	"""Read atom geometry through the public CDML parser for backend assertions."""
	document = oasa.cdml_document.CDMLDocument.parse(cdml_text, validation="strict")
	coordinates = []
	for atom_id in atom_ids:
		record = document.find_by_id(atom_id)
		if record is None:
			raise AssertionError("fixture atom is absent from parsed CDML: %s" % atom_id)
		values = dict(re.findall(r'\b([xy])="([^"]+)"', record.raw_xml))
		try:
			coordinates.append(tuple(_centimeters(values[axis]) for axis in ("x", "y")))
		except (KeyError, ValueError) as error:
			raise AssertionError("fixture atom has non-centimeter coordinates: %s" % atom_id) from error
	return tuple(coordinates)


#============================================
def _selected_atom_ids(
		session: bkchem_qt.models.document_session.DocumentSession,
		) -> set[str]:
	"""Return durable atom identities selected by the current projection."""
	return {
		item.atom_model.backend_durable_id
		for item in session.scene.selectedItems()
		if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
		and item.atom_model.backend_durable_id is not None
	}


#============================================
def _selected_bond_ids(
		session: bkchem_qt.models.document_session.DocumentSession,
		) -> set[str]:
	"""Return durable bond identities selected by the current projection."""
	return {
		item.bond_model.backend_durable_id
		for item in session.scene.selectedItems()
		if isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem)
		and item.bond_model.backend_durable_id is not None
	}


#============================================
def _selected_persistent_keys(
		session: bkchem_qt.models.document_session.DocumentSession,
		) -> set[tuple[str, str]]:
	"""Return every durable key selected by the current disposable projection."""
	keys = set()
	for item in session.scene.selectedItems():
		key = bkchem_qt.canvas.document_projection.persistent_selection_key(item)
		if key is not None:
			keys.add(key)
	return keys


#============================================
class _KeyEvent:
	"""Minimal deterministic key event for one EditMode arrow-key gesture."""

	#============================================
	def __init__(self, key: PySide6.QtCore.Qt.Key) -> None:
		"""Store one Qt key with no modifier state."""
		self._key = key

	#============================================
	def key(self) -> PySide6.QtCore.Qt.Key:
		"""Return the selected arrow key."""
		return self._key

	#============================================
	def modifiers(self) -> PySide6.QtCore.Qt.KeyboardModifier:
		"""Return the deterministic no-modifier state."""
		return PySide6.QtCore.Qt.KeyboardModifier.NoModifier


#============================================
#============================================
def test_atom_align_public_mode_uses_backend_history_and_fresh_projection(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""The parsed horizontal mode aligns durable atoms without Qt undo ownership."""
	session = _new_native_session(main_window, _ALIGN_CDML)
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	if not session.replace_projection_from_backend_snapshot(session.backend_snapshot):
		raise AssertionError("Durable CDML projection is unavailable")
	session.mode_manager.set_mode("bondalign")
	mode = session.mode_manager.current_mode
	for item in session.scene.items():
		if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
			item.setSelected(True)
	if not session.scene.selectedItems():
		raise AssertionError("Projected CDML did not produce selectable AtomItems")
	if _selected_atom_ids(session) != {"a1", "a2"}:
		raise AssertionError("Projected CDML did not retain durable atom identities")
	before = session.backend_snapshot
	before_document = session.document
	try:
		mode.mouse_press(PySide6.QtCore.QPointF(), object())
		accepted = session.backend_snapshot
		accepted_document = session.document
		accepted_selected_ids = _selected_atom_ids(session)
		accepted_undo_count = accepted_document.undo_stack.count()
		undone = session.undo_backend()
		undone_snapshot = session.backend_snapshot
		undone_document = session.document
		undone_selected_ids = _selected_atom_ids(session)
		undone_undo_count = undone_document.undo_stack.count()
		redone = session.redo_backend()
		redone_snapshot = session.backend_snapshot
		redone_document = session.document
		redone_selected_ids = _selected_atom_ids(session)
		redone_undo_count = redone_document.undo_stack.count()

		assert (
			accepted.revision != before.revision
			and _backend_atom_coordinates(accepted.cdml, ("a1", "a2")) == ((1.0, 3.0), (3.0, 3.0))
			and accepted_document is not before_document
			and accepted_selected_ids == {"a1", "a2"}
			and accepted_undo_count == 0
		)
		assert (
			undone.status == "accepted"
			and undone_snapshot.cdml == before.cdml
			and undone_document is not accepted_document
			and undone_selected_ids == {"a1", "a2"}
			and undone_undo_count == 0
		)
		assert (
			redone.status == "accepted"
			and redone_snapshot.cdml == accepted.cdml
			and redone_document is not undone_document
			and redone_selected_ids == {"a1", "a2"}
			and redone_undo_count == 0
		)
	finally:
		_dispose_session(session)


#============================================
def test_edit_mode_nudge_uses_backend_history_and_reprojects_selected_atoms(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""One arrow key sends one backend atom translation with no Qt undo command."""
	session = _new_native_session(main_window, _ALIGN_CDML)
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	if not session.replace_projection_from_backend_snapshot(session.backend_snapshot):
		raise AssertionError("Durable CDML projection is unavailable")
	session.mode_manager.set_mode("edit")
	mode = session.mode_manager.current_mode
	for item in session.scene.items():
		if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
			item.setSelected(True)
	before = session.backend_snapshot
	before_document = session.document
	try:
		mode.key_press(_KeyEvent(PySide6.QtCore.Qt.Key.Key_Right))
		accepted = session.backend_snapshot
		accepted_document = session.document
		accepted_selected_ids = _selected_atom_ids(session)
		accepted_undo_count = accepted_document.undo_stack.count()
		undone = session.undo_backend()
		undone_snapshot = session.backend_snapshot
		undone_document = session.document
		undone_selected_ids = _selected_atom_ids(session)
		undone_undo_count = undone_document.undo_stack.count()
		redone = session.redo_backend()
		redone_snapshot = session.backend_snapshot
		redone_document = session.document
		redone_selected_ids = _selected_atom_ids(session)
		redone_undo_count = redone_document.undo_stack.count()

		assert (
			accepted.revision != before.revision
			and _backend_atom_coordinates(accepted.cdml, ("a1", "a2")) == ((1.071, 1.0), (3.071, 5.0))
			and accepted_document is not before_document
			and accepted_selected_ids == {"a1", "a2"}
			and accepted_undo_count == 0
		)
		assert (
			undone.status == "accepted"
			and undone_snapshot.cdml == before.cdml
			and undone_document is not accepted_document
			and undone_selected_ids == {"a1", "a2"}
			and undone_undo_count == 0
		)
		assert (
			redone.status == "accepted"
			and redone_snapshot.cdml == accepted.cdml
			and redone_document is not undone_document
			and redone_selected_ids == {"a1", "a2"}
			and redone_undo_count == 0
		)
	finally:
		_dispose_session(session)


#============================================
def test_atom_translation_projection_retry_does_not_resubmit_the_accepted_request(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A failed accepted projection retries its snapshot without another backend nudge."""
	session = _new_native_session(main_window, _ALIGN_CDML)
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	if not session.replace_projection_from_backend_snapshot(session.backend_snapshot):
		raise AssertionError("Durable CDML projection is unavailable")
	calls = []
	executor_calls = []
	executor = session._operation_commit_executors["atom-translate"]

	def count_translate(
			prepared: bkchem_qt.models.document_session._PreparedPersistentOperation,
			) -> oasa.cdml_document.CDMLAtomTranslateResult:
		"""Record the sole backend translation executor call."""
		executor_calls.append(prepared)
		return executor(prepared)

	def fail_once(snapshot: oasa.cdml_document.CDMLSnapshot) -> bool:
		"""Reject the first accepted projection and install the retry normally."""
		calls.append(snapshot.revision)
		if len(calls) == 1:
			return _projection_unavailable(snapshot)
		return session.replace_projection_from_backend_snapshot(snapshot)

	session._operation_commit_executors["atom-translate"] = count_translate
	_install_projection_port(session, fail_once)
	try:
		outcome = session.submit_atom_translate((("m1", "a1"),), (2.0, 0.0))
		accepted_revision = session.backend_snapshot.revision
		retried = session.retry_current_backend_projection()

		assert outcome.status == "unavailable" and retried.status == "accepted"
		assert (
			len(executor_calls) == 1
			and calls == [accepted_revision, accepted_revision]
			and session.backend_snapshot.revision == accepted_revision
		)
	finally:
		_dispose_session(session)


#============================================
def test_atom_rotation_uses_backend_history_and_reprojection(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A RotateMode gesture installs fresh backend-owned state without Qt undo."""
	session = _new_native_session(main_window, _ALIGN_CDML)
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	if not session.replace_projection_from_backend_snapshot(session.backend_snapshot):
		raise AssertionError("Durable CDML projection is unavailable")
	try:
		old_item = next(
			item for item in session.scene.items()
			if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
			and item.atom_model.backend_durable_id == "a1"
		)
		old_item.setSelected(True)
		before_document = session.document
		before_revision = session.backend_snapshot.revision
		session.mode_manager.set_mode("rotate")
		mode = session.mode_manager.current_mode
		mode.mouse_press(PySide6.QtCore.QPointF(0.0, 0.0), object())
		mode.mouse_move(PySide6.QtCore.QPointF(100.0, 0.0), object())
		mode.mouse_move(PySide6.QtCore.QPointF(0.0, 100.0), object())
		mode.mouse_release(PySide6.QtCore.QPointF(0.0, 100.0), object())

		assert (
			session.backend_snapshot.revision == before_revision + 1
			and 'x="-1.000cm" y="1cm"' in session.backend_snapshot.cdml
			and session.document is not before_document
		)
		assert (
			_selected_atom_ids(session) == {"a1"}
			and session.document.undo_stack.count() == 0
			and not shiboken6.isValid(old_item)
		)
	finally:
		_dispose_session(session)


#============================================
def test_rotate_mode_keeps_the_press_session_callback_after_rebind(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A tab rebind during a drag cannot redirect its already-captured intent."""
	session = _new_native_session(main_window, _ALIGN_CDML)
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	if not session.replace_projection_from_backend_snapshot(session.backend_snapshot):
		raise AssertionError("Durable CDML projection is unavailable")
	calls = []
	def origin_callback(
			targets: tuple[tuple[str, str], ...], center: tuple[float, float], angle: float,
			) -> bkchem_qt.models.document_session.PersistentActionOutcome:
		"""Record the original session callback without changing backend state."""
		calls.append(("origin", targets, center, angle))
		return bkchem_qt.models.document_session.PersistentActionOutcome("accepted", "", None)

	def replacement_callback(
			targets: tuple[tuple[str, str], ...], center: tuple[float, float], angle: float,
			) -> bkchem_qt.models.document_session.PersistentActionOutcome:
		"""Expose any incorrect callback retargeting after the press event."""
		calls.append(("replacement", targets, center, angle))
		return bkchem_qt.models.document_session.PersistentActionOutcome("accepted", "", None)

	try:
		atom = next(
			item for item in session.scene.items()
			if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
			and item.atom_model.backend_durable_id == "a1"
		)
		atom.setSelected(True)
		session.mode_manager.set_mode("rotate")
		mode = session.mode_manager.current_mode
		mode.set_atom_rotate_operation(origin_callback)
		mode.mouse_press(PySide6.QtCore.QPointF(0.0, 0.0), object())
		mode.set_atom_rotate_operation(replacement_callback)
		mode.mouse_move(PySide6.QtCore.QPointF(100.0, 0.0), object())
		mode.mouse_move(PySide6.QtCore.QPointF(0.0, 100.0), object())
		mode.mouse_release(PySide6.QtCore.QPointF(0.0, 100.0), object())

		assert calls and calls[0][0:3] == ("origin", (("m1", "a1"),), (0.0, 0.0))
		assert calls[0][3] == pytest.approx(math.pi / 2)
	finally:
		_dispose_session(session)


#============================================
def test_rotate_mode_projection_retry_uses_only_the_accepted_snapshot(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A failed RotateMode projection retries its final backend snapshot once."""
	session = _new_native_session(main_window, _ALIGN_CDML)
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	if not session.replace_projection_from_backend_snapshot(session.backend_snapshot):
		raise AssertionError("Durable CDML projection is unavailable")
	calls = []
	executor_calls = []
	executor = session._operation_commit_executors["atom-rotate"]

	def count_rotate(
			prepared: bkchem_qt.models.document_session._PreparedPersistentOperation,
			) -> oasa.cdml_document.CDMLAtomRotateResult:
		"""Record the one accepted backend rotation."""
		executor_calls.append(prepared)
		return executor(prepared)

	def fail_once(snapshot: oasa.cdml_document.CDMLSnapshot) -> bool:
		"""Reject the initial projection then allow exact-snapshot recovery."""
		calls.append(snapshot.revision)
		if len(calls) == 1:
			return _projection_unavailable(snapshot)
		return session.replace_projection_from_backend_snapshot(snapshot)

	session._operation_commit_executors["atom-rotate"] = count_rotate
	_install_projection_port(session, fail_once)
	try:
		atom = next(
			item for item in session.scene.items()
			if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
			and item.atom_model.backend_durable_id == "a1"
		)
		atom.setSelected(True)
		session.mode_manager.set_mode("rotate")
		mode = session.mode_manager.current_mode
		mode.mouse_press(PySide6.QtCore.QPointF(0.0, 0.0), object())
		mode.mouse_move(PySide6.QtCore.QPointF(100.0, 0.0), object())
		mode.mouse_move(PySide6.QtCore.QPointF(0.0, 100.0), object())
		mode.mouse_release(PySide6.QtCore.QPointF(0.0, 100.0), object())
		accepted_revision = session.backend_snapshot.revision
		retried = session.retry_current_backend_projection()

		assert retried.status == "accepted" and len(executor_calls) == 1
		assert calls == [accepted_revision, accepted_revision] and session.backend_snapshot.revision == accepted_revision
	finally:
		_dispose_session(session)


#============================================
def test_rotate_mode_unwraps_a_positive_branch_crossing(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A clockwise sweep across atan2's branch submits the short positive turn."""
	session = _new_native_session(main_window, _ALIGN_CDML)
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	if not session.replace_projection_from_backend_snapshot(session.backend_snapshot):
		raise AssertionError("Durable CDML projection is unavailable")
	angles = []
	def capture(
			targets: tuple[tuple[str, str], ...], center: tuple[float, float], angle: float,
			) -> bkchem_qt.models.document_session.PersistentActionOutcome:
		"""Capture the normalised preview result without committing a fixture edit."""
		del targets, center
		angles.append(angle)
		return bkchem_qt.models.document_session.PersistentActionOutcome("accepted", "", None)

	try:
		atom = next(
			item for item in session.scene.items()
			if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
			and item.atom_model.backend_durable_id == "a1"
		)
		atom.setSelected(True)
		session.mode_manager.set_mode("rotate")
		mode = session.mode_manager.current_mode
		mode.set_atom_rotate_operation(capture)
		mode.mouse_press(PySide6.QtCore.QPointF(0.0, 0.0), object())
		mode.mouse_move(PySide6.QtCore.QPointF(-100.0, 1.7455), object())
		mode.mouse_move(PySide6.QtCore.QPointF(-100.0, -1.7455), object())
		mode.mouse_release(PySide6.QtCore.QPointF(-100.0, -1.7455), object())

		assert len(angles) == 1
		assert angles[0] == pytest.approx(math.radians(2), abs=0.0001)
	finally:
		_dispose_session(session)


#============================================
def test_edit_mode_unavailable_synchronized_route_is_inert(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A missing session route leaves a synchronized selected-atom nudge unchanged."""
	session = _new_native_session(main_window, _ALIGN_CDML)
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	if not session.replace_projection_from_backend_snapshot(session.backend_snapshot):
		raise AssertionError("Durable CDML projection is unavailable")
	session.mode_manager.set_mode("edit")
	mode = session.mode_manager.current_mode
	for item in session.scene.items():
		if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
			item.setSelected(True)
	before = session.backend_snapshot
	document = session.document
	undo_count = document.undo_stack.count()
	mode.set_atom_translate_operation(None)
	try:
		mode.key_press(_KeyEvent(PySide6.QtCore.Qt.Key.Key_Right))

		assert session.backend_snapshot == before
		assert session.document is document and document.undo_stack.count() == undo_count
	finally:
		_dispose_session(session)


#============================================
def test_geometry_repair_uses_backend_history_and_exact_reprojection(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A changed repair commits CDML once and backend undo restores its snapshot."""
	session = _new_native_session(main_window, _REPAIR_CDML)
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	before = session.backend_snapshot
	request = bkchem_qt.models.document_session.PersistentOperationRequest(
		"geometry.repair", "Normalize bond lengths",
		(
			("expected_revision", before.revision),
			("molecule_ids", ("m1",)),
			("kind", "normalize-bond-lengths"),
			("target_spacing_pt", 40.0),
		),
		frozenset({("molecule", "m1")}),
	)
	try:
		outcome = session.submit_persistent_operation(request)
		accepted = session.backend_snapshot
		undone = session.undo_backend()
		assert outcome.status == "accepted" and 'x="2.411cm"' in accepted.cdml
		assert undone.status == "accepted" and session.backend_snapshot.cdml == before.cdml
	finally:
		_dispose_session(session)


#============================================
def test_clean_geometry_uses_backend_history_and_fresh_projection(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A deterministic clean commits only through OASA and replaces Qt projection."""
	session = _new_native_session(main_window, _REPAIR_CDML)
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	before = session.backend_snapshot
	before_document = session.document
	request = bkchem_qt.models.document_session.PersistentOperationRequest(
		"geometry.repair", "Clean up geometry",
		(
			("expected_revision", before.revision),
			("molecule_ids", ("m1",)),
			("kind", "clean-geometry"),
			("target_spacing_pt", 40.0),
		),
		frozenset({("molecule", "m1")}),
	)
	try:
		outcome = session.submit_persistent_operation(request)
		accepted = session.backend_snapshot
		accepted_document = session.document
		undone = session.undo_backend()
		undone_snapshot = session.backend_snapshot
		undone_document = session.document
		redone = session.redo_backend()
		redone_document = session.document

		assert (
			outcome.status == "accepted"
			and accepted.cdml != before.cdml
			and accepted_document is not before_document
			and accepted_document.undo_stack.count() == 0
		)
		assert (
			undone.status == "accepted"
			and undone_snapshot.cdml == before.cdml
			and undone_document is not accepted_document
			and undone_document.undo_stack.count() == 0
		)
		assert (
			redone.status == "accepted"
			and session.backend_snapshot.cdml == accepted.cdml
			and redone_document is not undone_document
			and redone_document.undo_stack.count() == 0
		)
	finally:
		_dispose_session(session)


#============================================
def test_clean_geometry_action_submits_only_the_live_backend_session(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		) -> None:
	"""The visible action uses durable model IDs, backend history, and no Qt undo."""
	source = tmp_path / "backend-clean.cdml"
	source.write_text(_REPAIR_CDML, encoding="utf-8")
	assert main_window.open_file_path(str(source))
	session = main_window._active_session
	before = session.backend_snapshot
	before_document_id = id(session.document)
	try:
		bkchem_qt.actions.repair_actions._handle_clean_geometry(
			main_window, target_molecule_id="m1",
		)
		accepted = session.backend_snapshot
		accepted_document = session.document
		undone = session.undo_backend()
		undone_document = session.document
		redone = session.redo_backend()
		redone_document = session.document
		assert (
			accepted.cdml != before.cdml
			and id(accepted_document) != before_document_id
			and accepted_document.undo_stack.count() == 0
		)
		assert (
			undone.status == "accepted"
			and undone_document is not accepted_document
			and undone_document.undo_stack.count() == 0
			and redone.status == "accepted"
			and session.backend_snapshot.cdml == accepted.cdml
			and redone_document is not undone_document
			and redone_document.undo_stack.count() == 0
		)
	finally:
		_restore_blank_anchor(main_window, session)


#============================================
def test_snap_hex_projection_failure_recovers_only_accepted_snapshot(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""An accepted Snap retry projects its one accepted snapshot and selection."""
	session = _new_native_session(main_window, _REPAIR_CDML)
	before = session.backend_snapshot
	projection_snapshots = []
	fail_initial_projection = True

	def fail_then_reproject(snapshot: oasa.cdml_document.CDMLSnapshot) -> bool:
		"""Fail the first accepted projection before retrying through the public seam."""
		nonlocal fail_initial_projection
		projection_snapshots.append(snapshot)
		if fail_initial_projection:
			fail_initial_projection = False
			raise RuntimeError("intentional projection failure")
		return session.replace_projection_from_backend_snapshot(snapshot)

	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	assert session.replace_projection_from_backend_snapshot(before)
	atom_item = next(
		item for item in session.scene.items()
		if getattr(getattr(item, "atom_model", None), "backend_durable_id", None) == "a1"
	)
	atom_item.setSelected(True)
	del atom_item
	_install_projection_port(session, fail_then_reproject)
	request = bkchem_qt.models.document_session.PersistentOperationRequest(
		"geometry.repair", "Snap to hex grid",
		(
			("expected_revision", before.revision),
			("molecule_ids", ("m1",)),
			("kind", "snap-to-hex-grid"),
			("target_spacing_pt", 40.0),
		),
		frozenset({("molecule", "m1")}),
	)
	try:
		outcome = session.submit_persistent_operation(request)
		accepted = session.backend_snapshot
		recovered = session.retry_current_backend_projection()
		assert (
			outcome.status == "unavailable"
			and outcome.submitted
			and outcome.commit is not None
			and outcome.commit.snapshot == accepted
			and accepted.revision == before.revision + 1
		)
		assert (
			recovered.status == "accepted"
			and not recovered.submitted
			and recovered.commit is None
			and projection_snapshots == [accepted, accepted]
			and session.backend_snapshot == accepted
			and _selected_atom_ids(session) == {"a1"}
		)
	finally:
		_dispose_session(session)


#============================================
def test_ring_repair_projection_retry_uses_only_the_accepted_snapshot(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A failed ring projection recovers the accepted snapshot without replaying intent."""
	session = _new_native_session(main_window, _RING_REPAIR_CDML)
	before = session.backend_snapshot
	projection_snapshots = []

	def fail_then_reproject(snapshot: oasa.cdml_document.CDMLSnapshot) -> bool:
		"""Report one unavailable projection, then install the exact retry snapshot."""
		projection_snapshots.append(snapshot)
		if len(projection_snapshots) == 1:
			return _projection_unavailable(snapshot)
		return session.replace_projection_from_backend_snapshot(snapshot)

	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	if not session.replace_projection_from_backend_snapshot(before):
		raise AssertionError("Durable CDML projection is unavailable")
	_install_projection_port(session, fail_then_reproject)
	request = bkchem_qt.models.document_session.PersistentOperationRequest(
		"geometry.repair", "Normalize ring structures",
		(
			("expected_revision", before.revision),
			("molecule_ids", ("m1",)),
			("kind", "normalize-rings"),
			("target_spacing_pt", 40.0),
		),
		frozenset({("molecule", "m1")}),
	)
	try:
		outcome = session.submit_persistent_operation(request)
		accepted = session.backend_snapshot
		recovered = session.retry_current_backend_projection()
		accepted_before_retry = (
			outcome.status == "unavailable"
			and outcome.submitted
			and accepted.revision == before.revision + 1
		)
		final_snapshot_only = projection_snapshots == [accepted, accepted]

		assert accepted_before_retry
		assert recovered.status == "accepted" and not recovered.submitted and final_snapshot_only
	finally:
		_dispose_session(session)


#============================================
def test_draw_structure_blank_pair_records_backend_history_and_reprojects(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A blank Draw gesture becomes one OASA revision and canonical projection."""
	session = _new_native_session(main_window, '<cdml version="26.07"></cdml>')
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	before = session.backend_snapshot
	request = bkchem_qt.models.document_session.PersistentOperationRequest(
		"draw.structure", "Draw bonded pair",
		(
			("expected_revision", before.revision),
			("kind", "create-bonded-pair"),
			("source_position", (10.0, 20.0)),
			("target_position", (40.0, 20.0)),
			("element", "C"),
			("bond_type", "n"),
			("bond_order", 1),
			("simple_double", False),
		),
	)
	try:
		outcome = session.submit_persistent_operation(request)
		assert (
			outcome.status == "accepted"
			and outcome.commit is not None
			and outcome.commit.snapshot.revision == before.revision + 1
			and session.backend_projection_synchronized
		)
		assert session._backend_history.can_undo
	finally:
		_dispose_session(session)


#============================================
def test_draw_structure_exposes_plain_backend_durable_identity(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A Draw caller receives durable IDs without a Qt scene-object reference."""
	session = _new_native_session(main_window, '<cdml version="26.07"></cdml>')
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	request = bkchem_qt.models.document_session.PersistentOperationRequest(
		"draw.structure", "Draw bonded pair",
		(
			("expected_revision", session.backend_snapshot.revision),
			("kind", "create-bonded-pair"),
			("source_position", (10.0, 20.0)),
			("target_position", (40.0, 20.0)),
			("element", "C"),
			("bond_type", "n"),
			("bond_order", 1),
			("simple_double", False),
		),
	)
	try:
		outcome = session.submit_persistent_operation(request)
		result = outcome.structural_result
		assert result is not None and result.created_molecule_id in outcome.commit.cdml
		assert all(isinstance(identifier, str) for identifier in result.created_atom_ids)
	finally:
		_dispose_session(session)


#============================================
def test_draw_structure_projection_recovery_never_resubmits_acceptance(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Projection recovery uses the accepted snapshot without replaying Draw intent."""
	session = _new_native_session(main_window, '<cdml version="26.07"></cdml>')
	backend_calls = []
	projection_snapshots = []
	original_edit = session._backend_session.edit_structure

	def record_edit(
			request: oasa.cdml_document.CDMLStructuralEditRequest,
			) -> oasa.cdml_document.CDMLStructuralEditResult:
		"""Record one direct backend operation while preserving its real behavior."""
		backend_calls.append(request)
		return original_edit(request)

	def fail_then_reproject(snapshot: oasa.cdml_document.CDMLSnapshot) -> bool:
		"""Make the first authoritative installation fail and the retry succeed."""
		projection_snapshots.append(snapshot)
		if len(projection_snapshots) == 1:
			raise RuntimeError("intentional projection failure")
		return _projection_installed(snapshot)

	monkeypatch.setattr(session._backend_session, "edit_structure", record_edit)
	_install_projection_port(session, fail_then_reproject)
	request = bkchem_qt.models.document_session.PersistentOperationRequest(
		"draw.structure", "Draw bonded pair",
		(
			("expected_revision", session.backend_snapshot.revision),
			("kind", "create-bonded-pair"),
			("source_position", (10.0, 20.0)),
			("target_position", (40.0, 20.0)),
			("element", "C"),
			("bond_type", "n"),
			("bond_order", 1),
			("simple_double", False),
		),
	)
	try:
		outcome = session.submit_persistent_operation(request)
		accepted = session.backend_snapshot
		recovered = session.retry_current_backend_projection()
		assert outcome.status == "unavailable" and outcome.submitted
		assert outcome.structural_result is not None and recovered.status == "accepted"
		assert len(backend_calls) == 1 and projection_snapshots == [accepted, accepted]
	finally:
		_dispose_session(session)


#============================================
def test_draw_structure_rejection_keeps_backend_state_and_history_unchanged(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Malformed envelopes and rejected OASA edits preserve the current session."""
	session = _new_native_session(main_window, '<cdml version="26.07"></cdml>')
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	before = session.backend_snapshot
	malformed = bkchem_qt.models.document_session.PersistentOperationRequest(
		"draw.structure", "Draw bonded pair",
		(
			("expected_revision", before.revision),
			("kind", "create-bonded-pair"),
			("source_position", (10.0, 20.0)),
			("target_position", (40.0, 20.0)),
			("element", "C"),
			("bond_type", "n"),
			("bond_order", 1),
			("simple_double", False),
		),
		frozenset({("molecule", "unexpected")}),
	)
	rejected_by_oasa = bkchem_qt.models.document_session.PersistentOperationRequest(
		"draw.structure", "Draw bonded pair",
		(
			("expected_revision", before.revision),
			("kind", "create-bonded-pair"),
			("source_position", (10.0, 20.0)),
			("target_position", (40.0, 20.0)),
			("element", "NotAnElement"),
			("bond_type", "n"),
			("bond_order", 1),
			("simple_double", False),
		),
	)
	try:
		assert session.submit_persistent_operation(malformed).status == "rejected"
		assert session.submit_persistent_operation(rejected_by_oasa).status == "rejected"
		assert session.backend_snapshot == before and not session._backend_history.can_undo
	finally:
		_dispose_session(session)


#============================================
def test_bond_order_set_uses_backend_history_reprojection_and_durable_selection(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""An exact bond order commit remains owned by OASA through undo and redo."""
	session = _new_native_session(main_window, _ALIGN_CDML)
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	if not session.replace_projection_from_backend_snapshot(session.backend_snapshot):
		raise AssertionError("Durable CDML projection is unavailable")
	before = session.backend_snapshot
	try:
		outcome = session.submit_bond_order("m1", "b1", 2)
		accepted = session.backend_snapshot
		assert outcome.status == "accepted" and 'type="w2"' in accepted.cdml
		assert _selected_bond_ids(session) == {"b1"}
		assert session.undo_backend().status == "accepted"
		assert session.backend_snapshot.cdml == before.cdml
		assert session.redo_backend().status == "accepted"
		assert session.backend_snapshot.cdml == accepted.cdml
	finally:
		_dispose_session(session)


#============================================
def test_bond_order_set_semantic_noop_retains_projection_and_history(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A matching order stays entirely within the current backend snapshot."""
	session = _new_native_session(main_window, _ALIGN_CDML)
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	if not session.replace_projection_from_backend_snapshot(session.backend_snapshot):
		raise AssertionError("Durable CDML projection is unavailable")
	before = session.backend_snapshot
	document = session.document
	try:
		outcome = session.submit_bond_order("m1", "b1", 1)

		assert (
			outcome.status == "accepted"
			and outcome.commit is None
			and session.backend_snapshot == before
			and session.document is document
			and not session._backend_history.can_undo
			and document.undo_stack.count() == 0
		)
	finally:
		_dispose_session(session)


#============================================
def test_bond_order_set_projection_retry_never_resubmits_acceptance(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A failed accepted bond projection retries only its exact backend snapshot."""
	session = _new_native_session(main_window, _ALIGN_CDML)
	calls = []
	backend_calls = []
	set_bond_order = session._backend_session.set_bond_order

	def count_bond_order(
			request: oasa.cdml_document.CDMLBondOrderEditRequest,
			) -> oasa.cdml_document.CDMLBondOrderEditResult:
		"""Record the sole backend exact-order execution."""
		backend_calls.append(request)
		return set_bond_order(request)

	def fail_once(snapshot: oasa.cdml_document.CDMLSnapshot) -> bool:
		"""Reject one projection then install the retry normally."""
		calls.append(snapshot.revision)
		if len(calls) == 1:
			return _projection_unavailable(snapshot)
		return session.replace_projection_from_backend_snapshot(snapshot)

	session._backend_session.set_bond_order = count_bond_order
	_install_projection_port(session, fail_once)
	try:
		outcome = session.submit_bond_order("m1", "b1", 2)
		accepted_revision = session.backend_snapshot.revision
		retried = session.retry_current_backend_projection()

		assert outcome.status == "unavailable" and retried.status == "accepted"
		assert (
			len(backend_calls) == 1
			and calls == [accepted_revision, accepted_revision]
			and _selected_bond_ids(session) == {"b1"}
		)
	finally:
		_dispose_session(session)


#============================================
def test_bond_type_set_projection_retry_never_resubmits_acceptance(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A failed accepted type projection retries only its exact backend snapshot."""
	session = _new_native_session(main_window, _ALIGN_CDML)
	calls = []
	backend_calls = []
	set_bond_type = session._backend_session.set_bond_type

	def count_bond_type(
			request: oasa.cdml_document.CDMLBondTypeEditRequest,
			) -> oasa.cdml_document.CDMLBondTypeEditResult:
		"""Record the sole backend exact-type execution."""
		backend_calls.append(request)
		return set_bond_type(request)

	def fail_once(snapshot: oasa.cdml_document.CDMLSnapshot) -> bool:
		"""Reject one projection then install the retry normally."""
		calls.append(snapshot.revision)
		if len(calls) == 1:
			return _projection_unavailable(snapshot)
		return session.replace_projection_from_backend_snapshot(snapshot)

	session._backend_session.set_bond_type = count_bond_type
	_install_projection_port(session, fail_once)
	try:
		outcome = session.submit_bond_type("m1", "b1", "h")
		accepted_revision = session.backend_snapshot.revision
		retried = session.retry_current_backend_projection()

		assert outcome.status == "unavailable" and retried.status == "accepted"
		assert (
			len(backend_calls) == 1
			and calls == [accepted_revision, accepted_revision]
			and _selected_bond_ids(session) == {"b1"}
		)
	finally:
		_dispose_session(session)


#============================================
def test_atom_element_set_uses_backend_history_and_exact_reprojection(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""An AtomMode substitution commits once and backend navigation restores CDML."""
	session = _new_native_session(main_window, _ELEMENT_CDML)
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	before = session.backend_snapshot
	request = bkchem_qt.models.document_session.PersistentOperationRequest(
		"atom.element.set", "Set atom element",
		(
			("expected_revision", before.revision),
			("molecule_id", "m1"),
			("atom_id", "a1"),
			("element", "N"),
		),
		frozenset({("molecule", "m1"), ("atom", "a1")}))
	try:
		outcome = session.submit_persistent_operation(request)
		accepted = session.backend_snapshot
		undone = session.undo_backend()
		assert (
			outcome.status == "accepted"
			and 'name="N" charge="1"' in accepted.cdml
			and undone.status == "accepted"
			and session.backend_snapshot.cdml == before.cdml
		)
		redone = session.redo_backend()
		assert (
			redone.status == "accepted"
			and session.backend_snapshot.cdml == accepted.cdml
			and session.backend_projection_synchronized
		)
	finally:
		_dispose_session(session)


#============================================
def test_atom_element_set_rejections_leave_authoritative_state_unchanged(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Malformed envelopes and rejected elements keep the current backend snapshot."""
	session = _new_native_session(main_window, _ELEMENT_CDML)
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	before = session.backend_snapshot
	malformed = bkchem_qt.models.document_session.PersistentOperationRequest(
		"atom.element.set", "Set atom element",
		(
			("expected_revision", before.revision),
			("molecule_id", "m1"),
			("atom_id", "a1"),
			("element", "N"),
		),
		frozenset({("molecule", "m1"), ("atom", "wrong")}))
	rejected_by_oasa = bkchem_qt.models.document_session.PersistentOperationRequest(
		"atom.element.set", "Set atom element",
		(
			("expected_revision", before.revision),
			("molecule_id", "m1"),
			("atom_id", "a1"),
			("element", "NotAnElement"),
		),
		frozenset({("molecule", "m1"), ("atom", "a1")}))
	try:
		assert (
			session.submit_persistent_operation(malformed).status,
			session.submit_persistent_operation(rejected_by_oasa).status,
		) == ("rejected", "rejected")
		assert session.backend_snapshot == before and not session.can_undo_backend
	finally:
		_dispose_session(session)


#============================================
def test_atom_element_set_projection_recovery_never_resubmits_acceptance(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A failed projection recovers the accepted atom snapshot without a second edit."""
	session = _new_native_session(main_window, _ELEMENT_CDML)
	projection_failed = False

	def fail_then_reproject(snapshot: oasa.cdml_document.CDMLSnapshot) -> bool:
		"""Fail initial projection and accept the exact-snapshot retry."""
		nonlocal projection_failed
		if not projection_failed:
			projection_failed = True
			raise RuntimeError("intentional projection failure")
		return _projection_installed(snapshot)

	_install_projection_port(session, fail_then_reproject)
	request = bkchem_qt.models.document_session.PersistentOperationRequest(
		"atom.element.set", "Set atom element",
		(
			("expected_revision", session.backend_snapshot.revision),
			("molecule_id", "m1"),
			("atom_id", "a1"),
			("element", "N"),
		),
		frozenset({("molecule", "m1"), ("atom", "a1")}))
	try:
		outcome = session.submit_persistent_operation(request)
		accepted = session.backend_snapshot
		recovered = session.retry_current_backend_projection()
		assert outcome.status == "unavailable" and outcome.submitted
		assert (
			recovered.status == "accepted"
			and session.backend_snapshot == accepted
		)
	finally:
		_dispose_session(session)


#============================================
def test_same_tab_projection_failure_retains_root_with_session_until_retry(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A replacement failure preserves its accepted snapshot and owned root."""
	session = _new_native_session(main_window, _ELEMENT_CDML)
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	assert session.replace_projection_from_backend_snapshot(session.backend_snapshot)
	old_atom_item = next(
		item for item in session.scene.items()
		if getattr(item, "atom_model", None) is session.document.molecules[0].atoms[0]
	)
	real_delete = shiboken6.delete
	failed_once = False

	#============================================
	def fail_one_old_atom_delete(item: object) -> None:
		"""Retain one old projection root at its explicit native boundary."""
		nonlocal failed_once
		if item is old_atom_item and not failed_once:
			failed_once = True
			raise RuntimeError("injected same-tab projection retirement failure")
		real_delete(item)

	monkeypatch.setattr(
		bkchem_qt.canvas.graphics_retirement.shiboken6,
		"delete", fail_one_old_atom_delete,
	)
	request = bkchem_qt.models.document_session.PersistentOperationRequest(
		"atom.element.set", "Set atom element",
		(
			("expected_revision", session.backend_snapshot.revision),
			("molecule_id", "m1"),
			("atom_id", "a1"),
			("element", "N"),
		),
		frozenset({("molecule", "m1"), ("atom", "a1")}))
	try:
		outcome = session.submit_persistent_operation(request)
		accepted = session.backend_snapshot
		assert (
			outcome.status == "unavailable"
			and outcome.commit is not None
			and outcome.commit.snapshot == accepted
			and "name=\"N\"" in accepted.cdml
			and session._projection_retirement_reaper.owns_detached_root(old_atom_item)
		)

		monkeypatch.undo()
		session._projection_retirement_reaper.drain()
		recovered = session.retry_current_backend_projection()
		assert (
			not shiboken6.isValid(old_atom_item)
			and recovered.status == "accepted"
			and session.backend_projection_synchronized
		)
	finally:
		_dispose_session(session)


#============================================
def test_session_close_transfers_failed_scene_transition_as_one_aggregate(
		main_window: bkchem_qt.main_window.MainWindow,
		qapp: PySide6.QtWidgets.QApplication,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A failed replacement scene transition stays owned through tab close."""
	session = _new_native_session(main_window, _ELEMENT_CDML)
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	assert session.replace_projection_from_backend_snapshot(session.backend_snapshot)
	real_remove = bkchem_qt.canvas.graphics_retirement.GraphicsRetirementCoordinator._remove_scene_root
	failed_roots = []

	#============================================
	def fail_old_scene_removal(
			self: bkchem_qt.canvas.graphics_retirement.GraphicsRetirementCoordinator,
			scene: PySide6.QtWidgets.QGraphicsScene,
			root: PySide6.QtWidgets.QGraphicsItem,
			) -> None:
		"""Leave one old root scene-owned until the MainWindow retry boundary."""
		if not failed_roots or root is failed_roots[0]:
			if not failed_roots:
				failed_roots.append(root)
			raise RuntimeError("injected replacement scene-removal failure")
		real_remove(self, scene, root)

	monkeypatch.setattr(
		bkchem_qt.canvas.graphics_retirement.GraphicsRetirementCoordinator,
		"_remove_scene_root", fail_old_scene_removal,
	)
	monkeypatch.setattr(session._projection_retirement_reaper, "drain", lambda: None)
	request = bkchem_qt.models.document_session.PersistentOperationRequest(
		"atom.element.set", "Set atom element",
		(
			("expected_revision", session.backend_snapshot.revision),
			("molecule_id", "m1"),
			("atom_id", "a1"),
			("element", "N"),
		),
		frozenset({("molecule", "m1"), ("atom", "a1")}))
	try:
		outcome = session.submit_persistent_operation(request)
		assert outcome.status == "unavailable" and outcome.commit is not None
		_dispose_session(session)
		pending = next(iter(main_window._pending_session_deletions.values()))
		records = pending.retained_graphics_records
		assert (
			failed_roots
			and records is not None
			and any(
				failed_roots[0] in record.roots
				for record in records.scene_projections
			)
		)

		monkeypatch.undo()
		assert bkchem_qt.main_window.drain_pending_session_deletions(qapp, main_window)
		assert not shiboken6.isValid(failed_roots[0])
	finally:
		monkeypatch.undo()


#============================================
def test_session_disposal_transfers_replacement_failure_to_window_reaper(
		main_window: bkchem_qt.main_window.MainWindow,
		qapp: PySide6.QtWidgets.QApplication,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Terminal disposal transfers a live replacement sentinel to MainWindow."""
	session = _new_native_session(main_window, _ELEMENT_CDML)
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	assert session.replace_projection_from_backend_snapshot(session.backend_snapshot)
	old_atom_item = next(
		item for item in session.scene.items()
		if getattr(item, "atom_model", None) is session.document.molecules[0].atoms[0]
	)
	real_delete = shiboken6.delete
	session_disposed = False

	#============================================
	def fail_old_atom_delete(item: object) -> None:
		"""Keep the retired old root live until the window owns its retry."""
		if item is old_atom_item:
			raise RuntimeError("injected replacement record transfer failure")
		real_delete(item)

	monkeypatch.setattr(
		bkchem_qt.canvas.graphics_retirement.shiboken6,
		"delete", fail_old_atom_delete,
	)
	request = bkchem_qt.models.document_session.PersistentOperationRequest(
		"atom.element.set", "Set atom element",
		(
			("expected_revision", session.backend_snapshot.revision),
			("molecule_id", "m1"),
			("atom_id", "a1"),
			("element", "N"),
		),
		frozenset({("molecule", "m1"), ("atom", "a1")}))
	try:
		assert session.submit_persistent_operation(request).status == "unavailable"
		_dispose_session(session)
		session_disposed = True
		pending = next(iter(main_window._pending_session_deletions.values()))
		assert (
			shiboken6.isValid(old_atom_item)
			and old_atom_item in pending.retained_detached_graphics.roots
		)

		monkeypatch.undo()
		assert bkchem_qt.main_window.drain_pending_session_deletions(qapp, main_window)
		assert not shiboken6.isValid(old_atom_item)
	finally:
		monkeypatch.undo()
		if not session_disposed:
			_dispose_session(session)


#============================================
def test_destroyed_session_retries_transient_graphics_failure_on_event_loop(
		main_window: bkchem_qt.main_window.MainWindow,
		qapp: PySide6.QtWidgets.QApplication,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A transient MainWindow retry resolves from ordinary Qt event delivery."""
	session = _new_native_session(main_window, _ELEMENT_CDML)
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	assert session.replace_projection_from_backend_snapshot(session.backend_snapshot)
	old_atom_item = next(
		item for item in session.scene.items()
		if getattr(item, "atom_model", None) is session.document.molecules[0].atoms[0]
	)
	real_delete = shiboken6.delete

	#============================================
	def fail_old_atom_delete(item: object) -> None:
		"""Keep one old atom live through the destroyed-callback retry."""
		if item is old_atom_item:
			raise RuntimeError("injected transient MainWindow retry failure")
		real_delete(item)

	monkeypatch.setattr(
		bkchem_qt.canvas.graphics_retirement.shiboken6,
		"delete", fail_old_atom_delete,
	)
	request = bkchem_qt.models.document_session.PersistentOperationRequest(
		"atom.element.set", "Set atom element",
		(
			("expected_revision", session.backend_snapshot.revision),
			("molecule_id", "m1"),
			("atom_id", "a1"),
			("element", "N"),
		),
		frozenset({("molecule", "m1"), ("atom", "a1")}))
	try:
		assert session.submit_persistent_operation(request).status == "unavailable"
		_dispose_session(session)
		PySide6.QtCore.QCoreApplication.sendPostedEvents(
			None, PySide6.QtCore.QEvent.Type.DeferredDelete,
		)
		assert (
			main_window._pending_session_deletions
			and main_window._pending_session_graphics_retry_scheduled
			and shiboken6.isValid(old_atom_item)
		)

		monkeypatch.undo()
		qapp.processEvents()
		assert not main_window._pending_session_deletions
		assert not shiboken6.isValid(old_atom_item)
	finally:
		monkeypatch.undo()


#============================================
def test_session_close_transfers_failed_scene_decoration_to_window_reaper(
		main_window: bkchem_qt.main_window.MainWindow,
		qapp: PySide6.QtWidgets.QApplication,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A close retains a failed paper root under its session-owned terminal path."""
	session = _new_native_session(main_window, _ELEMENT_CDML)
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	request = bkchem_qt.models.document_session.PersistentOperationRequest(
		"atom.element.set", "Set atom element",
		(
			("expected_revision", session.backend_snapshot.revision),
			("molecule_id", "m1"),
			("atom_id", "a1"),
			("element", "N"),
		),
		frozenset({("molecule", "m1"), ("atom", "a1")}))
	accepted = session.submit_persistent_operation(request)
	paper = session.scene._paper_item
	real_delete = shiboken6.delete

	#============================================
	def fail_paper_delete(item: object) -> None:
		"""Keep the session-owned paper wrapper live until controlled retry."""
		if item is paper:
			raise RuntimeError("injected session paper retirement failure")
		real_delete(item)

	monkeypatch.setattr(
		bkchem_qt.canvas.graphics_retirement.shiboken6,
		"delete", fail_paper_delete,
	)
	try:
		with pytest.raises(RuntimeError, match="Session was queued after a disposal failure"):
			_dispose_session(session)
		pending = next(
			record for record in main_window._pending_session_deletions.values()
			if (
				record.retained_detached_graphics is not None
				and paper in record.retained_detached_graphics.roots
			)
		)
		assert (
			accepted.status == "accepted"
			and accepted.commit is not None
			and "name=\"N\"" in accepted.commit.snapshot.cdml
			and shiboken6.isValid(paper)
			and paper in pending.retained_detached_graphics.roots
			and not bkchem_qt.canvas.graphics_retirement
			.detached_graphics_retirement_reaper.owns_detached_root(paper)
		)

		monkeypatch.undo()
		assert bkchem_qt.main_window.drain_pending_session_deletions(qapp, main_window)
		assert not shiboken6.isValid(paper)
	finally:
		monkeypatch.undo()


#============================================
def test_template_insertion_uses_backend_history_and_canonical_reprojection(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A detached template placement commits through backend history and CDML."""
	session = _new_native_session(main_window, '<cdml version="26.07"></cdml>')
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	before = session.backend_snapshot
	request = bkchem_qt.models.document_session.PersistentOperationRequest(
		"template.insert", "Place template Me",
		(
			("expected_revision", before.revision),
			("template_name", "Me"),
			("anchor", (120.0, 80.0)),
		),
	)
	try:
		outcome = session.submit_persistent_operation(request)
		accepted = session.backend_snapshot
		undone = session.undo_backend()
		assert (
			outcome.status == "accepted"
			and outcome.commit is not None
			and outcome.commit.id_map
			and "<molecule" in accepted.cdml
			and undone.status == "accepted"
			and session.backend_snapshot.cdml == before.cdml
		)
		redone = session.redo_backend()
		assert (
			redone.status == "accepted"
			and session.backend_snapshot.cdml == accepted.cdml
			and session.backend_projection_synchronized
		)
	finally:
		_dispose_session(session)


#============================================
def test_session_injects_plain_template_catalog_for_mode_submission(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""The session supplies OASA catalog values before TemplateMode submits one."""
	monkeypatch.setattr(
		oasa.template_placement, "system_template_names", lambda: ("Me",),
	)
	session = _new_native_session(main_window, '<cdml version="26.07"></cdml>')
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	session.mode_manager.set_mode("template")
	mode = session.mode_manager.current_mode
	if not isinstance(mode, bkchem_qt.modes.template_mode.TemplateMode):
		raise AssertionError("Session did not install TemplateMode")
	try:
		mode.mouse_press(PySide6.QtCore.QPointF(120.0, 80.0), None)

		assert mode.template_names == ("Me",) and "<molecule" in session.backend_snapshot.cdml
	finally:
		_dispose_session(session)


#============================================
def test_template_insertion_selects_the_backend_mapped_root_molecule(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A template result selects only the root allocated by OASA acceptance."""
	session = _new_native_session(main_window, '<cdml version="26.07"></cdml>')
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	request = bkchem_qt.models.document_session.PersistentOperationRequest(
		"template.insert", "Place template Me",
		(
			("expected_revision", session.backend_snapshot.revision),
			("template_name", "Me"),
			("anchor", (120.0, 80.0)),
		),
	)
	try:
		outcome = session.submit_persistent_operation(request)
		if outcome.commit is None:
			raise AssertionError("Template insertion did not return an accepted commit")
		accepted = oasa.cdml_document.CDMLDocument.parse(
			outcome.commit.cdml, validation="compat",
		)
		mapped_root_ids = {
			identifier
			for identifier in outcome.commit.id_map.values()
			if accepted.find_by_id(identifier).local_name == "molecule"
		}
		selected_molecule_ids = {
			getattr(getattr(item, "molecule_model", None), "mol_id", None)
			for item in session.scene.selectedItems()
		}

		assert outcome.status == "accepted" and selected_molecule_ids == mapped_root_ids
	finally:
		_dispose_session(session)


#============================================
def test_template_insertion_rejects_invalid_plain_envelopes(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Invalid placement inputs leave the authoritative snapshot and history intact."""
	session = _new_native_session(main_window, '<cdml version="26.07"></cdml>')
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	before = session.backend_snapshot
	malformed_payload = bkchem_qt.models.document_session.PersistentOperationRequest(
		"template.insert", "Place template Me",
		(
			("expected_revision", before.revision),
			("template_name", "Me"),
			("anchor", (120.0,)),
		),
	)
	invalid_target = bkchem_qt.models.document_session.PersistentOperationRequest(
		"template.insert", "Place template Me",
		(
			("expected_revision", before.revision),
			("template_name", "Me"),
			("anchor", (120.0, 80.0)),
		),
		frozenset({("molecule", "unexpected")}),
	)
	invalid_name = bkchem_qt.models.document_session.PersistentOperationRequest(
		"template.insert", "Place unknown template",
		(
			("expected_revision", before.revision),
			("template_name", "not-a-known-template"),
			("anchor", (120.0, 80.0)),
		),
	)
	try:
		assert (
			session.submit_persistent_operation(malformed_payload).status,
			session.submit_persistent_operation(invalid_target).status,
			session.submit_persistent_operation(invalid_name).status,
		) == ("rejected", "rejected", "rejected")
		assert session.backend_snapshot == before and not session.can_undo_backend
	finally:
		_dispose_session(session)


#============================================
def test_template_insertion_rejects_stale_request_before_oasa_preparation(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A stale request is rejected before template preparation can begin."""
	session = _new_native_session(main_window, '<cdml version="26.07"></cdml>')
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	before = session.backend_snapshot

	def reject_unexpected_preparation(_request: object) -> object:
		"""Make an accidental stale-path preparation fail this focused test."""
		raise AssertionError("stale template request reached OASA preparation")

	monkeypatch.setattr(
		oasa.template_placement,
		"prepare_template_molecule_insertion",
		reject_unexpected_preparation,
	)
	request = bkchem_qt.models.document_session.PersistentOperationRequest(
		"template.insert", "Place template Me",
		(
			("expected_revision", before.revision + 1),
			("template_name", "Me"),
			("anchor", (120.0, 80.0)),
		),
	)
	try:
		outcome = session.submit_persistent_operation(request)
		assert (
			outcome.status == "rejected"
			and session.backend_snapshot == before
			and not session.can_undo_backend
		)
	finally:
		_dispose_session(session)


#============================================
def test_top_level_delete_uses_backend_history_and_exact_reprojection(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A direct-root Delete commits only through backend revision history."""
	session = _new_native_session(main_window, _DELETE_CDML)
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	before = session.backend_snapshot
	request = bkchem_qt.models.document_session.PersistentOperationRequest(
		"top-level.delete", "Delete",
		(("expected_revision", before.revision), ("root_ids", ("arrow1",))),
		frozenset({("presentation", "arrow1")}),
	)
	try:
		outcome = session.submit_persistent_operation(request)
		accepted = session.backend_snapshot
		assert session._backend_history.can_undo
		undone = session.undo_backend()
		assert outcome.status == "accepted" and 'id="arrow1"' not in accepted.cdml
		assert undone.status == "accepted" and session.backend_snapshot.cdml == before.cdml
	finally:
		_dispose_session(session)


#============================================
def test_edit_mode_delete_of_complete_presentation_root_uses_backend(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Edit Delete sends a selected durable arrow through the session operation."""
	session = _new_native_session(main_window, _DELETE_CDML)
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	assert session.replace_projection_from_backend_snapshot(session.backend_snapshot)
	scene = session.scene
	arrow_item = next(
		item for item in scene.items()
		if getattr(getattr(item, "document_object_model", None), "object_id", None) == "arrow1"
	)
	edit_mode = session.mode_manager._modes["edit"]
	undo_count = session.document.undo_stack.count()
	try:
		arrow_item.setSelected(True)
		edit_mode._delete_selected()
		assert 'id="arrow1"' not in session.backend_snapshot.cdml
		assert session.document.undo_stack.count() == undo_count
		assert session.backend_projection_synchronized
	finally:
		_dispose_session(session)


#============================================
def test_edit_mode_unavailable_complete_root_delete_keeps_backend_and_qt_unchanged(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A formed root-delete request never falls through to local mutation."""
	session = _new_native_session(main_window, _DELETE_CDML)
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	assert session.replace_projection_from_backend_snapshot(session.backend_snapshot)
	scene = session.scene
	arrow_item = next(
		item for item in scene.items()
		if getattr(getattr(item, "document_object_model", None), "object_id", None) == "arrow1"
	)
	edit_mode = session.mode_manager._modes["edit"]
	messages = []
	edit_mode.status_message.connect(messages.append)
	before = session.backend_snapshot
	undo_count = session.document.undo_stack.count()
	try:
		session.clear_projection_lifecycle_port()
		arrow_item.setSelected(True)
		edit_mode._delete_selected()
		assert (session.backend_snapshot, session.document.undo_stack.count()) == (before, undo_count)
		assert arrow_item in scene.items()
		assert messages == ["Delete unavailable for this document"]
	finally:
		edit_mode.status_message.disconnect(messages.append)
		_dispose_session(session)


#============================================
def test_edit_mode_partial_mixed_delete_is_inert_while_synchronized(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A synchronized atom/presentation selection does not enter local isolation."""
	session = _new_native_session(main_window, _REPAIR_CDML)
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	assert session.replace_projection_from_backend_snapshot(session.backend_snapshot)
	atom_item = next(
		item for item in session.scene.items()
		if getattr(getattr(item, "atom_model", None), "atom_id", None) == "a1"
	)
	arrow_item = next(
		item for item in session.scene.items()
		if getattr(getattr(item, "document_object_model", None), "object_id", None) == "arrow1"
	)
	edit_mode = session.mode_manager._modes["edit"]
	before = session.backend_snapshot
	undo_count = session.document.undo_stack.count()
	try:
		atom_item.setSelected(True)
		arrow_item.setSelected(True)
		edit_mode._delete_selected()
		assert session.backend_snapshot == before and not session.legacy_isolated
		assert session.document.undo_stack.count() == undo_count
		assert atom_item in session.scene.items() and arrow_item in session.scene.items()
	finally:
		_dispose_session(session)


#============================================
def test_edit_mode_delete_of_complete_molecule_uses_backend(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Edit Delete treats every selected primary item as one backend molecule root."""
	session = _new_native_session(main_window, _DELETE_CDML)
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	assert session.replace_projection_from_backend_snapshot(session.backend_snapshot)
	scene = session.scene
	primary_items = [
		item for item in scene.items()
		if getattr(getattr(item, "atom_model", None), "atom_id", None) == "a1"
	]
	assert primary_items
	edit_mode = session.mode_manager._modes["edit"]
	try:
		for item in primary_items:
			item.setSelected(True)
		edit_mode._delete_selected()
		assert 'id="m1"' not in session.backend_snapshot.cdml
		assert session.backend_projection_synchronized
	finally:
		_dispose_session(session)


#============================================
def test_normalize_length_menu_action_commits_backend_repair_and_reprojects(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		) -> None:
	"""The registered Repair action uses backend history instead of local moves."""
	source = tmp_path / "backend-repair.cdml"
	source.write_text(_REPAIR_CDML, encoding="utf-8")
	assert main_window.open_file_path(str(source))
	session = main_window._active_session
	before = session.backend_snapshot

	try:
		main_window._registry.get("repair.normalize_bond_lengths").handler()
		assert session.backend_snapshot.revision == before.revision + 1
		assert 'x="2.411cm"' in session.backend_snapshot.cdml
		assert session.backend_projection_synchronized
		assert session._backend_history.can_undo
	finally:
		_restore_blank_anchor(main_window, session)


#============================================
def test_snap_hex_menu_action_uses_backend_history_and_preserves_selection(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		) -> None:
	"""Visible Snap replaces its projection and keeps its durable selection."""
	source = tmp_path / "backend-snap.cdml"
	source.write_text(_REPAIR_CDML, encoding="utf-8")
	assert main_window.open_file_path(str(source))
	session = main_window._active_session
	before = session.backend_snapshot
	before_document_id = id(session.document)
	for item in session.scene.items():
		if getattr(getattr(item, "atom_model", None), "backend_durable_id", None) == "a1":
			item.setSelected(True)
	del item
	try:
		main_window._registry.get("repair.snap_to_hex_grid").handler()
		accepted = session.backend_snapshot
		accepted_document = session.document
		assert (
			accepted.revision == before.revision + 1
			and id(accepted_document) != before_document_id
			and accepted_document.undo_stack.count() == 0
			and _selected_atom_ids(session) == {"a1"}
		)
		undone = session.undo_backend()
		redone = session.redo_backend()
		assert (
			undone.status == "accepted"
			and redone.status == "accepted"
			and session.backend_snapshot.cdml == accepted.cdml
			and session.document.undo_stack.count() == 0
		)
	finally:
		_restore_blank_anchor(main_window, session)


#============================================
def test_normalize_angle_menu_action_uses_backend_history_and_reprojects(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		) -> None:
	"""Visible Angle repair replaces Qt state and restores accepted backend history."""
	source = tmp_path / "backend-angle.cdml"
	source.write_text(_ANGLE_REPAIR_CDML, encoding="utf-8")
	assert main_window.open_file_path(str(source))
	session = main_window._active_session
	before = session.backend_snapshot
	before_document = session.document
	for item in session.scene.items():
		if getattr(getattr(item, "atom_model", None), "backend_durable_id", None) == "a1":
			selected_item = item
			selected_item.setSelected(True)
			break
	else:
		raise AssertionError("fixture did not project a selectable durable atom")
	del item

	try:
		main_window._registry.get("repair.normalize_bond_angles").handler()
		accepted = session.backend_snapshot
		accepted_document = session.document
		accepted_selected_ids = _selected_atom_ids(session)
		assert not shiboken6.isValid(selected_item)
		undone = session.undo_backend()
		undone_snapshot = session.backend_snapshot
		redone = session.redo_backend()

		assert (
			accepted.revision == before.revision + 1
			and accepted.cdml != before.cdml
			and accepted_document is not before_document
			and accepted_document.undo_stack.count() == 0
			and accepted_selected_ids == {"a1"}
		)
		assert (
			undone.status == "accepted"
			and undone_snapshot.cdml == before.cdml
			and redone.status == "accepted"
			and session.backend_snapshot.cdml == accepted.cdml
			and session.document.undo_stack.count() == 0
		)
	finally:
		_restore_blank_anchor(main_window, session)


#============================================
def test_straighten_menu_action_uses_backend_history_and_reprojects(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		) -> None:
	"""Visible Straighten replaces the projection without Qt-local undo."""
	source = tmp_path / "backend-straighten.cdml"
	source.write_text(_STRAIGHTEN_REPAIR_CDML, encoding="utf-8")
	assert main_window.open_file_path(str(source))
	session = main_window._active_session
	before = session.backend_snapshot
	before_document = session.document
	for item in session.scene.items():
		if getattr(getattr(item, "atom_model", None), "backend_durable_id", None) == "a1":
			selected_item = item
			selected_item.setSelected(True)
			break
	else:
		raise AssertionError("fixture did not project a selectable durable atom")
	del item

	try:
		main_window._registry.get("repair.straighten_bonds").handler()
		accepted = session.backend_snapshot
		accepted_document = session.document
		assert not shiboken6.isValid(selected_item)
		undone = session.undo_backend()
		redone = session.redo_backend()

		assert (
			accepted.revision == before.revision + 1
			and accepted.cdml != before.cdml
			and accepted_document is not before_document
			and accepted_document.undo_stack.count() == 0
			and _selected_atom_ids(session) == {"a1"}
		)
		assert (
			undone.status == "accepted"
			and redone.status == "accepted"
			and session.backend_snapshot.cdml == accepted.cdml
			and session.document.undo_stack.count() == 0
		)
	finally:
		_restore_blank_anchor(main_window, session)


#============================================
def test_straighten_menu_noop_keeps_authoritative_revision_and_projection(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		) -> None:
	"""A canonical terminal bond has no history or projection replacement."""
	source = tmp_path / "backend-straighten-noop.cdml"
	source.write_text(_REPAIR_CDML, encoding="utf-8")
	assert main_window.open_file_path(str(source))
	session = main_window._active_session
	before = session.backend_snapshot
	before_document = session.document
	try:
		main_window._registry.get("repair.straighten_bonds").handler()

		assert (
			session.backend_snapshot == before
			and session.document is before_document
			and session.document.undo_stack.count() == 0
		)
	finally:
		_restore_blank_anchor(main_window, session)


#============================================
def test_imported_cdml_session_is_pathless_dirty_and_saves_exact_snapshot(
		qapp: PySide6.QtWidgets.QApplication,
		main_window: bkchem_qt.main_window.MainWindow,
		tmp_path: pathlib.Path,
		) -> None:
	"""External import state comes from the backend baseline, then Save publishes it."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_imported_cdml(
		_OPEN_ARROW_CDML,
	)
	session = bkchem_qt.models.document_session.DocumentSession(
		parent=main_window,
		theme_manager=main_window._theme_manager,
		prefs=main_window._prefs,
		mode_host=main_window,
		prepared_imported_cdml=prepared,
	)
	target = tmp_path / "imported.cdml"
	before_save = session.backend_snapshot
	assert before_save.is_dirty and session.document.file_path is None
	session.write_backend_snapshot(str(target))
	assert target.read_text(encoding="utf-8") == before_save.cdml
	_dispose_session(session)
	_drain_deferred_deletes(qapp, main_window)


#============================================
def test_worker_mol_open_replaces_same_tab_with_backend_dirty_exact_snapshot(
		main_window: bkchem_qt.main_window.MainWindow,
		tmp_path: pathlib.Path, qtbot: object,
		) -> None:
	"""A queued Molfile Open publishes only the staged backend snapshot on Save."""
	source = tmp_path / "ethane.mol"
	source.write_text(_MOLFILE, encoding="utf-8")
	target = main_window._active_session
	try:
		assert main_window.open_file_path(str(source), replace_current=True)
		_wait_for_async_import_terminal(qtbot, main_window, target)
		imported = main_window._active_session
		before_save = imported.backend_snapshot
		publish_path = tmp_path / "published.cdml"
		imported.write_backend_snapshot(str(publish_path))
		assert imported is not target
		assert imported.document.file_path is None
		assert imported.backend_projection_synchronized
		assert before_save.is_dirty
		assert publish_path.read_text(encoding="utf-8") == before_save.cdml
		assert not imported.backend_snapshot.is_dirty
	finally:
		_restore_blank_anchor(main_window, main_window._active_session)


#============================================
def test_worker_sdf_open_preserves_each_component_with_valid_durable_references(
		main_window: bkchem_qt.main_window.MainWindow,
		tmp_path: pathlib.Path, qtbot: object,
		) -> None:
	"""A queued multi-record SDF Open stages all disconnected components together."""
	source = tmp_path / "two-components.sdf"
	source.write_text(_MULTI_COMPONENT_SDF, encoding="utf-8")
	target = main_window._active_session
	try:
		assert main_window.open_file_path(str(source), replace_current=True)
		_wait_for_async_import_terminal(qtbot, main_window, target)
		imported = main_window._active_session
		identifiers, endpoint_ids = _persistent_ids_and_bond_endpoints(
			imported.backend_snapshot.cdml,
		)
		molecule_ids = re.findall(r'<molecule[^>]*\sid="([^"]+)"', imported.backend_snapshot.cdml)
		assert len(imported.document.molecules) == 2
		assert len(molecule_ids) == len(set(molecule_ids)) == 2
		assert len(identifiers) == len(re.findall(r'\sid="([^"]+)"', imported.backend_snapshot.cdml))
		assert endpoint_ids <= identifiers
	finally:
		_restore_blank_anchor(main_window, main_window._active_session)


#============================================
def test_worker_mol_open_projection_staging_failure_keeps_same_tab_authority(
		main_window: bkchem_qt.main_window.MainWindow,
		tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, qtbot: object,
		) -> None:
	"""A queued imported projection failure leaves the old tab aliases and snapshot live."""
	source = tmp_path / "projection-failure.mol"
	source.write_text(_MOLFILE, encoding="utf-8")
	warnings = _intercept_warnings(monkeypatch)
	target = main_window._active_session
	aliases = (main_window.document, main_window.scene, main_window.view)
	before = target.backend_snapshot

	def fail_import_staging(
			_cls: type[bkchem_qt.models.document_session.DocumentSession],
			_cdml_text: str,
			) -> bkchem_qt.models.document_session.PreparedImportedCDML:
		"""Model a Qt projection preparation error after worker canonicalization."""
		raise ValueError("import projection staging failed")

	monkeypatch.setattr(
		bkchem_qt.models.document_session.DocumentSession,
		"prepare_imported_cdml", classmethod(fail_import_staging),
	)
	assert main_window.open_file_path(str(source), replace_current=True)
	_wait_for_async_import_terminal(qtbot, main_window, target)
	assert main_window._active_session is target
	assert (main_window.document, main_window.scene, main_window.view) == aliases
	assert target.backend_snapshot == before
	assert warnings


#============================================
def test_worker_mol_open_late_detach_failure_restores_same_tab_authority(
		main_window: bkchem_qt.main_window.MainWindow,
		tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, qtbot: object,
		) -> None:
	"""A late imported tab-detach failure rolls back aliases and backend ownership."""
	source = tmp_path / "detach-failure.mol"
	source.write_text(_MOLFILE, encoding="utf-8")
	_intercept_warnings(monkeypatch)
	target = main_window._active_session
	before = target.backend_snapshot
	detach_tab_page = main_window._detach_tab_page

	def fail_target_detach(
			session: bkchem_qt.models.document_session.DocumentSession,
			index: int,
			) -> None:
		"""Fail while the old tab still owns its original view and session."""
		if session is target:
			raise RuntimeError("old imported target detach failed")
		detach_tab_page(session, index)

	try:
		monkeypatch.setattr(main_window, "_detach_tab_page", fail_target_detach)
		assert main_window.open_file_path(str(source), replace_current=True)
		_wait_for_async_import_terminal(qtbot, main_window, target)
		assert _failed_native_open_preserves_target(main_window, target)
		assert target.backend_snapshot == before
	finally:
		_recover_target_after_forced_native_open_failure(main_window, target)


#============================================
def test_stale_worker_mol_open_delivery_is_inert_after_token_invalidation(
		main_window: bkchem_qt.main_window.MainWindow,
		tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, qtbot: object,
		) -> None:
	"""A stale queued worker result changes no tab, recent file, or dialog state."""
	source = tmp_path / "stale.mol"
	source.write_text(_MOLFILE, encoding="utf-8")
	warnings = _intercept_warnings(monkeypatch)
	target = main_window._active_session
	before = target.backend_snapshot
	recent_before = bkchem_qt.config.preferences.Preferences.instance().value(
		bkchem_qt.config.preferences.Preferences.KEY_RECENT_FILES,
	)
	assert main_window.open_file_path(str(source), replace_current=True)
	target.invalidate_import_requests()
	_wait_for_async_import_terminal(qtbot, main_window, target)
	assert main_window._active_session is target
	assert target.backend_snapshot == before
	assert bkchem_qt.config.preferences.Preferences.instance().value(
		bkchem_qt.config.preferences.Preferences.KEY_RECENT_FILES,
	) == recent_before
	assert warnings == []


#============================================
def test_closed_worker_mol_open_delivery_is_inert_and_reaches_terminal_cleanup(
		main_window: bkchem_qt.main_window.MainWindow,
		tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, qtbot: object,
		) -> None:
	"""Closing a loading import tab suppresses its late result without touching peers."""
	source = tmp_path / "closed.mol"
	source.write_text(_MOLFILE, encoding="utf-8")
	warnings = _intercept_warnings(monkeypatch)
	stable = main_window._active_session
	before = stable.backend_snapshot
	recent_before = bkchem_qt.config.preferences.Preferences.instance().value(
		bkchem_qt.config.preferences.Preferences.KEY_RECENT_FILES,
	)
	assert main_window.open_file_path(str(source))
	loading = main_window._active_session
	assert loading is not stable
	assert main_window.close_session_at(main_window.sessions.index(loading))
	_wait_for_async_import_terminal(qtbot, main_window, loading)
	assert main_window.sessions == [stable]
	assert main_window._active_session is stable
	assert stable.backend_snapshot == before
	assert bkchem_qt.config.preferences.Preferences.instance().value(
		bkchem_qt.config.preferences.Preferences.KEY_RECENT_FILES,
	) == recent_before
	assert warnings == []


#============================================
def _new_projected_selection_translate_session(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> bkchem_qt.models.document_session.DocumentSession:
	"""Create one disposable Qt projection for a mixed selection contract test."""
	session = _new_native_session(main_window, _REPAIR_CDML)
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	if not session.replace_projection_from_backend_snapshot(session.backend_snapshot):
		raise AssertionError("Durable CDML projection is unavailable")
	return session


#============================================
@pytest.mark.parametrize(
	"atom_targets,presentation_root_keys",
	(
		((("m1", "a1"),), (("arrow", "arrow1"),)),
		((("m1", "a1", "extra"),), (("presentation", "arrow1"),)),
	),
)
def test_selection_translate_request_rejects_malformed_boundary_keys(
		atom_targets: tuple, presentation_root_keys: tuple,
		) -> None:
	"""The Qt boundary rejects malformed durable-key shapes before dispatch."""
	with pytest.raises(ValueError):
		bkchem_qt.models.document_session.build_selection_translate_request(
			0, atom_targets, presentation_root_keys, (1.0, 0.0),
		)


#============================================
@pytest.mark.parametrize(
	"atom_targets,presentation_root_ids,target_keys",
	(
		((), ("arrow1",), frozenset({("presentation", "arrow1")})),
		((("m1", "a1"),), (), frozenset({("molecule", "m1"), ("atom", "a1")})),
	),
)
def test_selection_translate_requires_both_target_categories_before_dispatch(
		main_window: bkchem_qt.main_window.MainWindow, atom_targets: tuple,
		presentation_root_ids: tuple, target_keys: frozenset[tuple[str, str]],
		) -> None:
	"""An incomplete mixed request leaves every local and backend history untouched."""
	session = _new_projected_selection_translate_session(main_window)
	backend_calls = []
	request = bkchem_qt.models.document_session.PersistentOperationRequest(
		"selection.translate", "Move Selected",
		(
			("expected_revision", session.backend_snapshot.revision),
			("atom_targets", atom_targets),
			("presentation_root_ids", presentation_root_ids),
			("delta", (1.0, 0.0)),
		),
		target_keys,
	)
	executor = session._operation_commit_executors["selection-translate"]

	def record_backend_call(
			prepared: bkchem_qt.models.document_session._PreparedPersistentOperation,
			) -> oasa.cdml_document.CDMLSelectionTranslateResult:
		"""Record any unexpected attempt to execute an incomplete request."""
		backend_calls.append(prepared)
		return executor(prepared)

	session._operation_commit_executors["selection-translate"] = record_backend_call
	try:
		before = session.backend_snapshot
		outcome = session.submit_persistent_operation(request)
		with pytest.raises(ValueError):
			bkchem_qt.models.document_session.build_selection_translate_request(
				before.revision, atom_targets,
				tuple(("presentation", identifier) for identifier in presentation_root_ids),
				(1.0, 0.0),
			)

		histories_unchanged = (
			session.backend_snapshot == before and not session.can_undo_backend
			and session.document.undo_stack.count() == 0
		)
		assert (
			(outcome.status, outcome.failure_kind) == ("rejected", "validation")
			and backend_calls == [] and histories_unchanged
		)
	finally:
		_dispose_session(session)


#============================================
def test_selection_translate_acceptance_uses_backend_history_not_qt_undo(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""One accepted mixed move creates backend history and no Qt undo command."""
	session = _new_projected_selection_translate_session(main_window)
	try:
		before = session.backend_snapshot
		outcome = session.submit_selection_translate(
			before.revision, (("m1", "a1"),), (("presentation", "arrow1"),), (72.0, 0.0),
		)
		history_state = (
			outcome.status == "accepted", outcome.commit is not None,
			session.backend_snapshot.revision == before.revision + 1,
			session.can_undo_backend, session.document.undo_stack.count(),
		)

		assert history_state == (True, True, True, True, 0)
	finally:
		_dispose_session(session)


#============================================
def test_selection_translate_acceptance_reprojects_durable_mixed_selection(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Canonical replacement restores the selected atom and presentation root."""
	session = _new_projected_selection_translate_session(main_window)
	try:
		for item in session.scene.items():
			key = bkchem_qt.canvas.document_projection.persistent_selection_key(item)
			if key in {("atom", "a1"), ("presentation", "arrow1")}:
				item.setSelected(True)
		before = session.backend_snapshot
		session.submit_selection_translate(
			before.revision, (("m1", "a1"),), (("presentation", "arrow1"),), (72.0, 0.0),
		)

		assert _selected_persistent_keys(session) == {
			("atom", "a1"), ("presentation", "arrow1"),
		}
	finally:
		_dispose_session(session)


#============================================
def test_selection_translate_rejects_mismatched_target_keys_without_history(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A request whose durable correlation is wrong cannot reach OASA."""
	session = _new_projected_selection_translate_session(main_window)
	try:
		before = session.backend_snapshot
		mismatched = bkchem_qt.models.document_session.PersistentOperationRequest(
			"selection.translate", "Move Selected",
			(
				("expected_revision", before.revision),
				("atom_targets", (("m1", "a1"),)),
				("presentation_root_ids", ("arrow1",)),
				("delta", (72.0, 0.0)),
			),
			frozenset({("atom", "wrong")}),
		)
		outcome = session.submit_persistent_operation(mismatched)

		assert (
			(outcome.status, outcome.failure_kind, session.backend_snapshot) ==
			("rejected", "validation", before) and not session.can_undo_backend
		)
	finally:
		_dispose_session(session)


#============================================
def test_selection_translate_zero_delta_is_an_accepted_noop(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A canonical zero movement preserves the current snapshot without history."""
	session = _new_projected_selection_translate_session(main_window)
	try:
		before = session.backend_snapshot
		outcome = session.submit_selection_translate(
			before.revision, (("m1", "a1"),), (("presentation", "arrow1"),), (0.0, 0.0),
		)

		assert (
			outcome.status == "accepted" and outcome.commit is None
			and session.backend_snapshot == before and not session.can_undo_backend
		)
	finally:
		_dispose_session(session)


#============================================
def test_selection_translate_stale_revision_cannot_add_backend_history(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A stale captured revision preserves the one already accepted snapshot."""
	session = _new_projected_selection_translate_session(main_window)
	try:
		original = session.backend_snapshot
		session.submit_selection_translate(
			original.revision, (("m1", "a1"),), (("presentation", "arrow1"),), (72.0, 0.0),
		)
		accepted = session.backend_snapshot
		stale = session.submit_selection_translate(
			original.revision, (("m1", "a1"),), (("presentation", "arrow1"),), (72.0, 0.0),
		)
		stale_preserved_snapshot = session.backend_snapshot == accepted
		undo = session.undo_backend()
		history_state = (
			stale.status, stale.failure_kind, stale_preserved_snapshot, undo.status,
			session.backend_snapshot.cdml == original.cdml, session.can_undo_backend,
		)

		assert history_state == ("rejected", "revision-conflict", True, "accepted", True, False)
	finally:
		_dispose_session(session)


#============================================
def test_selection_translate_projection_retry_reuses_only_the_accepted_snapshot(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Projection recovery never sends the accepted mixed request twice."""
	session = _new_native_session(main_window, _REPAIR_CDML)
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	if not session.replace_projection_from_backend_snapshot(session.backend_snapshot):
		raise AssertionError("Durable CDML projection is unavailable")
	calls = []
	projection_revisions = []
	executor = session._operation_commit_executors["selection-translate"]

	def count_translate(
			prepared: bkchem_qt.models.document_session._PreparedPersistentOperation,
			) -> oasa.cdml_document.CDMLSelectionTranslateResult:
		"""Record the one backend call made for the accepted mixed operation."""
		calls.append(prepared)
		return executor(prepared)

	def fail_once(snapshot: oasa.cdml_document.CDMLSnapshot) -> object:
		"""Make the first accepted replacement unavailable, then install its retry."""
		projection_revisions.append(snapshot.revision)
		if len(projection_revisions) == 1:
			return _projection_unavailable(snapshot)
		return session.replace_projection_from_backend_snapshot(snapshot)

	session._operation_commit_executors["selection-translate"] = count_translate
	_install_projection_port(session, fail_once)
	try:
		outcome = session.submit_selection_translate(
			session.backend_snapshot.revision, (("m1", "a1"),),
			(("presentation", "arrow1"),), (72.0, 0.0),
		)
		retried = session.retry_current_backend_projection()

		assert outcome.status == "unavailable" and retried.status == "accepted"
		assert len(calls) == 1 and projection_revisions == [
			session.backend_snapshot.revision, session.backend_snapshot.revision,
		]
	finally:
		_dispose_session(session)


#============================================
def _dispose_session(
		session: bkchem_qt.models.document_session.DocumentSession,
		) -> None:
	"""Release a standalone session through its owning window's safe reaper."""
	owner = session.parent()
	if not isinstance(owner, bkchem_qt.main_window.MainWindow):
		raise TypeError("Standalone test session has no MainWindow lifetime owner")
	owner._dispose_session_later(session)


#============================================
def _drain_deferred_deletes(
		app: PySide6.QtWidgets.QApplication,
		main_window: bkchem_qt.main_window.MainWindow = None,
		) -> None:
	"""Deliver queued QObject destruction before inspecting native wrappers."""
	assert bkchem_qt.main_window.drain_pending_session_deletions(app, main_window)


#============================================
def _restore_blank_anchor(
		main_window: bkchem_qt.main_window.MainWindow,
		opened_session: bkchem_qt.models.document_session.DocumentSession,
		) -> None:
	"""Leave the module fixture with a fresh synchronized blank session."""
	main_window._on_new()
	main_window._remove_session(opened_session)


#============================================
def _intercept_warnings(monkeypatch: pytest.MonkeyPatch) -> list[str]:
	"""Replace modal file-read warnings with a deterministic message sink."""
	messages = []

	def record_warning(_parent: object, _title: str, message: str) -> None:
		"""Record one production warning without entering a modal event loop."""
		messages.append(message)

	monkeypatch.setattr(
		PySide6.QtWidgets.QMessageBox, "warning", record_warning,
	)
	return messages


#============================================
def _presentation_by_id(
		document: bkchem_qt.models.document.Document, object_id: str,
		) -> bkchem_qt.models.document_object.PresentationObject:
	"""Return one projected object by its durable CDML identifier."""
	for presentation in document.presentation_objects:
		if presentation.object_id == object_id:
			return presentation
	raise ValueError("No projected object has CDML id %s" % object_id)


#============================================
def _failed_native_open_preserves_target(
		main_window: bkchem_qt.main_window.MainWindow,
		target: bkchem_qt.models.document_session.DocumentSession,
		) -> bool:
	"""Return whether a failed native Open left its target fully usable."""
	target.set_display_name("Recovered native Open target")
	target_index = main_window._tab_widget.indexOf(target.view)
	try:
		selected = main_window._select_session(target)
	except (AttributeError, RuntimeError):
		selected = False
	return (
		selected
		and main_window._active_session is target
		and main_window.document is target.document
		and main_window.scene is target.scene
		and main_window.view is target.view
		and main_window._property_dock._document is target.document
		and main_window._tab_widget.currentWidget() is target.view
		and main_window._tab_widget.tabText(target_index) == target.title
		and main_window._sessions_by_view.get(target.view) is target
		and all(session is target for session in main_window.sessions)
	)


#============================================
def _recover_target_after_forced_native_open_failure(
		main_window: bkchem_qt.main_window.MainWindow,
		target: bkchem_qt.models.document_session.DocumentSession,
		) -> None:
	"""Restore the shared window after exercising a known-broken rollback."""
	for session in tuple(main_window.sessions):
		if session is not target:
			main_window._remove_session(session)
	target_index = main_window._tab_widget.indexOf(target.view)
	if main_window._tab_widget.tabText(target_index) != target.title:
		target.title_changed.connect(main_window._on_session_title_changed)
	if main_window._active_session is target:
		return
	main_window._tab_widget.setCurrentIndex(
		main_window._tab_widget.indexOf(target.view),
	)
	main_window._set_active_session_aliases(target)
	main_window._bind_property_dock(target)
	if main_window._ui_signals_connected:
		main_window._connect_active_session_signals(target)
		current_mode = target.mode_manager.current_mode
		if current_mode is not None:
			current_mode.activate()


#============================================
def test_fresh_tabs_keep_backend_arrow_commits_isolated(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""One tab's complete-CDML commit cannot change another tab's backend state."""
	first = _new_tab(main_window)
	second = _new_tab(main_window)
	try:
		first.commit_complete_candidate(_arrow_candidate())
		assert "arrow" in first.backend_snapshot.cdml
		assert "arrow" not in second.backend_snapshot.cdml
	finally:
		_close_tab(main_window, second)
		_close_tab(main_window, first)


#============================================
def test_fresh_tab_backend_has_canonical_blank_version(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A fresh backend declares the shared CDML version."""
	session = _new_tab(main_window)
	try:
		assert 'version="%s"' % oasa.cdml_writer.DEFAULT_CDML_VERSION in session.backend_snapshot.cdml
	finally:
		_close_tab(main_window, session)


#============================================
def test_fresh_tab_backend_has_canonical_blank_namespace(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A fresh backend declares the canonical CDML namespace."""
	session = _new_tab(main_window)
	try:
		assert 'xmlns="%s"' % oasa.cdml_writer.CDML_NAMESPACE in session.backend_snapshot.cdml
	finally:
		_close_tab(main_window, session)


#============================================
def test_backend_commit_allocates_provisional_arrow_id(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A complete candidate receives its backend-owned persistent arrow ID."""
	session = _new_tab(main_window)
	try:
		commit = session.commit_complete_candidate(_arrow_candidate())
		assert commit.id_map[_PROVISIONAL_ARROW] in commit.cdml
	finally:
		_close_tab(main_window, session)


#============================================
def test_backend_commit_does_not_mutate_qt_projection(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A backend-only commit leaves the live Qt projection untouched."""
	session = _new_tab(main_window)
	document = session.document
	try:
		session.commit_complete_candidate(_arrow_candidate())
		assert session.document is document
		assert not document.dirty
	finally:
		_close_tab(main_window, session)


#============================================
def test_stale_projection_refuses_backend_snapshot_write(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		) -> None:
	"""A backend commit cannot save while its Qt projection is stale."""
	session = _new_tab(main_window)
	target = tmp_path / "stale.cdml"
	try:
		session.commit_complete_candidate(_arrow_candidate())
		with pytest.raises(bkchem_qt.models.document_session.BackendProjectionOutOfSyncError):
			session.write_backend_snapshot(str(target))
		assert not target.exists()
	finally:
		_close_tab(main_window, session)


#============================================
def test_rejected_candidate_keeps_backend_revision(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Backend validation failure cannot advance the authoritative revision."""
	session = _new_tab(main_window)
	original_revision = session.backend_snapshot.revision
	try:
		with pytest.raises(oasa.cdml_document.CDMLValidationError):
			session.commit_complete_candidate(
				'<cdml version="0.15"><arrow id="same"/><text id="same"/></cdml>',
			)
		assert session.backend_snapshot.revision == original_revision
	finally:
		_close_tab(main_window, session)


#============================================
def test_rejected_candidate_keeps_projection_synchronized(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Backend validation failure leaves the existing projection saveable."""
	session = _new_tab(main_window)
	try:
		with pytest.raises(oasa.cdml_document.CDMLValidationError):
			session.commit_complete_candidate(
				'<cdml version="0.15"><arrow id="same"/><text id="same"/></cdml>',
			)
		assert session.backend_projection_synchronized
	finally:
		_close_tab(main_window, session)


#============================================
def test_legacy_qt_dirty_transition_blocks_backend_write_until_canonical_reprojection(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		) -> None:
	"""Legacy direct edits block saving until canonical CDML reprojection."""
	session = _new_tab(main_window)
	target = tmp_path / "legacy-stale.cdml"
	try:
		session.document.mark_dirty()
		session.document.mark_clean()
		with pytest.raises(bkchem_qt.models.document_session.BackendProjectionOutOfSyncError):
			session.write_backend_snapshot(str(target))
		assert not target.exists()
	finally:
		_close_tab(main_window, session)


#============================================
def test_native_staging_installs_matching_projection(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Native staging installs a Qt projection from canonical backend CDML."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(
		_OPEN_ARROW_CDML,
	)
	session = _new_synchronized_session(main_window, prepared)
	try:
		arrow = _presentation_by_id(session.document, "arrow-1")
		assert session.backend_snapshot.cdml == prepared.canonical_cdml
		assert arrow.kind == "arrow"
	finally:
		_dispose_session(session)


#============================================
def test_prepared_native_cdml_transfer_is_one_use_and_private(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A retained staging value cannot install a second mutable authority."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(
		_ARROW_CDML,
	)
	first = _new_synchronized_session(main_window, prepared)
	try:
		with pytest.raises(RuntimeError, match="already been consumed"):
			_new_synchronized_session(main_window, prepared)
		assert first.backend_snapshot == prepared.snapshot
	finally:
		_dispose_session(first)


#============================================
def test_prepared_native_cdml_remains_retryable_after_setup_failure(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A failed receiving setup leaves the prepared transfer available to retry."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(
		_ARROW_CDML,
	)
	real_setup_modes = bkchem_qt.setup.mode_setup.setup_modes
	failed_once = False

	def fail_once_after_canvas(
			view: object, mode_host: object, parent: object | None = None,
			persistent_action: object | None = None,
			atom_align_action: object | None = None,
			atom_translate_action: object | None = None,
			atom_rotate_action: object | None = None,
			atom_translate_authority: object | None = None,
			presentation_translate_action: object | None = None,
			presentation_translate_context: object | None = None,
			selection_translate_action: object | None = None,
			selection_translate_context: object | None = None,
			top_level_delete_context: object | None = None,
			structure_delete_context: object | None = None,
			atom_mark_delete_context: object | None = None,
			atom_number_context: object | None = None,
			atom_mark_revision: object | None = None,
			template_names: tuple[str, ...] | None = None,
			template_action: object | None = None,
			biomolecule_catalog: tuple[object, ...] | None = None,
			biotemplate_action: object | None = None,
			user_template_catalog: tuple[object, ...] | None = None,
			user_template_action: object | None = None,
			graphics_retirement_reaper: object | None = None,
			) -> object:
		"""Fail only the first receiver setup after the canvas has been created."""
		nonlocal failed_once
		if not failed_once:
			failed_once = True
			raise RuntimeError("mode setup failed")
		return real_setup_modes(
			view, mode_host, parent=parent,
			persistent_action=persistent_action,
			atom_align_action=atom_align_action,
			atom_translate_action=atom_translate_action,
			atom_rotate_action=atom_rotate_action,
			atom_translate_authority=atom_translate_authority,
			presentation_translate_action=presentation_translate_action,
			presentation_translate_context=presentation_translate_context,
			selection_translate_action=selection_translate_action,
			selection_translate_context=selection_translate_context,
			top_level_delete_context=top_level_delete_context,
			structure_delete_context=structure_delete_context,
			atom_mark_delete_context=atom_mark_delete_context,
			atom_number_context=atom_number_context,
			atom_mark_revision=atom_mark_revision,
			template_names=template_names,
			template_action=template_action,
			biomolecule_catalog=biomolecule_catalog,
			biotemplate_action=biotemplate_action,
			user_template_catalog=user_template_catalog,
			user_template_action=user_template_action,
			graphics_retirement_reaper=graphics_retirement_reaper,
		)

	monkeypatch.setattr(bkchem_qt.setup.mode_setup, "setup_modes", fail_once_after_canvas)
	with pytest.raises(RuntimeError, match="mode setup failed"):
		_new_synchronized_session(main_window, prepared)
	session = _new_synchronized_session(main_window, prepared)
	try:
		assert (prepared.consumed, session.backend_snapshot) == (True, prepared.snapshot)
	finally:
		_dispose_session(session)


#============================================
def test_native_staging_decoder_failure_does_not_change_live_session(
		main_window: bkchem_qt.main_window.MainWindow, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Projection decoding failure remains detached from an already-live tab."""
	session = _new_tab(main_window)
	original_document = session.document
	original_snapshot = session.backend_snapshot

	def fail_decode(
			_projection_snapshot: object,
			) -> bkchem_qt.models.document.Document:
		"""Model a projection decode failure after backend staging succeeds."""
		raise ValueError("projection failed")

	try:
		monkeypatch.setattr(
			bkchem_qt.io.cdml_document_io, "hydrate_synchronized_cdml_document", fail_decode,
		)
		with pytest.raises(ValueError, match="projection failed"):
			bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(
				_ARROW_CDML,
			)
		assert (session.document, session.backend_snapshot) == (
			original_document, original_snapshot,
		)
	finally:
		_close_tab(main_window, session)


#============================================
def test_core_projection_never_binds_a_bond_to_a_duplicate_atom_id() -> None:
	"""Compatibility geometry shows duplicate atoms without inventing a bond target."""
	cdml = (
		"<cdml><molecule id='m'><atom id='a' name='C'><point x='0cm' y='0cm'/></atom>"
		"<atom id='a' name='N'><point x='1cm' y='0cm'/></atom>"
		"<atom id='c' name='O'><point x='2cm' y='0cm'/></atom>"
		"<bond id='e' start='a' end='c' type='n1'/></molecule></cdml>"
	)
	backend_document = oasa.cdml_document.CDMLDocument.parse(cdml, validation="compat")
	projection_snapshot = oasa.cdml_document.CDMLDocument.projection_snapshot(
		oasa.cdml_document.CDMLSnapshot(0, backend_document.serialize(), False),
	)
	document = bkchem_qt.io.cdml_document_io.hydrate_synchronized_cdml_document(
		projection_snapshot,
	)
	assert not document.molecules[0].bonds


#============================================
def test_synchronized_clean_session_writes_exact_backend_snapshot(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		) -> None:
	"""A clean native session writes the exact immutable backend snapshot."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(
		_ARROW_CDML,
	)
	session = _new_synchronized_session(main_window, prepared)
	target = tmp_path / "backend.cdml"
	try:
		saved = session.write_backend_snapshot(str(target))
		assert target.read_text(encoding="utf-8") == saved.cdml
		assert not saved.is_dirty
	finally:
		_dispose_session(session)


#============================================
def test_backend_write_failure_keeps_clean_snapshot_stable(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A failed backend write cannot change its clean authoritative snapshot."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(
		_ARROW_CDML,
	)
	session = _new_synchronized_session(main_window, prepared)
	target = tmp_path / "failed-backend.cdml"
	before = session.backend_snapshot

	def fail_write(
			_path: str, _snapshot: oasa.cdml_document.CDMLSnapshot,
			) -> None:
		"""Model a filesystem failure before any bytes are written."""
		raise OSError("disk unavailable")

	try:
		monkeypatch.setattr(
			bkchem_qt.models.document_session, "_write_backend_snapshot", fail_write,
		)
		with pytest.raises(OSError, match="disk unavailable"):
			session.write_backend_snapshot(str(target))
		assert (session.backend_snapshot, target.exists()) == (before, False)
	finally:
		_dispose_session(session)


#============================================
def test_authoritative_snapshot_capability_is_total_for_unavailable_states(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Unavailable, replacing, detached, and disposed sessions are ineligible."""
	session = _new_native_session(main_window)
	try:
		session._projection_replacing = True
		replacing = session.can_write_authoritative_snapshot
		session._projection_replacing = False
		session.view.set_document(None)
		detached = session.can_write_authoritative_snapshot
		session.view.set_document(session.document)
		session.dispose()
		assert (replacing, detached, session.can_write_authoritative_snapshot) == (
			False, False, False,
		)
	finally:
		session.deleteLater()


#============================================
def test_authoritative_snapshot_bootstrap_tracks_backend_provenance(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Blank and native sessions qualify, while legacy-populated Qt state does not."""
	blank = _new_native_session(main_window, '<cdml version="0.15"></cdml>')
	native = _new_native_session(main_window)
	legacy = _new_native_session(main_window)
	try:
		legacy.document.mark_dirty()
		assert (
			blank.can_write_authoritative_snapshot,
			native.can_write_authoritative_snapshot,
			legacy.can_write_authoritative_snapshot,
		) == (True, True, False)
	finally:
		_dispose_session(legacy)
		_dispose_session(native)
		_dispose_session(blank)


#============================================
def test_authoritative_save_routes_canonical_bytes_without_qt_serializer(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		) -> None:
	"""An eligible Save publishes OASA CDML and establishes both clean points."""
	session = _new_native_session(main_window)
	target = tmp_path / "authoritative.cdml"
	captured = session.backend_snapshot

	try:
		result = main_window._save_session_to_path(session, str(target))
		assert (
			result,
			target.read_text(encoding="utf-8"),
			session.backend_snapshot.is_dirty,
			session.document.dirty,
		) == (True, captured.cdml, False, False)
	finally:
		_dispose_session(session)


#============================================
def test_save_ineligible_session_requires_recovery_export_without_qt_serialization(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""An isolated projection cannot Save, while Recovery Export preserves its snapshot."""
	session = _new_native_session(main_window)
	target = tmp_path / "legacy-save.cdml"
	recovery_target = tmp_path / "recovery.cdml"
	before = session.backend_snapshot
	warnings = []

	def record_warning(*args: object, **_kwargs: object) -> None:
		"""Capture the user-facing unavailable-Save explanation without a dialog."""
		warnings.append(args)

	try:
		session.document.mark_dirty()
		monkeypatch.setattr(PySide6.QtWidgets.QMessageBox, "warning", record_warning)
		result = main_window._save_session_to_path(session, str(target))
		assert (
			result,
			warnings[0][1],
			session.backend_snapshot,
			session.can_write_authoritative_snapshot,
			target.exists(),
		) == (False, "Authoritative Save Unavailable", before, False, False)
		assert session.export_backend_snapshot(str(recovery_target)) == before
		assert recovery_target.read_text(encoding="utf-8") == before.cdml
	finally:
		_dispose_session(session)


#============================================
def test_file_action_predicates_disable_save_but_keep_recovery_export_available(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A local edit exposes recovery without enabling unavailable file actions."""
	session = main_window._active_session
	assert main_window._registry.is_enabled("file.save", main_window)
	try:
		session.document.mark_dirty()
		assert (
			main_window._registry.is_enabled("file.save", main_window),
			main_window._registry.is_enabled("file.save_as", main_window),
			main_window._registry.is_enabled("file.recovery_export", main_window),
			main_window._registry.is_enabled("file.save_as_template", main_window),
		) == (False, False, True, False)
	finally:
		session._discard_legacy_and_retry_projection()


#============================================
def test_template_export_publishes_backend_canonical_content_without_session_mutation(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		) -> None:
	"""Template export uses the validated backend snapshot, never Qt serialization."""
	session = _new_native_session(main_window)
	target = tmp_path / "canonical-template.cdml"
	before = session.backend_snapshot
	try:
		session.document.mark_dirty()
		assert main_window._save_template_session_to_path(session, str(target))
		assert (
			target.read_text(encoding="utf-8"), session.backend_snapshot,
			session.document.dirty,
		) == (before.cdml, before, True)
	finally:
		_dispose_session(session)


#============================================
def test_template_export_reports_unavailable_without_a_recovery_session(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Template export rejects an absent active backend snapshot before opening a dialog."""
	warnings = []

	def record_warning(*args: object, **_kwargs: object) -> None:
		"""Capture the unavailable-template result without a modal dialog."""
		warnings.append(args)

	monkeypatch.setattr(main_window, "_active_recovery_export_session", lambda: None)
	monkeypatch.setattr(PySide6.QtWidgets.QMessageBox, "warning", record_warning)
	assert not main_window._on_save_as_template()
	assert warnings[0][1] == "Template Export Unavailable"


#============================================
def test_authoritative_pre_replace_failure_preserves_old_file_and_memory_state(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A failed ordinary Save reports failure without publishing or cleaning state."""
	session = _new_native_session(main_window)
	target = tmp_path / "old-target.cdml"
	target.write_text("old-target", encoding="utf-8")
	before = (session.backend_snapshot, session.document.dirty)
	warnings = []

	def fail_before_replace(
			_path: str, _snapshot: oasa.cdml_document.CDMLSnapshot,
			) -> None:
		"""Model a failed staged write before publication can occur."""
		raise OSError("staged write failed")

	def record_warning(*args: object, **_kwargs: object) -> None:
		"""Capture the Save failure message without running a modal dialog."""
		warnings.append(args)

	try:
		monkeypatch.setattr(
			bkchem_qt.models.document_session, "_write_backend_snapshot", fail_before_replace,
		)
		monkeypatch.setattr(PySide6.QtWidgets.QMessageBox, "warning", record_warning)
		assert not main_window._save_session_to_path(session, str(target))
		assert (
			target.read_text(encoding="utf-8"), session.backend_snapshot,
			session.document.dirty, warnings[0][1],
		) == (
			"old-target", before[0], before[1], "Save Error",
		)
	finally:
		_dispose_session(session)


#============================================
def test_authoritative_writer_follows_symlink_and_preserves_referent_mode(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		) -> None:
	"""An existing native symlink retains its identity and referent permissions."""
	session = _new_native_session(main_window)
	referent = tmp_path / "referent.cdml"
	link = tmp_path / "linked.cdml"
	referent.write_text("old-target", encoding="utf-8")
	referent.chmod(0o640)
	link.symlink_to(referent)
	captured = session.backend_snapshot
	try:
		session.write_backend_snapshot(str(link))
		assert (
			link.is_symlink(),
			referent.read_text(encoding="utf-8"),
			stat.S_IMODE(referent.stat().st_mode),
		) == (True, captured.cdml, 0o640)
	finally:
		_dispose_session(session)


#============================================
def test_directory_fsync_failure_reports_partial_publication_and_cleans_stage(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A directory-sync error reports partial publication without a baseline update."""
	session = _new_native_session(main_window)
	target = tmp_path / "durability.cdml"
	captured = session.backend_snapshot
	directory_descriptors = set()
	mark_saved_calls = []
	original_open = bkchem_qt.models.document_session.os.open
	original_fsync = bkchem_qt.models.document_session.os.fsync

	def capture_directory_open(path: str, flags: int, mode: int = 0o777) -> int:
		"""Remember the descriptor used to durability-sync this test directory."""
		descriptor = original_open(path, flags, mode)
		if path == str(tmp_path) and not flags & os.O_CREAT:
			directory_descriptors.add(descriptor)
		return descriptor

	def fail_directory_fsync(descriptor: int) -> None:
		"""Fail only the post-replacement directory durability confirmation."""
		if descriptor in directory_descriptors:
			raise OSError(errno.EIO, "directory sync failed")
		original_fsync(descriptor)

	def record_mark_saved(*, expected_revision: int) -> object:
		"""Record an impermissible baseline update after durability failure."""
		mark_saved_calls.append(expected_revision)
		raise AssertionError("directory fsync failure called mark_saved")

	try:
		monkeypatch.setattr(
			bkchem_qt.models.document_session.os, "open", capture_directory_open,
		)
		monkeypatch.setattr(
			bkchem_qt.models.document_session.os, "fsync", fail_directory_fsync,
		)
		monkeypatch.setattr(session._backend_session, "mark_saved", record_mark_saved)
		with pytest.raises(
			bkchem_qt.models.document_session.BackendSnapshotPublicationError,
			match="publication durability is unconfirmed",
		):
			session.write_backend_snapshot(str(target))
		assert (
			target.read_text(encoding="utf-8"),
			mark_saved_calls,
			session.backend_snapshot,
			session.document.dirty,
			any(tmp_path.glob(".durability.cdml.bkchem-*.tmp")),
		) == (captured.cdml, [], captured, False, False)
	finally:
		_dispose_session(session)


#============================================
def test_recovery_export_writes_exact_snapshot_without_qt_or_baseline_mutation(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Recovery Export publishes backend bytes without reading the Qt projection."""
	session = _new_native_session(main_window)
	target = tmp_path / "recovery.cdml"
	captured = session.backend_snapshot
	original_document = session.document
	mark_saved_calls = []

	class ForbiddenDocument:
		"""Reject any unexpected Recovery Export access to Qt document state."""

		def __getattribute__(self, _name: str) -> object:
			raise AssertionError("Recovery Export inspected the Qt document")

	def record_mark_saved(*, expected_revision: int) -> object:
		"""Reject baseline mutation from the state-neutral export route."""
		mark_saved_calls.append(expected_revision)
		raise AssertionError("Recovery Export marked the backend saved")

	try:
		session._legacy_isolated = True
		session._backend_projection_synchronized = False
		monkeypatch.setattr(session, "_document", ForbiddenDocument())
		monkeypatch.setattr(session._backend_session, "mark_saved", record_mark_saved)
		result = session.export_backend_snapshot(str(target))
		assert (result, target.read_text(encoding="utf-8")) == (captured, captured.cdml)
		assert (session.backend_snapshot, mark_saved_calls, session.legacy_isolated) == (
			captured, [], True,
		)
	finally:
		session._document = original_document
		_dispose_session(session)


#============================================
def test_recovery_export_is_projection_independent_and_rejects_disposal(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		) -> None:
	"""A missing projection remains exportable until terminal disposal begins."""
	session = _new_native_session(main_window)
	target = tmp_path / "unavailable.cdml"
	captured = session.backend_snapshot
	original_document = session.document
	try:
		try:
			session._document = None
			session._backend_projection_synchronized = False
			assert (session.can_recovery_export, session.export_backend_snapshot(str(target))) == (
				True, captured,
			)
		finally:
			# Restore the owned projection before terminal Qt teardown.
			session._document = original_document
			session._backend_projection_synchronized = True
		session.dispose()
		with pytest.raises(RuntimeError, match="live backend session"):
			session.export_backend_snapshot(str(tmp_path / "disposed.cdml"))
	finally:
		_dispose_session(session)


#============================================
def test_optional_recent_file_failure_cannot_revoke_successful_authoritative_save(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Presentation bookkeeping failure cannot turn completed persistence into false."""
	session = _new_native_session(main_window)
	target = tmp_path / "successful-with-bad-recent.cdml"

	def fail_recent(_window: object, _path: str) -> None:
		"""Model optional recent-file persistence failing after a real Save."""
		raise OSError("recent settings unavailable")

	try:
		monkeypatch.setattr(bkchem_qt.actions.file_actions, "_record_recent_file", fail_recent)
		assert main_window._save_session_to_path(session, str(target))
	finally:
		_dispose_session(session)


#============================================
def test_disposed_session_rejects_backend_mutation(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A disposed tab cannot accept a stale backend commit callback."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(
		_ARROW_CDML,
	)
	session = _new_synchronized_session(main_window, prepared)
	session.dispose()
	try:
		with pytest.raises(RuntimeError):
			session.commit_complete_candidate(_arrow_candidate())
	finally:
		session.deleteLater()


#============================================
def test_disposed_session_rejects_backend_write(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		) -> None:
	"""A disposed tab cannot write a stale backend save request."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(
		_ARROW_CDML,
	)
	session = _new_synchronized_session(main_window, prepared)
	target = tmp_path / "disposed.cdml"
	session.dispose()
	try:
		with pytest.raises(RuntimeError):
			session.write_backend_snapshot(str(target))
		assert not target.exists()
	finally:
		session.deleteLater()


#============================================
def test_native_open_installs_canonical_backend_snapshot_projection(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		) -> None:
	"""Native Open projects the canonical backend snapshot without local reserialization."""
	source = tmp_path / "backend-first.cdml"
	source.write_text(_OPEN_ARROW_CDML, encoding="utf-8")
	startup = main_window._active_session
	expected = oasa.cdml_document.CDMLDocumentSession.load(
		_OPEN_ARROW_CDML,
	).projection_snapshot().snapshot
	try:
		opened = main_window.open_file_path(str(source))
		session = main_window._active_session
		assert opened and (
			session.backend_projection_synchronized
			and session.backend_snapshot == expected
			and _presentation_by_id(session.document, "arrow-1").kind == "arrow"
		)
		assert startup not in main_window.sessions
	finally:
		_restore_blank_anchor(main_window, main_window._active_session)


#============================================
def test_native_open_projects_backend_canonical_arrow(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		) -> None:
	"""The staged backend snapshot creates the durable arrow projection."""
	source = tmp_path / "projected-arrow.cdml"
	source.write_text(_OPEN_ARROW_CDML, encoding="utf-8")
	try:
		assert main_window.open_file_path(str(source))
		assert _presentation_by_id(
			main_window.document, "arrow-1",
		).kind == "arrow"
	finally:
		_restore_blank_anchor(main_window, main_window._active_session)


#============================================
def test_native_open_backend_staging_failure_keeps_active_aliases(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""An invalid backend candidate cannot disturb the current tab projection."""
	source = tmp_path / "invalid-root.cdml"
	source.write_text("<not-cdml/>", encoding="utf-8")
	messages = _intercept_warnings(monkeypatch)
	target = main_window._active_session
	aliases = (main_window.document, main_window.scene, main_window.view)
	opened = main_window.open_file_path(str(source))
	assert (opened, main_window._active_session, (
		main_window.document, main_window.scene, main_window.view,
	)) == (False, target, aliases)
	assert messages


#============================================
def test_native_open_projection_staging_failure_keeps_active_aliases(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A failed Qt projection decode cannot disturb the current backend tab."""
	source = tmp_path / "projection-failure.cdml"
	source.write_text(_OPEN_ARROW_CDML, encoding="utf-8")
	messages = _intercept_warnings(monkeypatch)
	target = main_window._active_session
	aliases = (main_window.document, main_window.scene, main_window.view)

	def fail_projection(
			_cdml_text: str, observations: object,
		) -> bkchem_qt.models.document.Document:
		"""Model a decoder failure after backend canonicalization succeeds."""
		del observations
		raise ValueError("projection staging failed")

	monkeypatch.setattr(
		bkchem_qt.io.cdml_document_io, "hydrate_synchronized_cdml_document", fail_projection,
	)
	opened = main_window.open_file_path(str(source))
	assert (opened, main_window._active_session, (
		main_window.document, main_window.scene, main_window.view,
	)) == (False, target, aliases)
	assert messages


#============================================
def test_same_tab_native_open_setup_failure_keeps_target_and_prepared_retryable(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A receiver-construction failure preserves both target and staging value."""
	source = tmp_path / "same-tab-failure.cdml"
	source.write_text(_OPEN_ARROW_CDML, encoding="utf-8")
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(
		_OPEN_ARROW_CDML,
	)
	_intercept_warnings(monkeypatch)
	target = main_window._active_session
	target_document = main_window.document

	def return_prepared(
			_cls: type[bkchem_qt.models.document_session.DocumentSession],
			_cdml_text: str,
			) -> bkchem_qt.models.document_session.PreparedNativeCDML:
		"""Return the retained value so construction is the failing stage."""
		return prepared

	def fail_setup_modes(
			_view: object, _mode_host: object, parent: object | None = None,
			persistent_action: object | None = None,
			atom_align_action: object | None = None,
			atom_translate_action: object | None = None,
			atom_rotate_action: object | None = None,
			atom_translate_authority: object | None = None,
			presentation_translate_action: object | None = None,
			presentation_translate_context: object | None = None,
			selection_translate_action: object | None = None,
			selection_translate_context: object | None = None,
			top_level_delete_context: object | None = None,
			structure_delete_context: object | None = None,
			atom_mark_delete_context: object | None = None,
			atom_number_context: object | None = None,
			atom_mark_revision: object | None = None,
			template_names: tuple[str, ...] | None = None,
			template_action: object | None = None,
			biomolecule_catalog: tuple[object, ...] | None = None,
			biotemplate_action: object | None = None,
			user_template_catalog: tuple[object, ...] | None = None,
			user_template_action: object | None = None,
			graphics_retirement_reaper: object | None = None,
			) -> object:
		"""Fail after native staging but before a session becomes viable."""
		del (
			parent, persistent_action, atom_align_action, atom_translate_action, atom_rotate_action,
			atom_translate_authority, presentation_translate_action,
			presentation_translate_context, selection_translate_action,
			selection_translate_context, top_level_delete_context, structure_delete_context,
			atom_mark_delete_context, atom_number_context, atom_mark_revision, template_names,
			template_action, biomolecule_catalog, biotemplate_action, user_template_catalog,
			user_template_action,
			graphics_retirement_reaper,
		)
		raise RuntimeError("mode setup failed")

	monkeypatch.setattr(
		bkchem_qt.models.document_session.DocumentSession,
		"prepare_native_cdml",
		classmethod(return_prepared),
	)
	try:
		with monkeypatch.context() as setup_patch:
			setup_patch.setattr(
				bkchem_qt.setup.mode_setup, "setup_modes", fail_setup_modes,
			)
			opened = main_window.open_file_path(str(source), replace_current=True)
		assert (opened, main_window._active_session, main_window.document) == (
			False, target, target_document,
		)
		retried = main_window.open_file_path(str(source), replace_current=True)
		assert retried and prepared.consumed and main_window._active_session is not target
	finally:
		if target in main_window.sessions:
			_recover_target_after_forced_native_open_failure(main_window, target)
		else:
			_restore_blank_anchor(main_window, main_window._active_session)


#============================================
def test_native_open_activation_failure_restores_existing_tab(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""An activation exception cannot replace the live tab with a failed Open."""
	source = tmp_path / "activation-failure.cdml"
	source.write_text(_OPEN_ARROW_CDML, encoding="utf-8")
	_intercept_warnings(monkeypatch)
	target = main_window._active_session
	activate_session = main_window._activate_session
	was_tab_change_blocked = main_window._tab_change_blocked

	def activate_then_fail(
			session: bkchem_qt.models.document_session.DocumentSession,
			) -> None:
		"""Change active state first, then model a late UI activation failure."""
		activate_session(session)
		raise RuntimeError("activation synchronization failed")

	try:
		with monkeypatch.context() as activation_patch:
			activation_patch.setattr(
				main_window, "_activate_session", activate_then_fail,
			)
			main_window._tab_change_blocked = True
			opened = main_window.open_file_path(str(source))
			main_window._tab_change_blocked = was_tab_change_blocked
		assert (opened, _failed_native_open_preserves_target(
			main_window, target,
		)) == (False, True)
	finally:
		main_window._tab_change_blocked = was_tab_change_blocked
		_recover_target_after_forced_native_open_failure(main_window, target)


#============================================
def test_same_tab_native_open_detach_failure_restores_existing_tab(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A replacement detach exception cannot leave a staged tab registered."""
	source = tmp_path / "detach-failure.cdml"
	source.write_text(_OPEN_ARROW_CDML, encoding="utf-8")
	_intercept_warnings(monkeypatch)
	target = main_window._active_session
	detach_tab_page = main_window._detach_tab_page

	def fail_target_detach(
			session: bkchem_qt.models.document_session.DocumentSession,
			index: int,
			) -> None:
		"""Fail only while the old target remains recoverable in its tab."""
		if session is target:
			raise RuntimeError("old-tab detach failed")
		detach_tab_page(session, index)

	try:
		with monkeypatch.context() as detach_patch:
			detach_patch.setattr(
				main_window, "_detach_tab_page", fail_target_detach,
			)
			opened = main_window.open_file_path(str(source), replace_current=True)
		assert (opened, _failed_native_open_preserves_target(
			main_window, target,
		)) == (False, True)
	finally:
		_recover_target_after_forced_native_open_failure(main_window, target)


#============================================
def test_same_tab_native_open_releases_replaced_native_wrappers(
		main_window: bkchem_qt.main_window.MainWindow,
		qapp: PySide6.QtWidgets.QApplication, tmp_path: pathlib.Path,
		) -> None:
	"""A viable same-tab replacement disposes the old tab ownership graph."""
	source = tmp_path / "same-tab-success.cdml"
	source.write_text(_OPEN_ARROW_CDML, encoding="utf-8")
	target = main_window._active_session
	old_wrappers = (target, target.document, target.scene, target.view)
	try:
		opened = main_window.open_file_path(str(source), replace_current=True)
		replacement = main_window._active_session
		assert opened and replacement is not target and (
			_presentation_by_id(replacement.document, "arrow-1").kind == "arrow"
		)
		_drain_deferred_deletes(qapp, main_window)
		assert not any(shiboken6.isValid(wrapper) for wrapper in old_wrappers)
	finally:
		_restore_blank_anchor(main_window, main_window._active_session)
