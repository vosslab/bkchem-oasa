"""Menu builder that combines YAML structure with action registry.

Reads the menu hierarchy from a YAML file, looks up action details
from the ActionRegistry, and calls the PlatformMenuAdapter to
construct the actual native Qt menus.
"""

# Standard Library
import builtins
import pathlib

# PIP3 modules
import yaml

# gettext i18n translation fallback
_ = builtins.__dict__.get('_', lambda m: m)


#============================================
class MenuActionPreflightError(RuntimeError):
	"""Report required YAML actions missing from a populated registry."""


#============================================
def required_menu_action_ids(yaml_path: str) -> tuple[str, ...]:
	"""Return sorted required action IDs declared by a menu YAML document.

	Args:
		yaml_path: Path to the menu YAML document.

	Returns:
		Sorted unique action IDs whose YAML items are not explicitly optional.
	"""
	structure = yaml.safe_load(pathlib.Path(yaml_path).read_text(encoding="utf-8"))
	required_ids = set()

	def visit(value: object) -> None:
		if isinstance(value, dict):
			action_id = value.get("action")
			if isinstance(action_id, str) and not value.get("optional", False):
				required_ids.add(action_id)
			for nested_value in value.values():
				visit(nested_value)
		elif isinstance(value, list):
			for nested_value in value:
				visit(nested_value)

	visit(structure)
	return tuple(sorted(required_ids))


#============================================
def preflight_required_menu_actions(registry: object, yaml_path: str) -> None:
	"""Require every non-optional YAML action before native menus are built.

	Args:
		registry: Populated action registry.
		yaml_path: Path to the menu YAML document.

	Raises:
		MenuActionPreflightError: If one or more required actions are absent.
	"""
	missing_ids = tuple(
		action_id for action_id in required_menu_action_ids(yaml_path)
		if action_id not in registry
	)
	if missing_ids:
		raise MenuActionPreflightError(
			"Required menu actions are unregistered: %s"
			% ", ".join(missing_ids)
		)


#============================================
class MenuBuilder:
	"""Builds menus from YAML structure and action registry."""

	#============================================
	def __init__(self, yaml_path: str, registry: object, adapter: object) -> None:
		"""Initialize the menu builder.

		Args:
			yaml_path: Path to the menus.yaml file.
			registry: ActionRegistry instance containing all menu actions.
			adapter: PlatformMenuAdapter instance for constructing menus.
		"""
		self._registry = registry
		self._adapter = adapter
		with open(yaml_path, encoding="utf-8") as file_handle:
			self._structure = yaml.safe_load(file_handle)
		self._menu_actions = {}
		self._cascade_names = set()

	#============================================
	def build_menus(self) -> None:
		"""Build all top-level menus and their items from the YAML structure."""
		cascades = self._structure.get('cascades', {})
		for menu_def in self._structure['menus']:
			menu_name = _(menu_def['label_key'])
			help_text = _(menu_def['help_key'])
			side = menu_def.get('side', 'left')
			self._adapter.add_menu(menu_name, help_text, side=side)
			self._menu_actions[menu_name] = []
			for item in menu_def.get('items', []):
				self._build_item(item, menu_name, cascades)

	#============================================
	def _build_item(
			self, item: dict, menu_name: str, cascades: dict,
			) -> None:
		"""Dispatch a single menu item to the appropriate builder.

		Args:
			item: Dict describing the menu item from YAML.
			menu_name: Parent menu label.
			cascades: Dict of cascade definitions from YAML.
		"""
		if 'action' in item:
			self._build_action_item(item, menu_name)
		elif 'separator' in item:
			self._adapter.add_separator(menu_name)
		elif 'cascade' in item:
			self._build_cascade_item(item, menu_name, cascades)

	#============================================
	def _build_action_item(self, item: dict, menu_name: str) -> None:
		"""Build a single action item and add it to the menu.

		Args:
			item: Dict with 'action' key referencing the registry ID.
			menu_name: Parent menu label.
		"""
		action_id = item['action']
		if action_id not in self._registry:
			if item.get('optional', False):
				return
			message = (
				f"Menu '{menu_name}' requires unregistered action "
				f"'{action_id}'. Mark the YAML item optional only when its "
				"absence is intentional."
			)
			raise KeyError(message)
		action = self._registry.get(action_id)
		self._adapter.add_command(
			menu_name, action.label, action.accelerator,
			action.help_text, action.handler,
			action_key=action_id,
		)
		self._menu_actions[menu_name].append(action)

	#============================================
	def _build_cascade_item(
			self, item: dict, menu_name: str, cascades: dict,
			) -> None:
		"""Build a cascade (submenu) item and add it to the menu.

		Args:
			item: Dict with 'cascade' key referencing cascade definitions.
			menu_name: Parent menu label.
			cascades: Dict of cascade definitions from YAML.
		"""
		cascade_key = item['cascade']
		cascade_def = cascades.get(cascade_key, {})
		cascade_label = _(cascade_def.get('label_key', cascade_key))
		cascade_help = _(cascade_def.get('help_key', ''))
		self._adapter.add_cascade(menu_name, cascade_label, cascade_help)
		self._cascade_names.add(cascade_label)

	#============================================
	def update_menu_states(self, app: object) -> None:
		"""Update enabled/disabled state of all actions.

		Args:
			app: Application object whose paper attribute may be queried.
		"""
		for menu_name, actions in self._menu_actions.items():
			for action in actions:
				predicate = action.enabled_when
				if predicate is None:
					continue
				if callable(predicate):
					enabled = bool(predicate())
				else:
					enabled = bool(getattr(app.paper, predicate, False))
				self._adapter.set_item_state_by_key(action.id, enabled)

	#============================================
	def get_plugin_slots(self) -> dict:
		"""Return a dict mapping slot names to cascade labels.

		Returns:
			Dict with keys like 'exporters' and 'importers'.
		"""
		slots = {}
		for cascade_label in self._cascade_names:
			lower = cascade_label.lower()
			if 'export' in lower:
				slots['exporters'] = cascade_label
			elif 'import' in lower:
				slots['importers'] = cascade_label
		return slots

	#============================================
	def add_to_plugin_slot(
			self, slot_name: str, label: str, help_text: str, command: object,
			) -> None:
		"""Add a command to a named plugin slot cascade.

		Args:
			slot_name: Slot name like 'exporters' or 'importers'.
			label: Command label text.
			help_text: Status help text.
			command: Callable to invoke when triggered.
		"""
		slots = self.get_plugin_slots()
		cascade_label = slots.get(slot_name)
		if cascade_label is None:
			return
		self._adapter.add_command_to_cascade(
			cascade_label, label, help_text, command,
		)
