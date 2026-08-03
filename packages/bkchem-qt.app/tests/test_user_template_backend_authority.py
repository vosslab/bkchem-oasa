"""Focused authority checks for session-delivered saved user templates."""

# Standard Library
import math

# local repo modules
import bkchem_qt.main_window
import bkchem_qt.io.user_template_catalog
import bkchem_qt.models.document_session
import bkchem_qt.models.projection_lifecycle
import oasa.cdml_document
import oasa.safe_xml


_SOURCE_CDML = (
	'<cdml xmlns:vendor="urn:vendor" version="26.07">'
	'<molecule id="source"><atom id="source_atom" name="C">'
	'<point x="2cm" y="3cm"/></atom></molecule>'
	'<vendor:note id="opaque">keep</vendor:note></cdml>'
)
_TEMPLATE_CDML = (
	'<cdml version="26.07"><molecule name="Saved template">'
	'<atom id="template_atom" name="C"><point x="1cm" y="2cm"/></atom>'
	'</molecule></cdml>'
)
_POINTS_PER_CM = 72.0 / 2.54


#============================================
def _entry(key: str, cdml: str = _TEMPLATE_CDML) -> object:
	"""Create one admitted immutable frontend delivery record."""
	return bkchem_qt.io.user_template_catalog.UserTemplateCatalogEntry(
		key, "Saved template", cdml,
	)


#============================================
def _session(main_window: bkchem_qt.main_window.MainWindow, entries: tuple[object, ...]) -> object:
	"""Register one native session with explicit frozen user-template delivery."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(_SOURCE_CDML)
	session = bkchem_qt.models.document_session.DocumentSession(
		parent=main_window, theme_manager=main_window._theme_manager,
		prefs=main_window._prefs, mode_host=main_window, view_parent=main_window,
		prepared_native_cdml=prepared, user_template_catalog=entries,
	)
	registered = main_window._register_session(session, activate=True)
	if registered.retry_current_backend_projection().status != "accepted":
		raise RuntimeError("User-template test session could not project")
	return registered


#============================================
def _molecule_centroids(snapshot: object) -> dict[str, tuple[float, float]]:
	"""Return direct molecule atom centroids in scene points from CDML only."""
	document = oasa.cdml_document.CDMLDocument.parse(snapshot.cdml, validation="strict")
	centroids = {}
	for record in document.objects():
		if record.local_name != "molecule" or record.identifier is None:
			continue
		root = oasa.safe_xml.parse_xml_string(record.raw_xml)
		points = []
		for element in root.iter():
			if str(element.tag).rsplit("}", 1)[-1] == "point":
				points.append((
					float(element.attrib["x"].removesuffix("cm")) * _POINTS_PER_CM,
					float(element.attrib["y"].removesuffix("cm")) * _POINTS_PER_CM,
				))
		centroids[record.identifier] = tuple(
			math.fsum(axis) / len(points) for axis in zip(*points)
		)
	return centroids


#============================================
def test_session_placement_inserts_frozen_template_at_anchor_and_backend_undo(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A session-owned placement capability creates one detached OASA molecule and history."""
	session = _session(main_window, (_entry("saved-a"),))
	try:
		before = session.backend_snapshot
		source_centroid = _molecule_centroids(before)["source"]
		session.submit_user_template("saved-a", (144.0, 216.0))
		after = session.backend_snapshot
		undo = session.undo_backend()
		centroids = _molecule_centroids(after)
		source_unchanged = centroids["source"] == source_centroid
		inserted_ids = frozenset(
			identifier for identifier in centroids if identifier != "source"
		)
		inserted_at_anchor = any(
			identifier != "source" and centroid == (144.0, 216.0)
			for identifier, centroid in centroids.items()
		)
		assert source_unchanged and inserted_at_anchor
		restored_centroids = _molecule_centroids(session.backend_snapshot)
		inserted_removed = inserted_ids.isdisjoint(restored_centroids)
		assert (
			undo.status == "accepted"
			and restored_centroids["source"] == source_centroid
			and inserted_removed
		)
	finally:
		main_window._remove_session(session)


#============================================
def test_catalog_replacement_is_session_neutral_and_removed_keys_reject_atomically(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A fresh session configuration changes delivery keys without document mutation."""
	session = _session(main_window, (_entry("saved-a"),))
	try:
		before = session.backend_snapshot
		session.replace_user_template_catalog((_entry("saved-b"),))
		removed = session.submit_user_template("saved-a", (1.0, 2.0))
		assert removed.failure_kind == "validation" and session.backend_snapshot == before
		current = session.submit_user_template("saved-b", (1.0, 2.0))
		assert current.status == "accepted" and current.submitted
	finally:
		main_window._remove_session(session)


#============================================
def test_stale_user_template_request_rejects_before_catalog_resolution(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A stale request remains a revision conflict even with an unknown key."""
	session = _session(main_window, (_entry("saved-a"),))
	try:
		captured_revision = session.backend_snapshot.revision
		session.submit_user_template("saved-a", (0.0, 0.0))
		after = session.backend_snapshot
		request = bkchem_qt.models.document_session.build_user_template_insert_request(
			captured_revision, "unknown-key", (0.0, 0.0),
		)
		outcome = session.submit_persistent_operation(request)
		assert outcome.failure_kind == "revision-conflict"
		assert session.backend_snapshot == after
	finally:
		main_window._remove_session(session)


#============================================
def test_retained_placement_capability_stays_bound_to_its_origin_tab(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Activating tab B cannot redirect a retained tab-A placement capability."""
	first = _session(main_window, (_entry("saved-a"),))
	second = _session(main_window, (_entry("saved-a"),))
	try:
		place_from_first = first.submit_user_template
		first_before = first.backend_snapshot
		second_before = second.backend_snapshot
		main_window._activate_session(second)
		place_from_first("saved-a", (35.0, 45.0))
		assert first.backend_snapshot != first_before and first.can_undo_backend
		assert second.backend_snapshot == second_before
	finally:
		for session in (second, first):
			if session in main_window.sessions:
				main_window._remove_session(session)


#============================================
def test_retained_disposed_action_reports_typed_unavailability(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A previously captured session capability becomes a typed inert result on close."""
	session = _session(main_window, (_entry("saved-a"),))
	action = session.submit_user_template
	main_window._remove_session(session)
	outcome = action("saved-a", (5.0, 10.0))
	assert outcome.status == "unavailable" and not outcome.submitted and outcome.commit is None


#============================================
def test_projection_retry_reuses_accepted_snapshot_after_catalog_replacement(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Recovery installs the accepted snapshot even after its source key is removed."""
	session = _session(main_window, (_entry("saved-a"),))

	def unavailable(_snapshot: object) -> object:
		"""Return one typed frontend-only projection delivery failure."""
		return bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult(
			bkchem_qt.models.projection_lifecycle.ProjectionLifecycleStatus.INSTALLATION_FAILED,
			bkchem_qt.models.projection_lifecycle.ProjectionLifecyclePhase.INSTALLATION,
		)

	try:
		session.install_projection_lifecycle_port(
			bkchem_qt.models.projection_lifecycle.SessionProjectionLifecyclePort(session, unavailable),
		)
		outcome = session.submit_user_template("saved-a", (90.0, 120.0))
		accepted = session.backend_snapshot
		session.replace_user_template_catalog(())
		session.install_projection_lifecycle_port(
			bkchem_qt.models.projection_lifecycle.SessionProjectionLifecyclePort(
				session, session.replace_projection_from_backend_snapshot,
			),
		)
		retry = session.retry_current_backend_projection()
		assert outcome.submitted and outcome.commit is not None and outcome.status == "unavailable"
		assert retry.status == "accepted" and session.backend_snapshot == accepted
	finally:
		main_window._remove_session(session)
