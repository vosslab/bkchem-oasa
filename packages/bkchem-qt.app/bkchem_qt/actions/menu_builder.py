"""Menu builder that combines YAML structure with action registry.

Reads the menu hierarchy from a YAML file, looks up action details
from the ActionRegistry, and calls the PlatformMenuAdapter to
construct the actual native Qt menus.
"""

# Standard Library
import builtins

# PIP3 modules
import yaml

# gettext i18n translation fallback
_ = builtins.__dict__.get('_', lambda m: m)


#============================================
class MenuBuilder:
	"""Builds menus from YAML structure and action registry."""

	#============================================
	def __init__(self, yaml_path: str, registry: object, adapter: object):
		"""Initialize the menu builder.

		Args:
			yaml_path: Path to the menus.yaml file.
			registry: ActionRegistry instance containing all menu actions.
			adapter: PlatformMenuAdapter instance for constructing menus.
		"""
		self._registry = registry
		self._adapter = adapter
		with open(yaml_path) as f:
			self._structure = yaml.safe_load(f)
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
	def _build_item(self, item, menu_name, cascades):
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
	def _build_action_item(self, item, menu_name):
		"""Build a single action item and add it to the menu.

		Args:
			item: Dict with 'action' key referencing the registry ID.
			menu_name: Parent menu label.
		"""
		action_id = item['action']
		if action_id not in self._registry:
			return
		action = self._registry.get(action_id)
		self._adapter.add_command(
			menu_name, action.label, action.accelerator,
			action.help_text, action.handler,
		)
		self._menu_actions[menu_name].append(action)

	#============================================
	def _build_cascade_item(self, item, menu_name, cascades):
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
	def update_menu_states(self, app):
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
				self._adapter.set_item_state(menu_name, action.label, enabled)

	#============================================
	def get_plugin_slots(self):
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
	def add_to_plugin_slot(self, slot_name, label, help_text, command):
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
