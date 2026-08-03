"""Mode system initialization for MainWindow."""

# Standard Library
import pathlib

# PIP3 modules
import yaml
import PySide6.QtCore

# local repo modules
import bkchem_qt.modes.config
import bkchem_qt.modes.mode_manager
import bkchem_qt.modes.template_mode
import bkchem_qt.modes.biotemplate_mode
import bkchem_qt.modes.user_template_mode
import bkchem_qt.modes.arrow_mode
import bkchem_qt.modes.text_mode
import bkchem_qt.modes.mark_mode
import bkchem_qt.modes.atom_mode
import bkchem_qt.modes.rotate_mode
import bkchem_qt.modes.bondalign_mode
import bkchem_qt.modes.bracket_mode
import bkchem_qt.modes.vector_mode
import bkchem_qt.modes.repair_mode
import bkchem_qt.modes.plus_mode
import bkchem_qt.modes.misc_mode
import bkchem_qt.modes.file_actions_mode
import bkchem_qt.resource_paths

# Modes are package-owned so installed Qt wheels do not need the source tree.
_MODES_YAML_PATH = bkchem_qt.resource_paths.get_resource_path("modes.yaml")


#============================================
def setup_modes(
		view: object, main_window: object,
		parent: PySide6.QtCore.QObject | None = None,
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
	"""Create and register all interaction modes.

	Args:
		view: The ChemView widget that owns the modes.
		main_window: The MainWindow (for file_actions_mode).
		parent: Optional QObject owner for the manager and its modes.  A
			DocumentSession supplies itself here so switching or closing a tab
			cannot retain mode callbacks for another session.
		persistent_action: Narrow plain-data callback used by migrated persistent
			modes.  It is deliberately not a window or Qt model.
		atom_align_action: Narrow session-owned callback accepting only an axis and
			immutable durable atom target pairs.
		atom_translate_action: Narrow session-owned callback accepting immutable
			durable atom target pairs and a plain scene-point delta.
		atom_rotate_action: Narrow session-owned callback accepting immutable
			durable atom target pairs, a plain scene-point center, and an angle.
		atom_translate_authority: Narrow frontend-only callback returning the
			current drag authority: backend, local, or unavailable.
		presentation_translate_action: Narrow session-owned callback accepting a
			captured revision, durable presentation root keys, and a plain scene-point
			delta for one backend-owned top-level translation.
		presentation_translate_context: Narrow frontend-only callback returning the
			current presentation-drag authority plus its captured backend revision.
		selection_translate_action: Narrow session-owned callback accepting a
			captured revision, durable atom pairs, presentation root keys, and one
			plain scene-point delta for one mixed backend-owned translation.
		selection_translate_context: Narrow frontend-only callback returning the
			current mixed-drag authority plus its captured backend revision.
		top_level_delete_context: Narrow frontend-only callback returning the
			current complete-root Delete authority plus its captured backend revision.
		structure_delete_context: Narrow frontend-only callback returning the
			current partial atom/bond Delete authority plus its captured backend
			revision.
		atom_mark_delete_context: Narrow frontend-only callback returning the
			current selected-mark Delete authority plus its captured backend revision.
		atom_number_context: Narrow plain-data callback from the session-owned
			backend snapshot for Misc atom-number presentation state.
		atom_mark_revision: Narrow plain-data callback returning the exact backend
			revision captured for one MarkMode gesture.
		template_names: Immutable OASA-owned system-template selection names for
			TemplateMode.  The session supplies them as plain data.
		template_action: Session-owned callback accepting one system-template name
			and finite anchor for backend-authoritative placement.
		biomolecule_catalog: Immutable OASA-owned biomolecule descriptors for
			BioTemplateMode.  The session supplies them as plain data.
		biotemplate_action: Session-owned callback accepting one catalog key and
			finite anchor for backend-authoritative biomolecule placement.
		user_template_catalog: Immutable plain user-template descriptors for
			UserTemplateMode. The session supplies them without filesystem state.
		user_template_action: Session-owned callback accepting one opaque user
			template catalog key and finite anchor for detached placement.
		graphics_retirement_reaper: Frontend-only session owner for failed terminal
			preview retirement.

	Returns:
		Configured ModeManager instance.
	"""
	mode_manager = bkchem_qt.modes.mode_manager.ModeManager(
		view, parent=parent if parent is not None else main_window,
	)
	# register file actions mode (before edit/draw in toolbar order)
	mode_manager.register_mode(
		"file_actions",
		bkchem_qt.modes.file_actions_mode.FileActionsMode(
			view, main_window=main_window
		),
	)
	# register additional modes beyond the default edit/draw
	mode_manager.register_mode(
		"template",
		bkchem_qt.modes.template_mode.TemplateMode(view, template_names=template_names),
	)
	mode_manager.register_mode(
		"biotemplate",
		bkchem_qt.modes.biotemplate_mode.BioTemplateMode(
			view, catalog=biomolecule_catalog,
		),
	)
	mode_manager.register_mode(
		"usertemplate",
		bkchem_qt.modes.user_template_mode.UserTemplateMode(
			view, catalog=user_template_catalog if user_template_catalog is not None else (),
		),
	)
	mode_manager.register_mode(
		"arrow",
		bkchem_qt.modes.arrow_mode.ArrowMode(view),
	)
	mode_manager.register_mode(
		"text",
		bkchem_qt.modes.text_mode.TextMode(view),
	)
	mode_manager.register_mode(
		"rotate",
		bkchem_qt.modes.rotate_mode.RotateMode(view),
	)
	mode_manager.register_mode(
		"mark",
		bkchem_qt.modes.mark_mode.MarkMode(view),
	)
	mode_manager.register_mode(
		"atom",
		bkchem_qt.modes.atom_mode.AtomMode(view),
	)
	mode_manager.register_mode(
		"bondalign",
		bkchem_qt.modes.bondalign_mode.BondAlignMode(view),
	)
	mode_manager.register_mode(
		"bracket",
		bkchem_qt.modes.bracket_mode.BracketMode(view),
	)
	mode_manager.register_mode(
		"vector",
		bkchem_qt.modes.vector_mode.VectorMode(view),
	)
	mode_manager.register_mode(
		"repair",
		bkchem_qt.modes.repair_mode.RepairMode(view),
	)
	mode_manager.register_mode(
		"plus",
		bkchem_qt.modes.plus_mode.PlusMode(view),
	)
	mode_manager.register_mode(
		"misc",
		bkchem_qt.modes.misc_mode.MiscMode(view),
	)
	# connect the mode manager to the view for event dispatch
	view.set_mode_manager(mode_manager)
	# Modes are QObjects but ModeManager historically registered them without
	# assigning a QObject parent.  Make the manager's lifetime authoritative.
	for mode in mode_manager._modes.values():
		mode.setParent(mode_manager)
	# Each new manager discovers the frozen persistent-operation interface only
	# after every mode exists.  No existing manager is retrofitted later.
	for mode in mode_manager._modes.values():
		installer = getattr(mode, "set_persistent_operation", None)
		if callable(installer):
			installer(persistent_action)
		align_installer = getattr(mode, "set_atom_align_operation", None)
		if callable(align_installer):
			align_installer(atom_align_action)
		translate_installer = getattr(mode, "set_atom_translate_operation", None)
		if callable(translate_installer):
			translate_installer(atom_translate_action)
		rotate_installer = getattr(mode, "set_atom_rotate_operation", None)
		if callable(rotate_installer):
			rotate_installer(atom_rotate_action)
		translate_authority_installer = getattr(mode, "set_atom_translate_authority", None)
		if callable(translate_authority_installer):
			translate_authority_installer(atom_translate_authority)
		presentation_translate_installer = getattr(mode, "set_presentation_translate_operation", None)
		if callable(presentation_translate_installer):
			presentation_translate_installer(presentation_translate_action)
		presentation_context_installer = getattr(mode, "set_presentation_translate_context", None)
		if callable(presentation_context_installer):
			presentation_context_installer(presentation_translate_context)
		selection_translate_installer = getattr(mode, "set_selection_translate_operation", None)
		if callable(selection_translate_installer):
			selection_translate_installer(selection_translate_action)
		selection_context_installer = getattr(mode, "set_selection_translate_context", None)
		if callable(selection_context_installer):
			selection_context_installer(selection_translate_context)
		delete_context_installer = getattr(mode, "set_top_level_delete_context", None)
		if callable(delete_context_installer):
			delete_context_installer(top_level_delete_context)
		structure_delete_installer = getattr(mode, "set_structure_delete_context", None)
		if callable(structure_delete_installer):
			structure_delete_installer(structure_delete_context)
		atom_mark_delete_installer = getattr(mode, "set_atom_mark_delete_context", None)
		if callable(atom_mark_delete_installer):
			atom_mark_delete_installer(atom_mark_delete_context)
		candidate_installer = getattr(mode, "set_atom_number_context", None)
		if callable(candidate_installer):
			candidate_installer(atom_number_context)
		mark_revision_installer = getattr(mode, "set_atom_mark_revision", None)
		if callable(mark_revision_installer):
			mark_revision_installer(atom_mark_revision)
		template_installer = getattr(mode, "set_template_action", None)
		if callable(template_installer):
			template_installer(template_action)
		biotemplate_installer = getattr(mode, "set_biotemplate_action", None)
		if callable(biotemplate_installer):
			biotemplate_installer(biotemplate_action)
		user_template_installer = getattr(mode, "set_user_template_action", None)
		if callable(user_template_installer):
			user_template_installer(user_template_action)
		retirement_installer = getattr(mode, "set_graphics_retirement_reaper", None)
		if callable(retirement_installer):
			retirement_installer(graphics_retirement_reaper)
	# inject YAML submode data into each registered mode
	_inject_submodes_from_yaml(mode_manager)
	return mode_manager


#============================================
def _inject_submodes_from_yaml(mode_manager: object) -> None:
	"""Parse modes.yaml and inject submode data into registered modes.

	For each registered mode, looks up its definition in modes.yaml
	and parses the submodes section. The parsed data is set on the
	mode object's attributes so the SubModeRibbon can render them.

	Args:
		mode_manager: The ModeManager with registered modes.
	"""
	if not _MODES_YAML_PATH.is_file():
		return
	with open(_MODES_YAML_PATH, "r") as fh:
		modes_config = yaml.safe_load(fh) or {}
	modes_defs = modes_config.get("modes", {})

	for mode_name in mode_manager.mode_names():
		mode = mode_manager._modes[mode_name]
		# find the YAML definition for this mode
		cfg = modes_defs.get(mode_name, {})
		if not cfg:
			continue

		# set show_edit_pool from YAML
		mode.show_edit_pool = cfg.get('show_edit_pool', False)

		# dynamic modes populate their own submodes at init time;
		# skip YAML injection if the mode already has submode data
		if cfg.get('dynamic') and mode.submodes:
			continue

		# parse submode groups from YAML
		parsed = bkchem_qt.modes.config.load_submodes_from_yaml(cfg)
		(submodes, submodes_names, submode_defaults,
			icon_map, group_labels, group_layouts,
			tooltip_map, size_map) = parsed

		mode.submodes = submodes
		mode.submodes_names = submodes_names
		# initialize current submode indices from defaults
		mode.submode = list(submode_defaults)
		mode.icon_map = icon_map
		mode.group_labels = group_labels
		mode.group_layouts = group_layouts
		mode.tooltip_map = tooltip_map
		mode.size_map = size_map


#============================================
def get_modes_yaml_path() -> pathlib.Path:
	"""Return the resolved path to modes.yaml.

	Returns:
		Path to the modes.yaml configuration file.
	"""
	return _MODES_YAML_PATH
