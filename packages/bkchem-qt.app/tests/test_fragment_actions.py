"""Focused command and persistence behavior for Qt fragment actions."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.actions.chemistry_actions
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.io.cdml_io
import bkchem_qt.models.fragment_model
import bkchem_qt.undo.commands


#============================================
class _ActionApp:
	"""Small action owner exposing the document contract used by the handlers."""

	#============================================
	def __init__(self, document: object) -> None:
		"""Store the document used by one tested action."""
		self.document = document


#============================================
def _dispose(
		document: object, scene: PySide6.QtWidgets.QGraphicsScene,
		app: PySide6.QtWidgets.QApplication,
		) -> None:
	"""Release scene and undo references before wrapper teardown."""
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
def _fragment_document() -> object:
	"""Return an editable two-atom CDML molecule with durable source IDs."""
	return bkchem_qt.io.cdml_io.load_cdml_document_string("""<cdml version="0.15"
		xmlns="http://www.freesoftware.fsf.org/bkchem/cdml">
		<molecule id="mol-1"><atom id="a1" name="C"><point x="1cm" y="1cm"/></atom>
		<atom id="a2" name="O"><point x="2cm" y="1cm"/></atom>
		<bond id="b1" start="a1" end="a2" type="n" order="1"/></molecule></cdml>""")


#============================================
def _fragment_input(
		parent: object, title: str, label: str, text: str = "",
		) -> tuple[str, bool]:
	"""Provide deterministic name input for the native Qt dialog."""
	return "alcohol", True


#============================================
def _fragment_type(
		parent: object, title: str, label: str, items: list[str],
		current: int, editable: bool,
		) -> tuple[str, bool]:
	"""Choose the first deterministic option from a native Qt item dialog."""
	return items[0], True


#============================================
def _cancel_fragment_name(
		parent: object, title: str, label: str, text: str = "",
		) -> tuple[str, bool]:
	"""Cancel the name prompt without mutating pending fragment IDs."""
	return "", False


#============================================
def test_create_fragment_action_undoes_metadata_without_mutating_graph(
		qapp: PySide6.QtWidgets.QApplication,
		monkeypatch: object,
		) -> None:
	"""Selected bond endpoints become one undoable, stable fragment."""
	document = _fragment_document()
	scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(scene)
	molecule = document.molecules[0]
	items = [
		bkchem_qt.canvas.items.atom_item.AtomItem(molecule.atoms[0]),
		bkchem_qt.canvas.items.bond_item.BondItem(molecule.bonds[0]),
	]
	try:
		for item in items:
			scene.addItem(item)
			item.setSelected(True)
		monkeypatch.setattr(PySide6.QtWidgets.QInputDialog, "getText", _fragment_input)
		monkeypatch.setattr(PySide6.QtWidgets.QInputDialog, "getItem", _fragment_type)
		bkchem_qt.actions.chemistry_actions._create_fragment(_ActionApp(document))
		after_create = molecule.fragments[0]
		document.undo_stack.undo()
		assert (
			after_create.name, after_create.atom_ids, after_create.bond_ids,
			not molecule.fragments, tuple(atom.symbol for atom in molecule.atoms),
		) == ("alcohol", ("a1", "a2"), ("b1",), True, ("C", "O"))
	finally:
		_dispose(document, scene, qapp)


#============================================
#============================================
#============================================
def test_view_fragments_deletes_selected_document_wide_duplicate_label(
		qapp: PySide6.QtWidgets.QApplication,
		monkeypatch: object,
		) -> None:
	"""Document-wide choices include context so the requested duplicate is removed."""
	document = bkchem_qt.io.cdml_io.load_cdml_document_string("""<cdml version="0.15"
		xmlns="http://www.freesoftware.fsf.org/bkchem/cdml"><molecule id="m1">
		<atom id="a1" name="C"><point x="1cm" y="1cm"/></atom></molecule><molecule id="m2">
		<atom id="a2" name="O"><point x="2cm" y="1cm"/></atom></molecule></cdml>""")
	scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(scene)
	first, second = document.molecules
	first.add_fragment(bkchem_qt.models.fragment_model.FragmentModel(
		fragment_id="first", fragment_type="explicit", name="same", atom_ids=("a1",), bond_ids=(),
	))
	second.add_fragment(bkchem_qt.models.fragment_model.FragmentModel(
		fragment_id="second", fragment_type="explicit", name="same", atom_ids=("a2",), bond_ids=(),
	))
	second.retain_unsupported_fragment_xml("<fragment id=\"retained\" type=\"legacy\"/>")
	try:
		monkeypatch.setattr(
			PySide6.QtWidgets.QInputDialog, "getItem",
			lambda parent, title, label, items, current, editable: (items[-1], True),
		)
		bkchem_qt.actions.chemistry_actions._view_fragments(_ActionApp(document))
		assert (
			tuple(fragment.fragment_id for molecule in document.molecules for fragment in molecule.fragments),
			second.unsupported_fragment_xml,
		) == (("first",), ("<fragment id=\"retained\" type=\"legacy\"/>",))
	finally:
		_dispose(document, scene, qapp)


#============================================
def test_cancelled_fragment_creation_leaves_missing_id_unchanged(
		qapp: PySide6.QtWidgets.QApplication,
		monkeypatch: object,
		) -> None:
	"""Cancelling before confirmation leaves the selected graph untouched."""
	document = _fragment_document()
	scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(scene)
	molecule = document.molecules[0]
	item = bkchem_qt.canvas.items.atom_item.AtomItem(molecule.atoms[0])
	try:
		scene.addItem(item)
		item.setSelected(True)
		molecule.atoms[0]._chem_atom.id = ""
		monkeypatch.setattr(PySide6.QtWidgets.QInputDialog, "getText", _cancel_fragment_name)
		bkchem_qt.actions.chemistry_actions._create_fragment(_ActionApp(document))
		assert (molecule.atoms[0]._chem_atom.id, molecule.fragments) == ("", ())
	finally:
		_dispose(document, scene, qapp)
