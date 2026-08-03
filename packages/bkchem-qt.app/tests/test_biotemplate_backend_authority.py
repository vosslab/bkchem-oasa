"""Focused authority checks for OASA-owned BioTemplate placement."""

# Standard Library
import math
from types import SimpleNamespace

# PIP3 modules
import PySide6.QtCore
import pytest

# local repo modules
import bkchem_qt.main_window
import bkchem_qt.models.document_session
import bkchem_qt.models.projection_lifecycle
import bkchem_qt.modes.biotemplate_mode
import oasa.biomolecule_template_placement
import oasa.cdml_document
import oasa.safe_xml


_SOURCE_CDML = (
	'<cdml xmlns:vendor="urn:vendor" version="26.07">'
	'<molecule id="source_molecule"><atom id="source_atom" name="C">'
	'<point x="2cm" y="3cm"/></atom></molecule>'
	'<vendor:note id="opaque_root" marker="literal">keep'
	'<vendor:detail>payload</vendor:detail>tail</vendor:note></cdml>'
)
_POINTS_PER_CM = 72.0 / 2.54


#============================================
def _active_session(main_window: object) -> object:
	"""Return the session that owns the visible document projection."""
	for session in main_window.sessions:
		if session.document is main_window.document and session.scene is main_window.scene:
			return session
	raise AssertionError("Main window has no active document session")


#============================================
def _native_session(main_window: bkchem_qt.main_window.MainWindow, cdml: str) -> object:
	"""Install one native backend session through the established test setup seam."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(cdml)
	session = main_window._construct_session(prepared_native_cdml=prepared)
	registered = main_window._register_session(session, activate=True)
	if not main_window._replace_session_projection(registered, registered.backend_snapshot):
		raise RuntimeError("Native CDML projection is unavailable")
	return registered


#============================================
def _mode(session: object) -> bkchem_qt.modes.biotemplate_mode.BioTemplateMode:
	"""Activate and return this session's BioTemplate projection client."""
	session.mode_manager.set_mode("biotemplate")
	mode = session.mode_manager.current_mode
	if not isinstance(mode, bkchem_qt.modes.biotemplate_mode.BioTemplateMode):
		raise AssertionError("BioTemplateMode did not activate")
	return mode


#============================================
def _select_template(mode: object, catalog_key: str) -> None:
	"""Select one known catalog key through the public submode callback."""
	mode.on_submode_switch(1, catalog_key)


#============================================
def _selected_molecule_ids(session: object) -> set[str]:
	"""Return durable molecule IDs represented by the selected current projection."""
	return {
		item.molecule_model.mol_id
		for item in session.scene.selectedItems()
		if getattr(item, "molecule_model", None) is not None
	}


#============================================
def _molecule_centroid(snapshot: object, molecule_id: str) -> tuple[float, float]:
	"""Read one accepted molecule's atom-point centroid in scene points."""
	document = oasa.cdml_document.CDMLDocument.parse(snapshot.cdml, validation="strict")
	record = document.find_by_id(molecule_id)
	if record is None:
		raise AssertionError("Accepted molecule is absent")
	root = oasa.safe_xml.parse_xml_string(record.raw_xml)
	points = []
	for element in root.iter():
		if str(element.tag).rsplit("}", 1)[-1] != "point":
			continue
		points.append((
			float(element.attrib["x"].removesuffix("cm")) * _POINTS_PER_CM,
			float(element.attrib["y"].removesuffix("cm")) * _POINTS_PER_CM,
		))
	if not points:
		raise AssertionError("Accepted molecule has no atom points")
	return tuple(math.fsum(axis) / len(points) for axis in zip(*points))


#============================================
def test_mode_emits_exact_plain_catalog_key_and_scene_anchor(main_window: object) -> None:
	"""Mode interaction delegates one known key and event point without a local edit."""
	session = _active_session(main_window)
	mode = _mode(session)
	intent = SimpleNamespace(catalog_key=None, anchor=None)

	def capture_intent(catalog_key: str, anchor: tuple[float, float]) -> object:
		"""Retain the immutable plain intent delivered by the mode action."""
		intent.catalog_key = catalog_key
		intent.anchor = anchor
		return SimpleNamespace(message="queued")

	_select_template(mode, "carbs/rings/furanose_scaffold")
	mode.set_biotemplate_action(capture_intent)
	before = session.backend_snapshot
	mode.mouse_press(PySide6.QtCore.QPointF(21.5, -37.25), None)
	assert intent.catalog_key == "carbs/rings/furanose_scaffold" and intent.anchor == (21.5, -37.25)
	assert session.backend_snapshot == before


#============================================
def test_synchronized_click_preserves_source_and_opaque_content_as_detached_root(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""An atom-area click anchors a detached root without changing source records."""
	session = _native_session(main_window, _SOURCE_CDML)
	try:
		before = session.backend_snapshot
		before_document = oasa.cdml_document.CDMLDocument.parse(before.cdml, validation="strict")
		mode = _mode(session)
		_select_template(mode, "carbs/rings/furanose_scaffold")
		anchor = PySide6.QtCore.QPointF(2.0 * _POINTS_PER_CM, 3.0 * _POINTS_PER_CM)
		mode.mouse_press(anchor, None)
		after = session.backend_snapshot
		inserted_ids = _selected_molecule_ids(session)
		inserted_id = next(iter(inserted_ids))
		after_document = oasa.cdml_document.CDMLDocument.parse(after.cdml, validation="strict")
		unchanged_source = (
			after_document.find_by_id("source_molecule").raw_xml
			== before_document.find_by_id("source_molecule").raw_xml
			and after_document.find_by_id("opaque_root").raw_xml
			== before_document.find_by_id("opaque_root").raw_xml
		)
		assert inserted_id != "source_molecule" and _molecule_centroid(after, inserted_id) == pytest.approx(anchor.toTuple())
		assert unchanged_source and inserted_ids == {inserted_id}
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_stale_biotemplate_request_rejects_before_oasa_preparation(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Revision rejection prevents catalog preparation and leaves state unchanged."""
	session = _active_session(main_window)
	before = session.backend_snapshot
	calls = []
	original_prepare = oasa.biomolecule_template_placement.prepare_biomolecule_template_insertion

	def count_preparation(request: object) -> object:
		"""Record preparation only when the stale guard failed."""
		calls.append(request)
		return original_prepare(request)

	monkeypatch.setattr(
		oasa.biomolecule_template_placement,
		"prepare_biomolecule_template_insertion", count_preparation,
	)
	request = bkchem_qt.models.document_session.PersistentOperationRequest(
		"biotemplate.insert", "Place Biomolecule Template",
		(("expected_revision", before.revision + 1), ("catalog_key", "carbs/rings/furanose_scaffold"), ("anchor", (0.0, 0.0))),
	)
	outcome = session.submit_persistent_operation(request)
	assert outcome.status == "rejected" and not calls
	assert session.backend_snapshot == before


#============================================
def test_invalid_or_unavailable_biotemplate_intents_leave_backend_unchanged(
		main_window: object,
		) -> None:
	"""Session validation and an unavailable mode action retain the exact snapshot."""
	session = _active_session(main_window)
	mode = _mode(session)
	before = session.backend_snapshot
	mode.set_biotemplate_action(None)
	mode.mouse_press(PySide6.QtCore.QPointF(10.0, 15.0), None)
	invalid = session.submit_persistent_operation(
		bkchem_qt.models.document_session.PersistentOperationRequest(
			"biotemplate.insert", "Place Biomolecule Template",
			(("expected_revision", before.revision), ("catalog_key", "unknown"), ("anchor", (0.0, 0.0))),
		),
	)
	assert invalid.status == "rejected" and invalid.failure_kind == "validation"
	assert session.backend_snapshot == before


#============================================
def test_two_biotemplate_placements_have_distinct_durable_ids_and_backend_undo_redo(
		main_window: object,
		) -> None:
	"""Two separately selected accepted roots have durable identity and history."""
	session = _active_session(main_window)
	mode = _mode(session)
	_select_template(mode, "carbs/rings/furanose_scaffold")
	mode.mouse_press(PySide6.QtCore.QPointF(30.0, 40.0), None)
	first_id = next(iter(_selected_molecule_ids(session)))
	mode.mouse_press(PySide6.QtCore.QPointF(130.0, 140.0), None)
	second_id = next(iter(_selected_molecule_ids(session)))
	accepted = session.backend_snapshot
	undone = session.undo_backend()
	redone = session.redo_backend()
	assert first_id and second_id and first_id != second_id
	assert undone.status == "accepted" and redone.status == "accepted" and session.backend_snapshot.cdml == accepted.cdml


#============================================
def test_biotemplate_action_remains_bound_to_its_originating_tab(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A retained session-A mode acts on A after tab B becomes active."""
	first_session = _native_session(main_window, _SOURCE_CDML)
	second_session = _native_session(main_window, _SOURCE_CDML)
	try:
		first_mode = _mode(first_session)
		_select_template(first_mode, "carbs/rings/furanose_scaffold")
		first_before = first_session.backend_snapshot
		second_before = second_session.backend_snapshot
		main_window._activate_session(second_session)
		first_mode.mouse_press(PySide6.QtCore.QPointF(110.0, 120.0), None)
		assert first_session.backend_snapshot.revision == first_before.revision + 1
		assert second_session.backend_snapshot == second_before
	finally:
		for session in (second_session, first_session):
			if session in main_window.sessions:
				main_window._remove_session(session)


#============================================
def test_disposed_biotemplate_action_reports_typed_unavailability(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A retained public placement action is inert after its tab's disposal begins."""
	session = _native_session(main_window, _SOURCE_CDML)
	action = session.submit_biomolecule_template
	main_window._remove_session(session)
	outcome = action("carbs/rings/furanose_scaffold", (5.0, 10.0))
	assert outcome.status == "unavailable" and not outcome.submitted
	assert session not in main_window.sessions and outcome.commit is None


#============================================
def test_accepted_biotemplate_projection_retry_preserves_selection_without_resubmission(
		main_window: bkchem_qt.main_window.MainWindow, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Exact retry restores one accepted root without recreating its proposal."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(_SOURCE_CDML)
	session = bkchem_qt.models.document_session.DocumentSession(
		parent=main_window, theme_manager=main_window._theme_manager,
		prefs=main_window._prefs, mode_host=main_window, prepared_native_cdml=prepared,
	)

	def unavailable(_snapshot: object) -> object:
		"""Report one post-acceptance projection installation failure."""
		return bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult(
			bkchem_qt.models.projection_lifecycle.ProjectionLifecycleStatus.INSTALLATION_FAILED,
			bkchem_qt.models.projection_lifecycle.ProjectionLifecyclePhase.INSTALLATION,
		)

	try:
		session.install_projection_lifecycle_port(
			bkchem_qt.models.projection_lifecycle.SessionProjectionLifecyclePort(
				session, session.replace_projection_from_backend_snapshot,
			),
		)
		if session.retry_current_backend_projection().status != "accepted":
			raise RuntimeError("BioTemplate test session did not project")
		baseline_ids = {
			record.identifier
			for record in oasa.cdml_document.CDMLDocument.parse(
				session.backend_snapshot.cdml, validation="strict",
			).objects()
			if record.local_name == "molecule" and record.identifier is not None
		}
		session.install_projection_lifecycle_port(
			bkchem_qt.models.projection_lifecycle.SessionProjectionLifecyclePort(session, unavailable),
		)
		outcome = session.submit_biomolecule_template(
			"carbs/rings/furanose_scaffold", (280.0, 195.0),
		)
		assert outcome.status == "unavailable" and outcome.submitted and outcome.commit is not None
		assert session.backend_snapshot == outcome.commit.snapshot
		accepted = outcome.commit.snapshot
		accepted_ids = {
			record.identifier
			for record in oasa.cdml_document.CDMLDocument.parse(
				accepted.cdml, validation="strict",
			).objects()
			if record.local_name == "molecule" and record.identifier is not None
		}
		inserted_ids = accepted_ids - baseline_ids

		def preparation_must_not_run(_request: object) -> object:
			"""Make proposal recreation fail if retry resubmits accepted intent."""
			raise AssertionError("Projection retry recreated a BioTemplate proposal")

		monkeypatch.setattr(
			oasa.biomolecule_template_placement,
			"prepare_biomolecule_template_insertion", preparation_must_not_run,
		)
		session.install_projection_lifecycle_port(
			bkchem_qt.models.projection_lifecycle.SessionProjectionLifecyclePort(
				session, session.replace_projection_from_backend_snapshot,
			),
		)
		retry = session.retry_current_backend_projection()
		selected = _selected_molecule_ids(session)
		assert inserted_ids and retry.status == "accepted" and session.backend_snapshot == accepted
		assert session.backend_snapshot.revision == accepted.revision and selected == inserted_ids
	finally:
		main_window._dispose_session_later(session)
