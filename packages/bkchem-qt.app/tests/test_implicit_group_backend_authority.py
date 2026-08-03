"""Focused Qt authority coverage for one implicit-group expansion."""

# PIP3 modules
import pytest

# local repo modules
import bkchem_qt.actions.chemistry_actions
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.group_item
import bkchem_qt.models.document_session
import bkchem_qt.models.projection_lifecycle
import oasa.cdml_document
import oasa.safe_xml


_CDML = (
	'<cdml version="26.07"><molecule id="m1">'
	'<atom id="a1" name="C"><point x="0cm" y="0cm"/></atom>'
	'<group id="g1" name="COOH" group-type="implicit">'
	'<point x="1cm" y="0cm"/></group>'
	'<bond id="b1" start="a1" end="g1" type="n1"/>'
	'</molecule></cdml>'
)


#============================================
def _native_session(main_window: object) -> object:
	"""Register one native session with its ordinary projection lifecycle."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(_CDML)
	session = main_window._register_session(
		main_window._construct_session(prepared_native_cdml=prepared), activate=True,
	)
	if not main_window._replace_session_projection(session, session.backend_snapshot):
		raise AssertionError("Native implicit-group projection is unavailable")
	return session


#============================================
def _group_item(session: object) -> object:
	"""Return the one current implicit group projection."""
	return next(
		item for item in session.scene.items()
		if isinstance(item, bkchem_qt.canvas.items.group_item.GroupItem)
	)


#============================================
def _projection_unavailable(_snapshot: object) -> object:
	"""Return one typed lifecycle failure without retaining a scene projection."""
	return bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult(
		bkchem_qt.models.projection_lifecycle.ProjectionLifecycleStatus.PREPARATION_UNAVAILABLE,
		bkchem_qt.models.projection_lifecycle.ProjectionLifecyclePhase.PREPARATION,
	)


#============================================
def _exterior_target(cdml_text: str) -> str:
	"""Read the accepted exterior-bond endpoint through hardened CDML parsing."""
	accepted = oasa.cdml_document.CDMLDocument.parse(cdml_text, validation="strict")
	dom = oasa.safe_xml.parse_dom_from_string(accepted.serialize())
	bond = next(element for element in dom.getElementsByTagName("bond")
		if element.getAttribute("id") == "b1")
	return bond.getAttribute("end")


#============================================
def _has_durable_id(cdml_text: str, identifier: str) -> bool:
	"""Return whether accepted CDML contains one durable identifier."""
	accepted = oasa.cdml_document.CDMLDocument.parse(cdml_text, validation="strict")
	dom = oasa.safe_xml.parse_dom_from_string(accepted.serialize())
	return any(
		element.getAttribute("id") == identifier
		for element in dom.getElementsByTagName("*")
	)


#============================================
def _accepted_projection_matches_intent(
		session: object, intent: dict[str, tuple[int, str, str]],
		before: object, selected_atom_ids: set[str], enabled_before: bool,
		) -> bool:
	"""Return whether one action used backend authority and canonical selection."""
	snapshot = session.backend_snapshot
	return all((
		enabled_before,
		intent["request"] == (before.revision, "m1", "g1"),
		snapshot.revision == before.revision + 1,
		snapshot.is_dirty,
		not _has_durable_id(snapshot.cdml, "g1"),
		selected_atom_ids == {_exterior_target(snapshot.cdml)},
		not session.document.undo_stack.canUndo(),
	))


#============================================
def test_expand_groups_uses_one_plain_backend_request_and_restores_replacement_selection(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""The selected current group is replaced through OASA with no Qt undo command."""
	session = _native_session(main_window)
	try:
		group = _group_item(session)
		group.setSelected(True)
		del group
		before = session.backend_snapshot
		intent: dict[str, tuple[int, str, str]] = {}
		original = session.submit_implicit_group_expand

		def submit(revision: int, molecule_id: str, group_id: str) -> object:
			"""Record the durable scalar intent crossing the Qt boundary."""
			intent["request"] = (revision, molecule_id, group_id)
			return original(revision, molecule_id, group_id)

		monkeypatch.setattr(session, "submit_implicit_group_expand", submit)
		enabled_before = main_window._registry.is_enabled("chemistry.expand_groups", main_window)
		bkchem_qt.actions.chemistry_actions._expand_groups(main_window)
		selected_atom_ids = {
			item.atom_model.backend_durable_id for item in session.scene.selectedItems()
			if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
		}

		assert _accepted_projection_matches_intent(
			session, intent, before, selected_atom_ids, enabled_before,
		)
		undone = session.undo_backend()
		assert undone.status == "accepted" and _has_durable_id(session.backend_snapshot.cdml, "g1")
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_accepted_implicit_expansion_recovers_only_the_accepted_snapshot(
		main_window: object,
		) -> None:
	"""A projection failure leaves one accepted backend expansion available for retry."""
	session = _native_session(main_window)
	try:
		failed_port = bkchem_qt.models.projection_lifecycle.SessionProjectionLifecyclePort(
			session, _projection_unavailable,
		)
		session.install_projection_lifecycle_port(failed_port)
		outcome = session.submit_implicit_group_expand(
			session.backend_snapshot.revision, "m1", "g1",
		)
		accepted = session.backend_snapshot
		recovery_port = bkchem_qt.models.projection_lifecycle.SessionProjectionLifecyclePort(
			session, session.replace_projection_from_backend_snapshot,
		)
		session.install_projection_lifecycle_port(recovery_port)
		recovered = session.retry_current_backend_projection()

		group_absent = not _has_durable_id(accepted.cdml, "g1")
		synchronized = session.backend_snapshot == accepted and session.backend_projection_synchronized

		assert outcome.status == "unavailable" and outcome.submitted and group_absent
		assert recovered.status == "accepted" and synchronized
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_expand_groups_rejects_legacy_isolated_projection_without_local_mutation(
		main_window: object,
		) -> None:
	"""An unsynchronized projection keeps its group as backend-owned CDML content."""
	session = _native_session(main_window)
	try:
		group = _group_item(session)
		group.setSelected(True)
		del group
		before = session.backend_snapshot
		session.document.mark_dirty()

		assert not main_window._registry.is_enabled("chemistry.expand_groups", main_window)
		bkchem_qt.actions.chemistry_actions._expand_groups(main_window)
		assert session.backend_snapshot == before and _has_durable_id(session.backend_snapshot.cdml, "g1")
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_expand_groups_ignores_a_foreign_group_projection(main_window: object) -> None:
	"""A same-model scene wrapper outside the current registry cannot address CDML."""
	session = _native_session(main_window)
	foreign = None
	try:
		current = _group_item(session)
		model = current.group_model
		current.setSelected(False)
		foreign = bkchem_qt.canvas.items.group_item.GroupItem(model)
		session.scene.addItem(foreign)
		foreign.setSelected(True)
		before = session.backend_snapshot

		assert not main_window._registry.is_enabled("chemistry.expand_groups", main_window)
		bkchem_qt.actions.chemistry_actions._expand_groups(main_window)
		assert session.backend_snapshot == before
		foreign.setSelected(False)
		foreign.dispose()
		session.scene.removeItem(foreign)
		del foreign
		foreign = None
		del current
		del model
	finally:
		if foreign is not None:
			foreign.dispose()
			session.scene.removeItem(foreign)
		if session in main_window.sessions:
			main_window._remove_session(session)
