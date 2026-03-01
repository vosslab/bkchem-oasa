"""File menu actions for BKChem-Qt."""

# Standard Library
import os

# PIP3 modules
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.io.cdml_io
import bkchem_qt.bridge.oasa_bridge
import bkchem_qt.bridge.worker
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
from bkchem_qt.actions.action_registry import MenuAction

# file filter strings for QFileDialog
CDML_FILTER = "CDML Files (*.cdml);;SVG Files (*.svg);;All Files (*)"
CHEMISTRY_FILTER = (
	"Chemistry Files (*.cdml *.svg *.mol *.sdf *.smi *.cml *.cdxml);;"
	"CDML Files (*.cdml);;"
	"SVG Files (*.svg);;"
	"MOL Files (*.mol *.sdf);;"
	"SMILES Files (*.smi);;"
	"All Files (*)"
)

# map file extensions to OASA codec names for non-CDML formats
_EXTENSION_TO_CODEC = {
	".mol": "molfile",
	".sdf": "molfile",
	".smi": "smiles",
	".cml": "cml",
	".cdxml": "cdxml",
}


#============================================
def open_file(main_window) -> None:
	"""Show a file dialog and load the selected chemistry file.

	Prompts the user with a native file dialog filtered to supported
	chemistry formats. On selection, delegates to ``open_file_path()``
	to parse and display the file.

	Args:
		main_window: MainWindow instance providing scene and document.
	"""
	file_path, _selected_filter = PySide6.QtWidgets.QFileDialog.getOpenFileName(
		main_window,
		"Open Chemistry File",
		"",
		CHEMISTRY_FILTER,
	)
	if not file_path:
		return
	open_file_path(main_window, file_path)


#============================================
def open_file_path(main_window, file_path: str) -> None:
	"""Load a specific chemistry file by path and add to the scene.

	Determines the file format from the extension, parses the file
	through the appropriate loader (CDML or OASA codec), and adds
	the resulting molecules to the active scene.

	Args:
		main_window: MainWindow instance providing scene and document.
		file_path: Absolute or relative path to the file to load.
	"""
	ext = os.path.splitext(file_path)[1].lower()
	molecules = []

	if ext == ".cdml":
		# CDML files are small; load synchronously
		molecules = bkchem_qt.io.cdml_io.load_cdml_file(file_path)
		if molecules:
			_add_molecules_to_scene(main_window, molecules)
	elif ext in _EXTENSION_TO_CODEC:
		# use async worker for non-CDML formats (may be large)
		codec_name = _EXTENSION_TO_CODEC[ext]
		_load_with_worker(main_window, codec_name, file_path)
	else:
		# try CDML as a fallback for unknown extensions
		molecules = bkchem_qt.io.cdml_io.load_cdml_file(file_path)
		if molecules:
			_add_molecules_to_scene(main_window, molecules)


#============================================
def _load_with_worker(main_window, codec_name: str, file_path: str) -> None:
	"""Load a non-CDML file asynchronously using FileReaderWorker.

	Runs the OASA codec reader in a background thread so that large
	files do not freeze the GUI. On completion, converts the result
	to MoleculeModels and adds them to the scene.

	Args:
		main_window: MainWindow instance.
		codec_name: OASA codec name (e.g. 'molfile', 'smiles').
		file_path: Path to the chemistry file.
	"""
	worker = bkchem_qt.bridge.worker.FileReaderWorker(codec_name, file_path)

	def on_finished(oasa_mol):
		"""Handle successful file read by converting and displaying."""
		if oasa_mol is None:
			main_window.statusBar().showMessage("No molecules found", 3000)
			return
		# generate coordinates and convert to MoleculeModels
		from oasa import coords_generator
		coords_generator.calculate_coords(oasa_mol, bond_length=1.0, force=0)
		if not oasa_mol.is_connected():
			parts = oasa_mol.get_disconnected_subgraphs()
		else:
			parts = [oasa_mol]
		molecules = []
		for part in parts:
			mol_model = bkchem_qt.bridge.oasa_bridge.oasa_mol_to_qt_mol(part)
			molecules.append(mol_model)
		if molecules:
			_add_molecules_to_scene(main_window, molecules)
		main_window.statusBar().showMessage(
			"Loaded %d molecule(s)" % len(molecules), 3000,
		)

	def on_error(msg):
		"""Handle file read error."""
		PySide6.QtWidgets.QMessageBox.warning(
			main_window, "File Read Error", msg,
		)

	worker.finished.connect(on_finished)
	worker.error.connect(on_error)
	# keep a reference so the worker is not garbage collected
	main_window._active_worker = worker
	main_window.statusBar().showMessage("Loading file...", 0)
	worker.start()


#============================================
def _add_molecules_to_scene(main_window, molecules: list) -> None:
	"""Add a list of MoleculeModel objects to the active scene.

	For each molecule, creates AtomItem and BondItem graphics items,
	adds them to the scene, and stores the molecule in the document.
	Bond items are added before atom items so that atoms render on top.

	Args:
		main_window: MainWindow instance with ``_scene`` and optionally
			a ``_document`` attribute.
		molecules: List of MoleculeModel instances to display.
	"""
	scene = main_window._scene

	for mol_model in molecules:
		# map from AtomModel to AtomItem for bond endpoint lookup
		atom_items = {}

		# create AtomItems for every atom in the molecule
		for atom_model in mol_model.atoms:
			atom_item = bkchem_qt.canvas.items.atom_item.AtomItem(atom_model)
			scene.addItem(atom_item)
			atom_items[id(atom_model)] = atom_item

		# create BondItems for every bond in the molecule
		for bond_model in mol_model.bonds:
			bond_item = bkchem_qt.canvas.items.bond_item.BondItem(bond_model)
			scene.addItem(bond_item)

		# register the molecule with the document if available
		document = getattr(main_window, "_document", None)
		if document is not None:
			document.add_molecule(mol_model)


#============================================
def register_file_actions(registry, app) -> None:
	"""Register all File menu actions for BKChem-Qt.

	Maps each file action to the appropriate Qt handler method on the
	main window. Actions without a Qt implementation use a stub lambda
	that shows a status bar message.

	Args:
		registry: ActionRegistry instance to register actions with.
		app: The main BKChem-Qt application object providing handler methods.
	"""
	# create a new file in a new tab
	registry.register(MenuAction(
		id='file.new',
		label_key='New',
		help_key='Create a new file in a new tab',
		accelerator='(C-n)',
		handler=app._on_new,
		enabled_when=None,
	))
	# save the current file
	registry.register(MenuAction(
		id='file.save',
		label_key='Save',
		help_key='Save the file',
		accelerator='(C-s)',
		handler=app._on_save,
		enabled_when=None,
	))
	# save under a different name
	registry.register(MenuAction(
		id='file.save_as',
		label_key='Save As...',
		help_key='Save the file under a different name',
		accelerator='(C-S-s)',
		handler=lambda: app.statusBar().showMessage("Save As: not yet implemented", 3000),
		enabled_when=None,
	))
	# save as a template file
	registry.register(MenuAction(
		id='file.save_as_template',
		label_key='Save As Template',
		help_key='Save the file as template, certain criteria must be met for this to work',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage("Save As Template: not yet implemented", 3000),
		enabled_when=None,
	))
	# open a file in a new tab
	registry.register(MenuAction(
		id='file.load',
		label_key='Open',
		help_key='Open a file in a new tab',
		accelerator='(C-o)',
		handler=app._on_open,
		enabled_when=None,
	))
	# open a file replacing the current tab
	registry.register(MenuAction(
		id='file.load_same_tab',
		label_key='Open in same tab',
		help_key='Open a file replacing the current one',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage("Open in same tab: not yet implemented", 3000),
		enabled_when=None,
	))
	# document properties dialog
	registry.register(MenuAction(
		id='file.properties',
		label_key='Document Properties...',
		help_key='Set the paper size and other properties of the document',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage("Document Properties: not yet implemented", 3000),
		enabled_when=None,
	))
	# close the current tab
	registry.register(MenuAction(
		id='file.close_tab',
		label_key='Close tab',
		help_key='Close the current tab, exit when there is only one tab',
		accelerator='(C-w)',
		handler=lambda: app.statusBar().showMessage("Close tab: not yet implemented", 3000),
		enabled_when=None,
	))
	# exit the application
	registry.register(MenuAction(
		id='file.exit',
		label_key='Quit',
		help_key='Quit BKChem',
		accelerator='(C-q)',
		handler=app.close,
		enabled_when=None,
	))
