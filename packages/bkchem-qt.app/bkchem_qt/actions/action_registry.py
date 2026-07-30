"""Action registry for BKChem-Qt menu system.

Provides the MenuAction dataclass and ActionRegistry class that form
the shared contract for the modular menu refactor.
"""

# Standard Library
import builtins
import importlib
import dataclasses

# local repo modules
from bkchem_qt.actions.registrar_manifest import (
	ACTION_REGISTRAR_MODULES,
	registrar_name,
)

# gettext i18n translation fallback
_ = builtins.__dict__.get('_', lambda m: m)


#============================================
@dataclasses.dataclass
class MenuAction:
	"""A single menu action entry.

	Attributes:
		id: Unique action identifier, e.g. "file.save", "edit.undo".
		label_key: English label key, translated via _() at access time.
		help_key: English help text key, translated via _() at access time.
		accelerator: Keyboard shortcut string, e.g. "(C-x C-s)", or None.
		handler: Callable invoked when the action fires, or None for cascades.
		enabled_when: Callable, string attribute name, or None (always enabled).
	"""
	id: str
	label_key: str
	help_key: str
	accelerator: str
	handler: object
	enabled_when: object

	@property
	def label(self) -> str:
		"""Return the translated label string."""
		return _(self.label_key)

	@property
	def help_text(self) -> str:
		"""Return the translated help text string."""
		return _(self.help_key)


#============================================
class ActionRegistrationError(RuntimeError):
	"""Report an action module that could not take part in startup."""


#============================================
class ActionRegistry:
	"""Registry of all menu actions, keyed by action ID."""

	def __init__(self) -> None:
		"""Initialize an empty action registry."""
		self._actions: dict = {}

	def register(self, action: MenuAction) -> None:
		"""Register a MenuAction. Raises ValueError on duplicate IDs.

		Args:
			action: The MenuAction to register.

		Raises:
			ValueError: If action.id is already registered.
		"""
		if action.id in self._actions:
			raise ValueError(f"Duplicate action ID: '{action.id}'")
		self._actions[action.id] = action

	def get(self, action_id: str) -> MenuAction:
		"""Look up an action by its ID.

		Args:
			action_id: The unique action identifier.

		Returns:
			The MenuAction with the given ID.

		Raises:
			KeyError: If the action_id is not registered.
		"""
		return self._actions[action_id]

	def __contains__(self, action_id: str) -> bool:
		"""Check whether an action ID is registered.

		Args:
			action_id: The unique action identifier.

		Returns:
			True if the action_id is registered, False otherwise.
		"""
		return action_id in self._actions

	def all_actions(self) -> dict:
		"""Return a shallow copy of all registered actions.

		Returns:
			A dict mapping action IDs to MenuAction instances.
		"""
		return dict(self._actions)

	def is_enabled(self, action_id: str, context: object) -> bool:
		"""Determine whether an action is currently enabled.

		Args:
			action_id: The unique action identifier.
			context: Object whose attributes may be checked for string predicates.

		Returns:
			True if the action is enabled, False otherwise.
		"""
		action = self._actions[action_id]
		predicate = action.enabled_when
		# None means always enabled
		if predicate is None:
			return True
		# callable predicate: invoke it
		if callable(predicate):
			return bool(predicate())
		# string predicate: look up attribute on context
		return bool(getattr(context, predicate, False))


#============================================
def register_all_actions(app: object) -> ActionRegistry:
	"""Register all menu actions from per-menu modules.

	Imports each immutable-manifest registration module and calls its registrar.
	The manifest remains available in both source and frozen application layouts.
	Every import and registrar failure names its responsible module, preventing a
	partially populated menu from looking like a successful application start.

	Args:
		app: The application object passed to each registrar.

	Returns:
		A populated ActionRegistry instance.
	"""
	registry = ActionRegistry()
	for qualified_name in ACTION_REGISTRAR_MODULES:
		func_name = registrar_name(qualified_name)
		try:
			mod = importlib.import_module(qualified_name)
		except Exception as exc:
			message = f"Could not import action module '{qualified_name}': {exc}"
			raise ActionRegistrationError(message) from exc
		registrar = getattr(mod, func_name, None)
		if not callable(registrar):
			message = (
				f"Action module '{qualified_name}' does not define callable "
				f"registrar '{func_name}'."
			)
			raise ActionRegistrationError(message)
		try:
			registrar(registry, app)
		except Exception as exc:
			message = (
				f"Could not register actions from module '{qualified_name}' "
				f"through '{func_name}': {exc}"
			)
			raise ActionRegistrationError(message) from exc
	return registry
