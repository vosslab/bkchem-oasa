"""Behavioral checks for the Qt linear-form conversion action."""

# Standard Library
import math

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.actions.chemistry_actions
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.io.cdml_document_io
import bkchem_qt.undo.commands


#============================================
class _StatusBar:
	"""Minimal status sink used by action tests without a MainWindow."""

	#============================================
	def showMessage(self, message: str, timeout: int) -> None:
		"""Accept an action status message."""


#============================================
class _ActionApp:
	"""Small action owner exposing the handler's document and status contract."""

	#============================================
	def __init__(self, document: object) -> None:
		"""Store a document and stable status target."""
		self.document = document
		self._status_bar = _StatusBar()

	#============================================
	def statusBar(self) -> _StatusBar:
		"""Return the status sink used by the action."""
		return self._status_bar


#============================================
def _dispose(
		document: object, scene: PySide6.QtWidgets.QGraphicsScene,
		app: PySide6.QtWidgets.QApplication,
		) -> None:
	"""Release native scene and command references before Python teardown."""
	scene.clearSelection()
	document.clear()
	document.set_scene(None)
	bkchem_qt.undo.commands.dispose_undo_stack_graphics(document.undo_stack)
	document.undo_stack.clear()
	scene.clear()
	scene.deleteLater()
	document.deleteLater()
	PySide6.QtCore.QCoreApplication.sendPostedEvents(
		None, PySide6.QtCore.QEvent.Type.DeferredDelete,
	)
	app.processEvents()


#============================================
def _document_from_xml(molecule_xml: str) -> object:
	"""Load one compact editable molecule into a fresh Qt document."""
	xml = """<cdml version="0.15" xmlns="http://www.freesoftware.fsf.org/bkchem/cdml">"""
	xml += molecule_xml
	xml += "</cdml>"
	document = bkchem_qt.io.cdml_document_io.decode_compatibility_cdml_string(xml)
	return document


#============================================
def _project_and_select(
		document: object, scene: PySide6.QtWidgets.QGraphicsScene,
		atom_indexes: tuple[int, ...],
		) -> None:
	"""Project one molecule and select the requested atom items."""
	molecule = document.molecules[0]
	items_by_model = {}
	for atom in molecule.atoms:
		item = bkchem_qt.canvas.items.atom_item.AtomItem(atom)
		scene.addItem(item)
		items_by_model[atom] = item
	for bond in molecule.bonds:
		item = bkchem_qt.canvas.items.bond_item.BondItem(bond)
		scene.addItem(item)
	for index in atom_indexes:
		items_by_model[molecule.atoms[index]].setSelected(True)


#============================================
def _linear_snapshot(document: object) -> tuple:
	"""Return the persistent conversion state required for undo/redo checks."""
	molecule = document.molecules[0]
	fragment = molecule.fragments[0] if molecule.fragments else None
	snapshot = (
		tuple((atom.x, atom.y, atom.show_hydrogens) for atom in molecule.atoms),
		None if fragment is None else (
			fragment.fragment_type, fragment.atom_ids, fragment.bond_ids,
			tuple((property_model.name, property_model.value, property_model.type_name)
				for property_model in fragment.properties),
		),
		document.dirty,
	)
	return snapshot


#============================================
def _ignore_warning(parent: object, title: str, message: str) -> None:
	"""Suppress a native warning while verifying its no-mutation behavior."""


#============================================
def test_linear_form_conversion_records_metadata_and_round_trips_undo(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""A selected path becomes a horizontal fragment in one reversible edit."""
	document = _document_from_xml("""<molecule id="m1">
		<atom id="a1" name="C"><point x="1cm" y="1cm"/></atom>
		<atom id="a2" name="C"><point x="2cm" y="2cm"/></atom>
		<atom id="a3" name="O"><point x="3cm" y="1cm"/></atom>
		<bond id="b2" start="a2" end="a3" type="n" order="1"/>
		<bond id="b1" start="a1" end="a2" type="n" order="1"/></molecule>""")
	scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(scene)
	try:
		_project_and_select(document, scene, (0, 1, 2))
		document.molecules[0].atoms[1].show_hydrogens = False
		document.mark_clean()
		before = _linear_snapshot(document)
		bkchem_qt.actions.chemistry_actions._convert_to_linear(_ActionApp(document))
		after = _linear_snapshot(document)
		coordinates = tuple((atom.x, atom.y) for atom in document.molecules[0].atoms)
		property_model = after[1][3][0]
		successful_linear_form = (
			coordinates[0][1] == coordinates[1][1] == coordinates[2][1]
			and math.isclose(
				coordinates[2][0] - coordinates[1][0],
				coordinates[1][0] - coordinates[0][0], abs_tol=0.001,
			)
			and after[1][0:3] == ("linear_form", ("a1", "a2", "a3"), ("b1", "b2"))
			and property_model[0] == "bond_length"
			and float(property_model[1]) > 0.0
			and bool(property_model[2])
			and after[2]
		)
		document.undo_stack.undo()
		document.undo_stack.redo()
		redo_restored = _linear_snapshot(document) == after
		document.undo_stack.undo()
		assert (successful_linear_form, redo_restored, _linear_snapshot(document)) == (True, True, before)
	finally:
		_dispose(document, scene, qapp)


#============================================
def test_linear_form_rejects_no_selection_without_dirtying_document(
		qapp: PySide6.QtWidgets.QApplication,
		monkeypatch: object,
		) -> None:
	"""No selection reports a requirement and creates neither metadata nor undo."""
	document = _document_from_xml("""<molecule id="m1">
		<atom id="a1" name="C"><point x="1cm" y="1cm"/></atom></molecule>""")
	scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(scene)
	try:
		monkeypatch.setattr(PySide6.QtWidgets.QMessageBox, "warning", _ignore_warning)
		document.mark_clean()
		bkchem_qt.actions.chemistry_actions._convert_to_linear(_ActionApp(document))
		assert (document.molecules[0].fragments, document.dirty, document.undo_stack.count()) == ((), False, 0)
	finally:
		_dispose(document, scene, qapp)


#============================================
def test_linear_form_rejects_branched_component_without_mutation(
		qapp: PySide6.QtWidgets.QApplication,
		monkeypatch: object,
		) -> None:
	"""A fork cannot be represented as a single linear form and remains intact."""
	document = _document_from_xml("""<molecule id="m1">
		<atom id="a1" name="C"><point x="1cm" y="1cm"/></atom>
		<atom id="a2" name="C"><point x="2cm" y="1cm"/></atom>
		<atom id="a3" name="C"><point x="3cm" y="1cm"/></atom>
		<atom id="a4" name="O"><point x="2cm" y="2cm"/></atom>
		<bond id="b1" start="a1" end="a2" type="n" order="1"/>
		<bond id="b2" start="a2" end="a3" type="n" order="1"/>
		<bond id="b3" start="a2" end="a4" type="n" order="1"/></molecule>""")
	scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(scene)
	try:
		_project_and_select(document, scene, (0, 1, 2, 3))
		monkeypatch.setattr(PySide6.QtWidgets.QMessageBox, "warning", _ignore_warning)
		document.mark_clean()
		before = _linear_snapshot(document)
		bkchem_qt.actions.chemistry_actions._convert_to_linear(_ActionApp(document))
		assert (_linear_snapshot(document), document.undo_stack.count()) == (before, 0)
	finally:
		_dispose(document, scene, qapp)


#============================================
def test_linear_form_moves_a_uniquely_attached_external_branch(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""An unselected branch follows its one selected anchor during reflow."""
	document = _document_from_xml("""<molecule id="m1">
		<atom id="a1" name="C"><point x="1cm" y="1cm"/></atom>
		<atom id="a2" name="C"><point x="2cm" y="2cm"/></atom>
		<atom id="a3" name="C"><point x="3cm" y="1cm"/></atom>
		<atom id="a4" name="O"><point x="2cm" y="3cm"/></atom>
		<bond id="b1" start="a1" end="a2" type="n" order="1"/>
		<bond id="b2" start="a2" end="a3" type="n" order="1"/>
		<bond id="b3" start="a2" end="a4" type="n" order="1"/></molecule>""")
	scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(scene)
	try:
		_project_and_select(document, scene, (0, 1, 2))
		middle_before = (document.molecules[0].atoms[1].x, document.molecules[0].atoms[1].y)
		branch_before = (document.molecules[0].atoms[3].x, document.molecules[0].atoms[3].y)
		bkchem_qt.actions.chemistry_actions._convert_to_linear(_ActionApp(document))
		middle_after = (document.molecules[0].atoms[1].x, document.molecules[0].atoms[1].y)
		branch_after = (document.molecules[0].atoms[3].x, document.molecules[0].atoms[3].y)
		assert (
			branch_after[0] - branch_before[0], branch_after[1] - branch_before[1],
		) == (
			middle_after[0] - middle_before[0], middle_after[1] - middle_before[1],
		)
	finally:
		_dispose(document, scene, qapp)


#============================================
def test_linear_form_spacing_keeps_multiletter_glyphs_separate(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""The linear layout measures the same glyph bounds used by atom painting."""
	document = _document_from_xml("""<molecule id="m1"><atom id="a1" name="Cl"><point x="1cm" y="1cm"/></atom>
		<atom id="a2" name="Br"><point x="2cm" y="2cm"/></atom><bond id="b1" start="a1" end="a2" type="n" order="1"/></molecule>""")
	scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(scene)
	try:
		_project_and_select(document, scene, (0, 1))
		bkchem_qt.actions.chemistry_actions._convert_to_linear(_ActionApp(document))
		first, second = document.molecules[0].atoms
		_first_left, first_right = bkchem_qt.actions.chemistry_actions._linear_label_bounds(first)
		second_left, _second_right = bkchem_qt.actions.chemistry_actions._linear_label_bounds(second)
		assert first.x + first_right < second.x + second_left
	finally:
		_dispose(document, scene, qapp)


#============================================
def test_linear_form_rejects_ring_and_external_bridge_without_mutation(
		qapp: PySide6.QtWidgets.QApplication,
		monkeypatch: object,
		) -> None:
	"""Cycles and external links to two anchors never receive partial reflow."""
	monkeypatch.setattr(PySide6.QtWidgets.QMessageBox, "warning", _ignore_warning)
	documents = [
		(_document_from_xml("""<molecule id="ring"><atom id="a1" name="C"><point x="1cm" y="1cm"/></atom>
			<atom id="a2" name="C"><point x="2cm" y="1cm"/></atom><atom id="a3" name="C"><point x="2cm" y="2cm"/></atom>
			<bond id="b1" start="a1" end="a2" type="n" order="1"/><bond id="b2" start="a2" end="a3" type="n" order="1"/>
			<bond id="b3" start="a3" end="a1" type="n" order="1"/></molecule>"""), (0, 1, 2)),
		(_document_from_xml("""<molecule id="bridge"><atom id="a1" name="C"><point x="1cm" y="1cm"/></atom>
			<atom id="a2" name="C"><point x="2cm" y="2cm"/></atom><atom id="a3" name="O"><point x="3cm" y="1cm"/></atom>
			<bond id="b1" start="a1" end="a2" type="n" order="1"/><bond id="b2" start="a1" end="a3" type="n" order="1"/>
			<bond id="b3" start="a2" end="a3" type="n" order="1"/></molecule>"""), (0, 1)),
	]
	resources = []
	try:
		for document, selection in documents:
			scene = PySide6.QtWidgets.QGraphicsScene()
			document.set_scene(scene)
			resources.append((document, scene))
			_project_and_select(document, scene, selection)
			document.mark_clean()
			before = _linear_snapshot(document)
			bkchem_qt.actions.chemistry_actions._convert_to_linear(_ActionApp(document))
			assert (_linear_snapshot(document), document.undo_stack.count()) == (before, 0)
	finally:
		for document, scene in resources:
			_dispose(document, scene, qapp)


#============================================
def test_linear_form_rejects_multi_molecule_selection_without_mutation(
		qapp: PySide6.QtWidgets.QApplication,
		monkeypatch: object,
		) -> None:
	"""One conversion never joins independent document molecules."""
	document = bkchem_qt.io.cdml_document_io.decode_compatibility_cdml_string("""<cdml version="0.15"
		xmlns="http://www.freesoftware.fsf.org/bkchem/cdml"><molecule id="m1"><atom id="a1" name="C"><point x="1cm" y="1cm"/></atom></molecule>
		<molecule id="m2"><atom id="a2" name="O"><point x="2cm" y="1cm"/></atom></molecule></cdml>""")
	scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(scene)
	try:
		for molecule in document.molecules:
			item = bkchem_qt.canvas.items.atom_item.AtomItem(molecule.atoms[0])
			scene.addItem(item)
			item.setSelected(True)
		monkeypatch.setattr(PySide6.QtWidgets.QMessageBox, "warning", _ignore_warning)
		document.mark_clean()
		bkchem_qt.actions.chemistry_actions._convert_to_linear(_ActionApp(document))
		assert (tuple(molecule.fragments for molecule in document.molecules), document.dirty) == (((), ()), False)
	finally:
		_dispose(document, scene, qapp)


#============================================
#============================================
def test_later_geometry_edit_removes_stale_linear_fragment_and_undo_restores_it(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""A command snapshot prevents later bends from leaving false metadata."""
	document = _document_from_xml("""<molecule id="m1"><atom id="a1" name="C"><point x="1cm" y="1cm"/></atom>
		<atom id="a2" name="C"><point x="2cm" y="2cm"/></atom><bond id="b1" start="a1" end="a2" type="n" order="1"/></molecule>""")
	scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(scene)
	try:
		_project_and_select(document, scene, (0, 1))
		bkchem_qt.actions.chemistry_actions._convert_to_linear(_ActionApp(document))
		middle = document.molecules[0].atoms[1]
		before = (middle.x, middle.y)
		after = (middle.x, middle.y + 4.0)
		document.undo_stack.push(bkchem_qt.undo.commands.TransformGeometryCommand(
				[(middle, before, after)], [], "Bend Linear Form",
		))
		after_bend = document.molecules[0].fragments
		document.undo_stack.undo()
		after_undo = document.molecules[0].fragments
		document.undo_stack.redo()
		assert (after_bend, bool(after_undo), document.molecules[0].fragments) == ((), True, ())
	finally:
		_dispose(document, scene, qapp)
