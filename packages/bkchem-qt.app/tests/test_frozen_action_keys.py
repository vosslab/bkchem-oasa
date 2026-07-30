"""Test that all action keys follow the frozen English key policy.

Validates that every registered action key:
- matches the dotted lowercase pattern
- contains no spaces, uppercase, or display-text fragments
- belongs to a known frozen set that can only grow, not shrink
"""

# Standard Library
import pathlib
import re

# local repo modules
import bkchem_qt.actions.action_registry
import bkchem_qt.actions.menu_builder
import bkchem_qt.actions.registrar_manifest
import bkchem_qt.io.format_bridge

# pattern: dotted lowercase, e.g. 'file.save', 'repair.clean_geometry'
_KEY_PATTERN = re.compile(r'^[a-z][a-z0-9]*(\.[a-z][a-z0-9_]*)+$')

# Frozen baseline of current shipped action keys.  Intentional release removals
# update this set with their focused action/menu absence regression.
_KNOWN_KEYS = frozenset({
	'file.new',
	'file.save',
	'file.save_as',
	'file.recovery_export',
	'file.save_as_template',
	'file.load',
	'file.load_same_tab',
	'file.properties',
	'file.close_tab',
	'file.exit',
	'edit.undo',
	'edit.redo',
	'edit.cut',
	'edit.copy',
	'edit.paste',
	'edit.selected_to_svg',
	'edit.select_all',
	'view.zoom_in',
	'view.zoom_out',
	'view.zoom_reset',
	'view.zoom_to_fit',
	'view.zoom_to_content',
	'insert.biomolecule_template',
	'align.top',
	'align.bottom',
	'align.left',
	'align.right',
	'align.center_h',
	'align.center_v',
	'object.scale',
	'object.bring_to_front',
	'object.send_back',
	'object.swap_on_stack',
	'object.vertical_mirror',
	'object.horizontal_mirror',
	'object.configure',
	'chemistry.info',
	'chemistry.check',
	'chemistry.expand_groups',
	'chemistry.oxidation_number',
	'chemistry.read_smiles',
	'chemistry.read_inchi',
	'chemistry.read_peptide',
	'chemistry.gen_smiles',
	'chemistry.set_name',
	'chemistry.create_fragment',
	'chemistry.view_fragments',
	'chemistry.convert_to_linear',
	'options.standard',
	'options.language',
	'options.logging',
	'options.inchi_path',
	'options.theme',
	'options.preferences',
	'repair.normalize_bond_lengths',
	'repair.snap_to_hex_grid',
	'repair.normalize_bond_angles',
	'repair.normalize_rings',
	'repair.straighten_bonds',
	'repair.clean_geometry',
	'help.keyboard_shortcuts',
	'help.about',
})


#============================================
class _FakeApp:
	"""Minimal stand-in for the main window used by action registrars.

	Returns a no-op callable for any attribute access so that
	handler=app.on_whatever resolves without AttributeError.
	"""

	def __init__(self) -> None:
		"""Initialize with required stubs for action registration."""
		self.document = _FakeDocument()
		self._scene = _FakeScene()

	def __getattr__(self, name: str) -> object:
		"""Return a no-op callable for any missing attribute."""
		return lambda *args, **kwargs: None

	def statusBar(self) -> object:
		"""Return a fake status bar."""
		return _FakeStatusBar()


#============================================
class _FakeDocument:
	"""Minimal stand-in for the document model."""

	def __init__(self) -> None:
		"""Initialize with empty molecule list and undo stack."""
		self.molecules = []
		self.undo_stack = _FakeUndoStack()
		self.selected_mols = []


#============================================
class _FakeUndoStack:
	"""Minimal stand-in for QUndoStack."""

	def undo(self) -> None:
		"""No-op undo."""

	def redo(self) -> None:
		"""No-op redo."""

	def canUndo(self) -> bool:
		"""Return False."""
		return False

	def canRedo(self) -> bool:
		"""Return False."""
		return False


#============================================
class _FakeScene:
	"""Minimal stand-in for the scene."""

	grid_spacing_pt = 40.0

	def items(self) -> list:
		"""Return empty item list."""
		return []


#============================================
class _FakeStatusBar:
	"""Minimal stand-in for the status bar."""

	def showMessage(self, msg: str, timeout: int = 0) -> None:
		"""No-op message display."""


#============================================
def _get_all_registered_keys() -> set:
	"""Register all actions and return the set of action IDs."""
	app = _FakeApp()
	registry = bkchem_qt.actions.action_registry.register_all_actions(app)
	all_actions = registry.all_actions()
	return set(all_actions.keys())


#============================================
def test_all_keys_match_dotted_pattern() -> None:
	"""Every action key must match ^[a-z][a-z0-9]*(\\.[a-z][a-z0-9_]*)+$."""
	keys = _get_all_registered_keys()
	assert len(keys) > 0, "No action keys registered"
	bad_keys = []
	for key in sorted(keys):
		if not _KEY_PATTERN.match(key):
			bad_keys.append(key)
	assert not bad_keys, (
		f"Action keys violate dotted lowercase pattern: {bad_keys}"
	)


#============================================
def test_no_spaces_or_uppercase_in_keys() -> None:
	"""No key should contain spaces or uppercase letters."""
	keys = _get_all_registered_keys()
	for key in sorted(keys):
		assert ' ' not in key, f"Action key contains space: {key!r}"
		assert key == key.lower(), f"Action key has uppercase: {key!r}"


#============================================
def test_current_supported_keys_are_registered() -> None:
	"""Every current shipped action key resolves during deterministic startup."""
	keys = _get_all_registered_keys()
	missing = _KNOWN_KEYS - keys
	assert not missing, (
		f"Current shipped action keys are missing: {sorted(missing)}"
	)


#============================================
def test_known_keys_count() -> None:
	"""Registered keys should be at least as many as the frozen set."""
	keys = _get_all_registered_keys()
	assert len(keys) >= len(_KNOWN_KEYS), (
		f"Expected at least {len(_KNOWN_KEYS)} keys, got {len(keys)}"
	)


#============================================
def test_qt_menu_exposes_smiles_without_inchi_export() -> None:
	"""The shipped Qt menu exposes SMILES without an InChI export action."""
	registry = bkchem_qt.actions.action_registry.register_all_actions(_FakeApp())
	menu_path = bkchem_qt.resource_paths.get_resource_path("menus.yaml")
	menu_action_ids = bkchem_qt.actions.menu_builder.required_menu_action_ids(
		str(menu_path)
	)

	assert "chemistry.gen_smiles" in registry
	assert (
		"chemistry.gen_inchi" not in registry
		and "chemistry.gen_inchi" not in menu_action_ids
	)


#============================================
def test_format_bridge_exposes_no_projection_derived_inchi_export() -> None:
	"""The Qt format boundary provides no model-to-InChI export adapter."""
	assert not hasattr(bkchem_qt.io.format_bridge, "export_inchi")


#============================================
def test_registrar_manifest_is_ordered_and_complete() -> None:
	"""The frozen startup authority lists every current registrar in order."""
	assert bkchem_qt.actions.registrar_manifest.ACTION_REGISTRAR_MODULES == (
		"bkchem_qt.actions.align_actions",
		"bkchem_qt.actions.chemistry_actions",
		"bkchem_qt.actions.edit_actions",
		"bkchem_qt.actions.file_actions",
		"bkchem_qt.actions.haworth_actions",
		"bkchem_qt.actions.help_actions",
		"bkchem_qt.actions.insert_actions",
		"bkchem_qt.actions.object_actions",
		"bkchem_qt.actions.options_actions",
		"bkchem_qt.actions.plugins_actions",
		"bkchem_qt.actions.pubchem_actions",
		"bkchem_qt.actions.repair_actions",
		"bkchem_qt.actions.view_actions",
	)


#============================================
def test_manifest_registration_does_not_depend_on_source_file_discovery(
		monkeypatch: object,
		) -> None:
	"""Manifest registration works when source-directory globbing is unavailable."""
	def unavailable_glob(*args: object, **kwargs: object) -> object:
		raise AssertionError("frozen startup must not discover action source files")

	monkeypatch.setattr(pathlib.Path, "glob", unavailable_glob)
	keys = _get_all_registered_keys()

	assert "file.new" in keys


#============================================
def test_every_required_menu_action_has_a_manifest_registrar() -> None:
	"""The shipped YAML menu has complete action coverage after manifest loading."""
	registry = bkchem_qt.actions.action_registry.register_all_actions(_FakeApp())
	menu_path = bkchem_qt.resource_paths.get_resource_path("menus.yaml")

	bkchem_qt.actions.menu_builder.preflight_required_menu_actions(
		registry, str(menu_path),
	)
