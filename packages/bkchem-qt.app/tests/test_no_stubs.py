"""Anti-stub test: verify no registered action handler is a placeholder stub.

Iterates all registered menu actions and asserts that none of them
produce a 'not yet implemented' status bar message.
"""

# Standard Library
import re
import types
import inspect


# source code patterns that indicate a stub handler
_STUB_PATTERNS = [
	re.compile(r"not\s+yet\s+implemented", re.IGNORECASE),
	re.compile(r"stub", re.IGNORECASE),
	re.compile(r"TODO", re.IGNORECASE),
]


#============================================
def _handler_source_contains_stub(handler: object) -> str:
	"""Check if a handler's source code contains stub indicators.

	Inspects the handler's source code and bytecode constants for
	stub-like strings.

	Args:
		handler: Callable to inspect.

	Returns:
		The matching stub string if found, empty string otherwise.
	"""
	# try to get source code
	try:
		source = inspect.getsource(handler)
		for pattern in _STUB_PATTERNS:
			match = pattern.search(source)
			if match:
				return match.group()
	except (TypeError, OSError):
		pass
	# inspect bytecode constants for lambda wrappers
	func = handler
	if hasattr(func, "__func__"):
		func = func.__func__
	if hasattr(func, "__wrapped__"):
		func = func.__wrapped__
	if isinstance(func, types.FunctionType):
		code = func.__code__
		for const in code.co_consts:
			if isinstance(const, str):
				for pattern in _STUB_PATTERNS:
					match = pattern.search(const)
					if match:
						return match.group()
			# check nested code objects (closures, lambdas)
			if isinstance(const, types.CodeType):
				for inner_const in const.co_consts:
					if isinstance(inner_const, str):
						for pattern in _STUB_PATTERNS:
							match = pattern.search(inner_const)
							if match:
								return match.group()
	return ""


#============================================
def test_no_stub_handlers(main_window: object) -> None:
	"""Every registered action handler must be a real implementation.

	Fails if any handler source or bytecode contains 'not yet implemented',
	'stub', or 'TODO' strings.
	"""
	registry = main_window._registry
	actions = registry.all_actions()
	assert len(actions) > 0, "registry should have registered actions"
	stub_actions = []
	for action_id, action in sorted(actions.items()):
		handler = action.handler
		if handler is None:
			# None handlers are cascade items (submenus), not stubs
			continue
		stub_match = _handler_source_contains_stub(handler)
		if stub_match:
			stub_actions.append(f"{action_id}: matched '{stub_match}'")
	msg = "Found stub handlers:\n" + "\n".join(stub_actions)
	assert len(stub_actions) == 0, msg


#============================================
def test_all_handlers_are_callable(main_window: object) -> None:
	"""Every registered action must have a callable handler or None."""
	registry = main_window._registry
	actions = registry.all_actions()
	for action_id, action in sorted(actions.items()):
		handler = action.handler
		if handler is not None:
			assert callable(handler), (
				f"Action '{action_id}' handler is not callable: {type(handler)}"
			)


#============================================
def test_minimum_action_count(main_window: object) -> None:
	"""Registry should have at least 48 actions (all stubs replaced)."""
	registry = main_window._registry
	actions = registry.all_actions()
	# the original plan counted 63 total registered actions, 48 were stubs
	assert len(actions) >= 48, (
		f"Expected at least 48 registered actions, got {len(actions)}"
	)


#============================================
def test_action_categories_present(main_window: object) -> None:
	"""All expected menu categories should have actions registered."""
	registry = main_window._registry
	actions = registry.all_actions()
	# extract category prefixes from action IDs
	categories = set()
	for action_id in actions:
		prefix = action_id.split(".")[0]
		categories.add(prefix)
	expected_categories = {
		"file", "edit", "align", "object",
		"chemistry", "repair", "options", "help",
	}
	missing = expected_categories - categories
	assert not missing, f"Missing action categories: {missing}"
