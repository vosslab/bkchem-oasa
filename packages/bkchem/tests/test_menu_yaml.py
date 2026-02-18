#!/usr/bin/env python3
"""Tests for YAML menu structure."""

# Standard Library
import os
import re

# PIP3 modules
import yaml
import pytest

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
def test_all_ten_menus_present():
	"""Verify 10 menus with expected names."""
	data = _load_yaml()
	expected_names = {
		'file', 'edit', 'insert', 'align', 'object',
		'view', 'chemistry', 'options', 'help', 'plugins',
	}
	menu_names = {m['name'] for m in data['menus']}
	assert menu_names == expected_names
	assert len(data['menus']) == 10

#============================================
def test_menu_order():
	"""Names in correct order."""
	data = _load_yaml()
	expected_order = [
		'file', 'edit', 'insert', 'align', 'object',
		'view', 'chemistry', 'options', 'help', 'plugins',
	]
	actual_order = [m['name'] for m in data['menus']]
	assert actual_order == expected_order

#============================================
def test_help_and_plugins_right_side():
	"""Help and plugins have side=right, others left."""
	data = _load_yaml()
	for menu in data['menus']:
		if menu['name'] in ('help', 'plugins'):
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
def test_total_action_count():
	"""Total action items across all menus equals 55."""
	data = _load_yaml()
	all_items = _collect_all_items(data)
	action_count = sum(1 for item in all_items if 'action' in item)
	assert action_count == 55, f"Expected 55 actions, got {action_count}"

#============================================
def test_total_separator_count():
	"""Total separators equals 19."""
	data = _load_yaml()
	all_items = _collect_all_items(data)
	sep_count = sum(1 for item in all_items if 'separator' in item)
	assert sep_count == 19, f"Expected 19 separators, got {sep_count}"

#============================================
def test_cascade_count():
	"""Total cascade refs equals 3."""
	data = _load_yaml()
	all_items = _collect_all_items(data)
	cascade_count = sum(1 for item in all_items if 'cascade' in item)
	assert cascade_count == 3, f"Expected 3 cascades, got {cascade_count}"

#============================================
def test_file_menu_item_count():
	"""File menu has 16 items (9 actions + 3 cascades + 4 separators)."""
	data = _load_yaml()
	# find file menu
	file_menu = [m for m in data['menus'] if m['name'] == 'file'][0]
	item_count = len(file_menu['items'])
	assert item_count == 16, f"Expected 16 file items, got {item_count}"

#============================================
def test_chemistry_menu_item_count():
	"""Chemistry menu has 20 items (14 actions + 6 separators)."""
	data = _load_yaml()
	# find chemistry menu
	chem_menu = [m for m in data['menus'] if m['name'] == 'chemistry'][0]
	item_count = len(chem_menu['items'])
	assert item_count == 20, f"Expected 20 chemistry items, got {item_count}"
