"""Tests for YAML menu structure."""

# Standard Library
import os
import re

# PIP3 modules
import yaml

# path to the YAML file
YAML_PATH = os.path.join(
	os.path.dirname(__file__), '..', 'bkchem_data', 'menus.yaml'
)

#============================================
def _load_yaml() -> dict:
	"""Load and parse the menu YAML file.

	Returns:
		dict: parsed YAML data with menus and cascades sections.
	"""
	with open(YAML_PATH) as f:
		return yaml.safe_load(f)

#============================================
def _collect_all_items(data: dict) -> list:
	"""Collect all item dicts from all menus.

	Args:
		data: parsed YAML data.

	Returns:
		list: flat list of all item dicts across all menus.
	"""
	items = []
	for menu in data['menus']:
		items.extend(menu.get('items', []))
	return items

#============================================
def test_yaml_parses():
	"""File loads without error."""
	data = _load_yaml()
	assert isinstance(data, dict)
	assert 'menus' in data

#============================================
def test_every_menu_has_name_and_side():
	"""Every menu entry has a name and side key."""
	data = _load_yaml()
	for menu in data['menus']:
		assert 'name' in menu, f"Menu missing 'name': {menu}"
		assert 'side' in menu, f"Menu missing 'side': {menu}"

#============================================
def test_every_menu_has_items():
	"""Every menu has a non-empty items list."""
	data = _load_yaml()
	for menu in data['menus']:
		items = menu.get('items', [])
		assert len(items) > 0, f"Menu '{menu['name']}' has no items"

#============================================
def test_help_right_side():
	"""Help has side=right, others left."""
	data = _load_yaml()
	for menu in data['menus']:
		if menu['name'] == 'help':
			assert menu['side'] == 'right', f"{menu['name']} should be right"
		else:
			assert menu['side'] == 'left', f"{menu['name']} should be left"

#============================================
def test_item_types_valid():
	"""Every item is one of: action, separator, cascade."""
	data = _load_yaml()
	all_items = _collect_all_items(data)
	for item in all_items:
		item_keys = set(item.keys())
		# each item should have exactly one type key
		valid_keys = {'action', 'separator', 'cascade'}
		assert len(item_keys & valid_keys) == 1, f"Invalid item: {item}"

#============================================
def test_action_ids_well_formed():
	"""All action IDs match pattern word.word_word etc."""
	data = _load_yaml()
	# pattern: word dot word (with optional underscores)
	pattern = re.compile(r'^[a-z]+\.[a-z][a-z0-9_]*$')
	all_items = _collect_all_items(data)
	for item in all_items:
		if 'action' in item:
			action_id = item['action']
			assert pattern.match(action_id), f"Bad action ID: {action_id}"

#============================================
def test_no_duplicate_action_ids():
	"""No action ID appears twice across all menus."""
	data = _load_yaml()
	all_items = _collect_all_items(data)
	action_ids = [item['action'] for item in all_items if 'action' in item]
	assert len(action_ids) == len(set(action_ids)), (
		f"Duplicate action IDs found: "
		f"{[a for a in action_ids if action_ids.count(a) > 1]}"
	)

#============================================
def test_cascade_refs_have_definitions():
	"""Every cascade name referenced in items exists in cascades section."""
	data = _load_yaml()
	all_items = _collect_all_items(data)
	cascade_refs = {item['cascade'] for item in all_items if 'cascade' in item}
	cascade_defs = set(data.get('cascades', {}).keys())
	missing = cascade_refs - cascade_defs
	assert not missing, f"Missing cascade definitions: {missing}"

#============================================
def test_no_adjacent_separators():
	"""No menu has two separators in a row."""
	data = _load_yaml()
	for menu in data['menus']:
		items = menu.get('items', [])
		for i in range(len(items) - 1):
			if 'separator' in items[i] and 'separator' in items[i + 1]:
				assert False, f"Adjacent separators in '{menu['name']}' at index {i}"

#============================================
def test_no_leading_or_trailing_separators():
	"""No menu starts or ends with a separator."""
	data = _load_yaml()
	for menu in data['menus']:
		items = menu.get('items', [])
		if items:
			assert 'separator' not in items[0], (
				f"Menu '{menu['name']}' starts with a separator"
			)
			assert 'separator' not in items[-1], (
				f"Menu '{menu['name']}' ends with a separator"
			)
