"""Behavioral coverage for OASA-backed repair actions."""

# Standard Library
import pathlib

# PIP3 modules
import PySide6.QtCore

# local repo modules
from oasa import cdml_document
import bkchem_qt.actions.repair_actions
import bkchem_qt.canvas.molecule_projection
import bkchem_qt.models.molecule_model


_TWO_REPAIR_MOLECULES_CDML = (
	'<cdml version="26.07"><molecule id="m1">'
	'<atom id="a1" name="C"><point x="1cm" y="1cm"/></atom>'
	'<atom id="a2" name="C"><point x="4cm" y="1cm"/></atom>'
	'<atom id="a3" name="O"><point x="3cm" y="3cm"/></atom>'
	'<bond id="b1" start="a1" end="a2" type="n1"/>'
	'<bond id="b2" start="a1" end="a3" type="n1"/>'
	'</molecule><molecule id="m2">'
	'<atom id="a4" name="C"><point x="9cm" y="1cm"/></atom>'
	'<atom id="a5" name="O"><point x="12cm" y="1cm"/></atom>'
	'<bond id="b3" start="a4" end="a5" type="n1"/>'
	'</molecule></cdml>'
)

_STRAIGHTEN_REPAIR_MOLECULES_CDML = (
	'<cdml version="26.07"><molecule id="m1">'
	'<atom id="a1" name="C"><point x="1cm" y="1cm"/></atom>'
	'<atom id="a2" name="O"><point x="4cm" y="2cm"/></atom>'
	'<bond id="b1" start="a1" end="a2" type="n1"/>'
	'</molecule><molecule id="m2">'
	'<atom id="a3" name="C"><point x="9cm" y="1cm"/></atom>'
	'<atom id="a4" name="O"><point x="12cm" y="1cm"/></atom>'
	'<bond id="b2" start="a3" end="a4" type="n1"/>'
	'</molecule></cdml>'
)

_RING_REPAIR_MOLECULES_CDML = (
	'<cdml version="26.07"><molecule id="m1">'
	'<atom id="a1" name="C"><point x="0cm" y="0cm"/></atom>'
	'<atom id="a2" name="C"><point x="2cm" y="0cm"/></atom>'
	'<atom id="a3" name="C"><point x="1.5cm" y="1cm"/></atom>'
	'<atom id="a4" name="C"><point x="0cm" y="1cm"/></atom>'
	'<bond id="rb1" start="a1" end="a2" type="n1"/>'
	'<bond id="rb2" start="a2" end="a3" type="n1"/>'
	'<bond id="rb3" start="a3" end="a4" type="n1"/>'
	'<bond id="rb4" start="a4" end="a1" type="n1"/>'
	'</molecule><molecule id="m2">'
	'<atom id="a5" name="C"><point x="9cm" y="1cm"/></atom>'
	'<atom id="a6" name="O"><point x="12cm" y="1cm"/></atom>'
	'<bond id="rb5" start="a5" end="a6" type="n1"/>'
	'</molecule></cdml>'
)


#============================================
def _draw_repair_target(
		main_window: object, x: float, y: float,
		) -> tuple[object, object]:
	"""Add one stretched two-atom molecule and return it with its bond."""
	molecule = bkchem_qt.models.molecule_model.MoleculeModel()
	first = molecule.create_atom(symbol="C")
	second = molecule.create_atom(symbol="C")
	first.set_xyz(x, y, 0.0)
	second.set_xyz(x + 120.0, y, 0.0)
	molecule.add_atom(first)
	molecule.add_atom(second)
	bond = molecule.create_bond(order=1, bond_type="n")
	molecule.add_bond(first, second, bond)
	main_window.document.add_molecule(molecule, mark_dirty=False)
	bkchem_qt.canvas.molecule_projection.project_molecules_to_scene(
		main_window.scene, [molecule],
	)
	return molecule, bond


#============================================
def _coordinates(molecule: object) -> tuple[tuple[float, float], ...]:
	"""Return molecule coordinates for behavior-level before/after checks."""
	coordinates = tuple((atom.x, atom.y) for atom in molecule.atoms)
	return coordinates


#============================================
def _molecule_xml(cdml_text: str, molecule_id: str) -> str:
	"""Return one authoritative molecule record from accepted CDML."""
	document = cdml_document.CDMLDocument.parse(cdml_text, validation="strict")
	record = document.find_by_id(molecule_id)
	if record is None:
		raise AssertionError("fixture molecule is absent: %s" % molecule_id)
	return record.raw_xml


#============================================
def test_selected_bond_normalization_requires_a_backend_identified_molecule(
		main_window: object,
		) -> None:
	"""Legacy-only Qt molecules remain unchanged by the authoritative route."""
	selected, selected_bond = _draw_repair_target(main_window, 100.0, 100.0)
	other, _other_bond = _draw_repair_target(main_window, 400.0, 100.0)
	for item in main_window.scene.items():
		if getattr(item, "bond_model", None) is selected_bond:
			item.setSelected(True)
	before = (_coordinates(selected), _coordinates(other))
	bkchem_qt.actions.repair_actions._handle_normalize_bond_lengths(main_window)

	assert (_coordinates(selected), _coordinates(other)) == before


#============================================
def test_angle_repair_mode_click_is_inert_without_a_backend_molecule_identity(
		main_window: object,
		) -> None:
	"""Click normalization leaves an unsynchronized Qt-only molecule unchanged."""
	clicked, _clicked_bond = _draw_repair_target(main_window, 100.0, 100.0)
	other, _other_bond = _draw_repair_target(main_window, 400.0, 100.0)
	main_window.scene.clearSelection()
	main_window._mode_manager.set_mode("repair")
	repair_mode = main_window._mode_manager.current_mode
	repair_mode._active_submode_key = "normalize-angles"
	session = getattr(main_window, "_active_session", None)
	before = (
		_coordinates(clicked), _coordinates(other), main_window.document.dirty,
		main_window.document.undo_stack.count(),
	)
	before_revision = None
	if session is not None and session.backend_projection_synchronized:
		before_revision = session.backend_snapshot.revision
	repair_mode.mouse_press(PySide6.QtCore.QPointF(100.0, 100.0), None)

	assert (
		_coordinates(clicked), _coordinates(other), main_window.document.dirty,
		main_window.document.undo_stack.count(),
	) == before
	if before_revision is not None:
		assert session.backend_snapshot.revision == before_revision


#============================================
def test_clean_geometry_requires_a_backend_identified_molecule(
		main_window: object,
		) -> None:
	"""Clean Geometry leaves legacy-only scene models outside the backend route."""
	first, _first_bond = _draw_repair_target(main_window, 0.0, 100.0)
	second, _second_bond = _draw_repair_target(main_window, 400.0, 100.0)
	main_window.document.mark_clean()
	before = (_coordinates(first), _coordinates(second))
	bkchem_qt.actions.repair_actions._handle_clean_geometry(main_window)

	assert (_coordinates(first), _coordinates(second), main_window.document.dirty) == (
		before[0], before[1], False,
	)


#============================================
def test_clean_geometry_target_requires_a_backend_identified_molecule(
		main_window: object,
		) -> None:
	"""Explicit legacy-only targets cannot create a local Clean Geometry edit."""
	molecule, _bond = _draw_repair_target(main_window, 100.0, 100.0)
	main_window.document.mark_clean()
	before = _coordinates(molecule)
	bkchem_qt.actions.repair_actions._handle_clean_geometry(
		main_window, target_molecule=molecule,
	)

	assert (_coordinates(molecule), main_window.document.dirty) == (before, False)


#============================================
def test_angle_repair_mode_click_changes_only_the_clicked_durable_molecule(
		main_window: object, tmp_path: pathlib.Path,
		) -> None:
	"""Angle click changes its root without rewriting the second CDML molecule."""
	source = tmp_path / "repair-mode-angle.cdml"
	source.write_text(_TWO_REPAIR_MOLECULES_CDML, encoding="utf-8")
	assert main_window.open_file_path(str(source))
	session = main_window._active_session
	before = session.backend_snapshot.cdml
	for item in session.scene.items():
		if getattr(getattr(item, "atom_model", None), "backend_durable_id", None) == "a1":
			click_point = item.scenePos()
			break
	else:
		raise AssertionError("fixture did not project a clickable durable atom")
	del item
	main_window._mode_manager.set_mode("repair")
	repair_mode = main_window._mode_manager.current_mode
	repair_mode._active_submode_key = "normalize-angles"
	repair_mode.mouse_press(click_point, None)
	after = session.backend_snapshot.cdml

	assert (
		_molecule_xml(after, "m1") != _molecule_xml(before, "m1")
		and _molecule_xml(after, "m2") == _molecule_xml(before, "m2")
	)


#============================================
def test_straighten_repair_mode_click_changes_only_the_clicked_durable_molecule(
		main_window: object, tmp_path: pathlib.Path,
		) -> None:
	"""Straighten submits only the clicked durable molecule to OASA."""
	source = tmp_path / "repair-mode-straighten.cdml"
	source.write_text(_STRAIGHTEN_REPAIR_MOLECULES_CDML, encoding="utf-8")
	assert main_window.open_file_path(str(source))
	session = main_window._active_session
	before = session.backend_snapshot.cdml
	for item in session.scene.items():
		if getattr(getattr(item, "atom_model", None), "backend_durable_id", None) == "a1":
			click_point = item.scenePos()
			break
	else:
		raise AssertionError("fixture did not project a clickable durable atom")
	del item
	main_window._mode_manager.set_mode("repair")
	repair_mode = main_window._mode_manager.current_mode
	repair_mode._active_submode_key = "straighten"
	repair_mode.mouse_press(click_point, None)
	after = session.backend_snapshot.cdml

	assert (
		_molecule_xml(after, "m1") != _molecule_xml(before, "m1")
		and _molecule_xml(after, "m2") == _molecule_xml(before, "m2")
	)


#============================================
def test_ring_repair_mode_click_uses_backend_history_without_qt_undo(
		main_window: object, tmp_path: pathlib.Path,
		) -> None:
	"""A durable ring click replaces its projection through the session boundary."""
	source = tmp_path / "repair-mode-ring.cdml"
	source.write_text(_RING_REPAIR_MOLECULES_CDML, encoding="utf-8")
	assert main_window.open_file_path(str(source))
	session = main_window._active_session
	before = session.backend_snapshot.cdml
	for item in session.scene.items():
		if getattr(getattr(item, "atom_model", None), "backend_durable_id", None) == "a1":
			click_point = item.scenePos()
			break
	else:
		raise AssertionError("fixture did not project a clickable durable ring atom")
	del item
	main_window._mode_manager.set_mode("repair")
	repair_mode = main_window._mode_manager.current_mode
	repair_mode._active_submode_key = "normalize-rings"
	repair_mode.mouse_press(click_point, None)
	after = session.backend_snapshot.cdml
	only_target_changed = (
		_molecule_xml(after, "m1") != _molecule_xml(before, "m1")
		and _molecule_xml(after, "m2") == _molecule_xml(before, "m2")
	)
	backend_without_qt_undo = (
		session.can_undo_backend and not session.document.undo_stack.canUndo()
	)

	assert only_target_changed
	assert backend_without_qt_undo


#============================================
def test_straighten_repair_mode_click_is_inert_without_a_backend_molecule_identity(
		main_window: object,
		) -> None:
	"""An ID-less click cannot create a local Straighten Bonds mutation."""
	clicked, _clicked_bond = _draw_repair_target(main_window, 100.0, 100.0)
	other, _other_bond = _draw_repair_target(main_window, 400.0, 100.0)
	main_window.scene.clearSelection()
	main_window._mode_manager.set_mode("repair")
	repair_mode = main_window._mode_manager.current_mode
	repair_mode._active_submode_key = "straighten"
	before = (
		_coordinates(clicked), _coordinates(other), main_window.document.dirty,
		main_window.document.undo_stack.count(),
	)
	repair_mode.mouse_press(PySide6.QtCore.QPointF(100.0, 100.0), None)

	assert (
		_coordinates(clicked), _coordinates(other), main_window.document.dirty,
		main_window.document.undo_stack.count(),
	) == before
