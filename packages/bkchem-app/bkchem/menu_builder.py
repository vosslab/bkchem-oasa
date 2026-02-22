"""Menu builder that combines YAML structure with action registry.

Reads the menu hierarchy from a YAML file, looks up action details
from the ActionRegistry, and calls the PlatformMenuAdapter to
construct the actual native tkinter menus.
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
			yaml_path: path to menus.yaml
			registry: ActionRegistry instance
			adapter: PlatformMenuAdapter instance
		"""
		self._registry = registry
		self._adapter = adapter
		# load the YAML menu structure from disk
		with open(yaml_path) as f:
			self._structure = yaml.safe_load(f)
		# track menu-name to list of actions for state updates
		self._menu_actions = {}
		# track cascade labels for plugin slot injection
		self._cascade_names = set()

	#============================================
	def build_menus(self) -> None:
		"""Build all menus from the YAML structure.

		Iterates over the top-level menus defined in the YAML,
		creates each menu via the adapter, then populates items
		(actions, separators, cascades) in order.
		"""
		cascades = self._structure.get('cascades', {})
		for menu_def in self._structure['menus']:
			# translate label and help text
			menu_name = _(menu_def['label_key'])
			help_text = _(menu_def['help_key'])
			side = menu_def.get('side', 'left')
			# create the top-level menu bar entry
			self._adapter.add_menu(menu_name, help_text, side=side)
			self._menu_actions[menu_name] = []
			# populate menu items in order
			for item in menu_def.get('items', []):
				self._build_item(
					item, menu_name, cascades,
				)

	#============================================
	def _build_item(self, item: dict, menu_name: str,
					cascades: dict) -> None:
		"""Build a single menu item (action, separator, or cascade).

		Args:
			item: item dict from the YAML items list
			menu_name: translated name of the parent menu
			cascades: dict of cascade definitions from YAML
		"""
		if 'action' in item:
			self._build_action_item(item, menu_name)
		elif 'separator' in item:
			self._adapter.add_separator(menu_name)
		elif 'cascade' in item:
			self._build_cascade_item(item, menu_name, cascades)

	#============================================
	def _build_action_item(self, item: dict, menu_name: str) -> None:
		"""Build an action menu item.

		Args:
			item: item dict containing 'action' key
			menu_name: translated name of the parent menu
		"""
		action_id = item['action']
		# skip actions not yet registered (e.g. from plugins)
		if action_id not in self._registry:
			return
		action = self._registry.get(action_id)
		self._adapter.add_command(
			menu_name,
			action.label,
			action.accelerator,
			action.help_text,
			action.handler,
		)
		# track for state updates later
		self._menu_actions[menu_name].append(action)

	#============================================
	def _build_cascade_item(self, item: dict, menu_name: str,
							cascades: dict) -> None:
		"""Build a cascade (submenu) menu item.

		Args:
			item: item dict containing 'cascade' key
			menu_name: translated name of the parent menu
			cascades: dict of cascade definitions from YAML
		"""
		cascade_key = item['cascade']
		cascade_def = cascades.get(cascade_key, {})
		cascade_label = _(cascade_def.get('label_key', cascade_key))
		cascade_help = _(cascade_def.get('help_key', ''))
		self._adapter.add_cascade(
			menu_name, cascade_label, cascade_help,
		)
		# remember cascade label for plugin slot lookup
		self._cascade_names.add(cascade_label)

	#============================================
	def update_menu_states(self, app: object) -> None:
		"""Update enable/disable state for all menu items.

		Evaluates each action's enabled_when predicate and calls
		set_item_state on the adapter accordingly.

		Args:
			app: the application object (used as context for
				string-based enabled_when predicates)
		"""
		for menu_name, actions in self._menu_actions.items():
			for action in actions:
				predicate = action.enabled_when
				# skip items with no predicate (always enabled)
				if predicate is None:
					continue
				# evaluate the predicate
				if callable(predicate):
					enabled = bool(predicate())
				else:
					# string: look up attribute on app.paper
					enabled = bool(
						getattr(app.paper, predicate, False)
					)
				self._adapter.set_item_state(
					menu_name, action.label, enabled,
				)

	#============================================
	def get_plugin_slots(self) -> dict:
		"""Return plugin injection slot names.

		Scans cascade labels for export/import keywords and maps
		them to standard slot names.

		Returns:
			dict mapping slot names to cascade labels
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
	def add_to_plugin_slot(self, slot_name: str, label: str,
			help_text: str, command: object) -> None:
		"""Add an entry to a plugin slot cascade.

		Args:
			slot_name: 'importers' or 'exporters'
			label: menu item label
			help_text: status help text
			command: callable handler
		"""
		slots = self.get_plugin_slots()
		cascade_label = slots.get(slot_name)
		if cascade_label is None:
			return
		self._adapter.add_command_to_cascade(
			cascade_label, label, help_text, command,
		)
