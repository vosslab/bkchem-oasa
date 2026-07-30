"""Focused backend-authoritative behavior checks for detached TemplateMode placement."""

# Standard Library
import math

# PIP3 modules
import PySide6.QtCore
import pytest

# local repo modules
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.modes.draw_mode
import bkchem_qt.modes.template_mode
import oasa.cdml_document
import oasa.safe_xml


#============================================
def _active_session(main_window: object) -> object:
	"""Return the session owning the current public main-window projection."""
	for session in main_window.sessions:
		if session.document is main_window.document and session.scene is main_window.scene:
			return session
	raise AssertionError("Main window has no active document session")


#============================================
def _direct_children(element: object, name: str) -> tuple[object, ...]:
	"""Return direct compatibility-DOM children with one local CDML name."""
	return tuple(
		child for child in element.childNodes
		if getattr(child, "localName", None) == name
	)


#============================================
def _root_molecules(complete_cdml: str) -> tuple[object, ...]:
	"""Return direct-root molecules after the CDML boundary accepts the text."""
	accepted = oasa.cdml_document.CDMLDocumentSession.load(complete_cdml).snapshot().cdml
	document = oasa.safe_xml.parse_dom_from_string(accepted)
	return _direct_children(document.documentElement, "molecule")


#============================================
def _molecule_facts(molecule: object) -> tuple[tuple[str, str, str], ...]:
	"""Return durable atom identity and coordinate facts for one root molecule."""
	facts = []
	for atom in _direct_children(molecule, "atom"):
		points = _direct_children(atom, "point")
		if len(points) != 1:
			raise AssertionError("Canonical atom has no single direct coordinate point")
		point = points[0]
		facts.append(
			(atom.getAttribute("id"), point.getAttribute("x"), point.getAttribute("y")),
		)
	return tuple(facts)


#============================================
def _centroid(molecule: object) -> tuple[float, float]:
	"""Return one prepared root molecule's finite CDML atom centroid."""
	facts = _molecule_facts(molecule)
	if not facts:
		raise AssertionError("Prepared template molecule has no direct atoms")
	return (
		math.fsum(_coordinate_points(atom[1]) for atom in facts) / len(facts),
		math.fsum(_coordinate_points(atom[2]) for atom in facts) / len(facts),
	)


#============================================
def _coordinate_points(value: str) -> float:
	"""Convert the canonical CDML centimetre coordinate into scene points."""
	if not value.endswith("cm"):
		raise AssertionError("Template coordinates must use canonical centimetres")
	return float(value[:-2]) * 72.0 / 2.54


#============================================
def _template_mode(session: object) -> bkchem_qt.modes.template_mode.TemplateMode:
	"""Activate and return the session-owned Template mode."""
	session.mode_manager.set_mode("template")
	mode = session.mode_manager.current_mode
	if not isinstance(mode, bkchem_qt.modes.template_mode.TemplateMode):
		raise AssertionError("TemplateMode did not activate")
	mode.set_template("Me")
	return mode


#============================================
def _draw_mode(session: object) -> bkchem_qt.modes.draw_mode.DrawMode:
	"""Activate and return the session-owned Draw mode."""
	session.mode_manager.set_mode("draw")
	mode = session.mode_manager.current_mode
	if not isinstance(mode, bkchem_qt.modes.draw_mode.DrawMode):
		raise AssertionError("DrawMode did not activate")
	return mode


#============================================
def _draw_root_pair(session: object) -> str:
	"""Create one root molecule and return one atom's durable identity."""
	mode = _draw_mode(session)
	position = PySide6.QtCore.QPointF(120.0, 160.0)
	mode.mouse_press(position, None)
	mode.mouse_release(position, None)
	for molecule in _root_molecules(session.backend_snapshot.cdml):
		atoms = _molecule_facts(molecule)
		if atoms:
			return atoms[0][0]
	raise AssertionError("Draw did not create a canonical root atom")


#============================================
def _atom_item(scene: object, atom_id: str) -> object:
	"""Return the current projected item for one durable atom ID."""
	for item in scene.items():
		if (
			isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
			and item.atom_model.atom_id == atom_id
		):
			return item
	raise AssertionError("Current projection has no requested durable atom")


#============================================
def test_blank_template_click_commits_oasa_prepared_detached_molecule(
		main_window: object,
		) -> None:
	"""A blank click accepts one detached template centered at its scene anchor."""
	session = _active_session(main_window)
	mode = _template_mode(session)
	anchor = PySide6.QtCore.QPointF(240.0, 310.0)
	mode.mouse_press(anchor, None)
	molecules = _root_molecules(session.backend_snapshot.cdml)
	inserted = next((molecule for molecule in molecules if molecule.getAttribute("id")), None)
	if inserted is None:
		raise AssertionError("Template placement did not create a durable root molecule")
	selected_molecule_ids = {
		getattr(getattr(item, "molecule_model", None), "mol_id", None)
		for item in session.scene.selectedItems()
	}

	assert (
		_centroid(inserted) == pytest.approx((anchor.x(), anchor.y()), abs=0.1)
		and selected_molecule_ids == {inserted.getAttribute("id")}
	)


#============================================
def test_atom_anchor_template_click_preserves_source_and_stays_detached(
		main_window: object,
		) -> None:
	"""An atom click adds a separate anchored molecule without changing its source."""
	session = _active_session(main_window)
	atom_id = _draw_root_pair(session)
	source_item = _atom_item(session.scene, atom_id)
	anchor = (source_item.atom_model.x, source_item.atom_model.y)
	before_molecules = _root_molecules(session.backend_snapshot.cdml)
	before_source = next(
		molecule for molecule in before_molecules
		if any(fact[0] == atom_id for fact in _molecule_facts(molecule))
	)
	before_source_facts = _molecule_facts(before_source)
	mode = _template_mode(session)
	mode.mouse_press(PySide6.QtCore.QPointF(*anchor), None)
	after_molecules = _root_molecules(session.backend_snapshot.cdml)
	after_source = next(
		molecule for molecule in after_molecules
		if any(fact[0] == atom_id for fact in _molecule_facts(molecule))
	)
	inserted = next(
		molecule for molecule in after_molecules
		if molecule.getAttribute("id") != after_source.getAttribute("id")
	)

	assert (
		_molecule_facts(after_source) == before_source_facts
		and _centroid(inserted) == pytest.approx(anchor, abs=0.1)
	)


#============================================
def test_unknown_template_or_missing_durable_atom_identity_leaves_backend_unchanged(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Rejected catalog entries and unaddressable anchors retain the prior snapshot."""
	session = _active_session(main_window)
	mode = _template_mode(session)
	before = session.backend_snapshot
	monkeypatch.setattr(mode, "_current_template", "missing-template")
	mode.mouse_press(PySide6.QtCore.QPointF(30.0, 45.0), None)
	assert session.backend_snapshot == before

	atom_id = _draw_root_pair(session)
	mode = _template_mode(session)
	item = _atom_item(session.scene, atom_id)
	anchor = PySide6.QtCore.QPointF(item.atom_model.x, item.atom_model.y)
	before_missing_identity = session.backend_snapshot
	monkeypatch.setattr(type(item.atom_model), "atom_id", property(lambda _self: None))
	mode.mouse_press(anchor, None)
	assert session.backend_snapshot == before_missing_identity


#============================================
def test_template_projection_failure_retries_the_accepted_snapshot_only(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A public retry restores an accepted template snapshot without resubmission."""
	session = _active_session(main_window)
	install_projection = session._install_prepared_projection
	failure_pending = True

	def fail_first_projection_install(
			prepared: object, selected_keys: object, file_path: object,
			projected_snapshot: object,
			) -> None:
		"""Fail only the first installation of this accepted template snapshot."""
		nonlocal failure_pending
		if failure_pending:
			failure_pending = False
			raise RuntimeError("one-time template projection installation failure")
		install_projection(prepared, selected_keys, file_path, projected_snapshot)

	monkeypatch.setattr(session, "_install_prepared_projection", fail_first_projection_install)
	mode = _template_mode(session)
	mode.mouse_press(PySide6.QtCore.QPointF(80.0, 95.0), None)
	accepted_snapshot = session.backend_snapshot
	retry = session.retry_current_backend_projection()
	inserted_ids = {
		molecule.getAttribute("id")
		for molecule in _root_molecules(accepted_snapshot.cdml)
	}
	selected_ids = {
		getattr(getattr(item, "molecule_model", None), "mol_id", None)
		for item in session.scene.selectedItems()
	}

	assert (
		retry.status == "accepted"
		and session.backend_snapshot == accepted_snapshot
		and session.backend_projection_synchronized
		and selected_ids == inserted_ids
	)
