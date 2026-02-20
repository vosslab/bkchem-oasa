#--------------------------------------------------------------------------
#     This file is part of BKChem - a chemical drawing program
#     Copyright (C) 2002-2009 Beda Kosata <beda@zirael.org>

#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 2 of the License, or
#     (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

#     Complete text of GNU GPL can be found in the file gpl.txt in the
#     main directory of the program

#--------------------------------------------------------------------------

"""YAML config loaders for modes and edit pool."""

import os
import builtins

import yaml

from bkchem import os_support

# gettext i18n translation fallback
_ = builtins.__dict__.get( '_', lambda m: m)


# module-level YAML config caches, loaded lazily on first use
_MODES_CONFIG = None
_EDIT_POOL_CONFIG = None


#============================================
def _load_modes_yaml() -> dict:
	"""Load modes.yaml from the bkchem_data directory."""
	data_dir = os_support._get_bkchem_data_dir()
	yaml_path = os.path.join(data_dir, 'modes.yaml')
	with open(yaml_path, 'r') as fh:
		return yaml.safe_load(fh)


#============================================
def get_modes_config() -> dict:
	"""Return the cached modes YAML config, loading on first call."""
	global _MODES_CONFIG
	if _MODES_CONFIG is None:
		_MODES_CONFIG = _load_modes_yaml()
	return _MODES_CONFIG


#============================================
def get_toolbar_order() -> list:
	"""Return the toolbar mode ordering from YAML."""
	return list(get_modes_config()['toolbar_order'])


#============================================
def _load_edit_pool_from_yaml() -> list:
	"""Parse edit_pool_buttons from the YAML config.

	Returns:
		list of BkGroup dicts, each with keys:
			group_label (str), options (list of dicts with
			key, icon, name, tooltip, command)
	"""
	cfg = get_modes_config()
	raw_groups = cfg.get('edit_pool_buttons', [])
	result = []
	for grp in raw_groups:
		parsed_group = {
			'group_label': _(grp.get('group_label', '')),
			'options': [],
		}
		for opt in grp.get('options', []):
			parsed_group['options'].append({
				'key': opt['key'],
				'icon': opt.get('icon', opt['key']),
				'name': _(opt.get('name', opt['key'])),
				'tooltip': _(opt.get('tooltip', opt.get('name', opt['key']))),
				'command': opt.get('command', opt['key']),
			})
		result.append(parsed_group)
	return result


#============================================
def get_edit_pool_config() -> list:
	"""Return cached edit pool button config from YAML."""
	global _EDIT_POOL_CONFIG
	if _EDIT_POOL_CONFIG is None:
		_EDIT_POOL_CONFIG = _load_edit_pool_from_yaml()
	return _EDIT_POOL_CONFIG


#============================================
def _load_submodes_from_yaml(cfg: dict) -> tuple:
	"""Parse submode groups from a mode's YAML config.

	Args:
		cfg: mode config dict from YAML

	Returns:
		tuple of (submodes, submodes_names, submode_defaults,
				  icon_map, group_labels, group_layouts, tooltip_map, size_map)
	"""
	submodes = []
	submodes_names = []
	submode_defaults = []
	icon_map = {}
	group_labels = []
	group_layouts = []
	tooltip_map = {}
	size_map = {}
	for grp in cfg.get('submodes', []):
		# skip dynamic groups that have no options (filled at runtime)
		if 'options' not in grp:
			continue
		keys = [opt['key'] for opt in grp['options']]
		# default cascade: name defaults to key, icon defaults to key
		names = [_(opt.get('name', opt['key'])) for opt in grp['options']]
		submodes.append(keys)
		submodes_names.append(names)
		submode_defaults.append(grp.get('default', 0))
		# group label for ribbon-style display (i18n)
		label = grp.get('group_label', '')
		group_labels.append(_(label) if label else '')
		group_layouts.append(grp.get('layout', 'row'))
		for opt in grp['options']:
			key = opt['key']
			# icon: defaults to key; 'none' means no icon
			icon_val = opt.get('icon', key)
			if icon_val != 'none':
				icon_map[key] = icon_val
			# tooltip: store only if explicitly set
			if 'tooltip' in opt:
				tooltip_map[key] = _(opt['tooltip'])
			# size hint
			if 'size' in opt:
				size_map[key] = opt['size']
	return (submodes, submodes_names, submode_defaults,
			icon_map, group_labels, group_layouts, tooltip_map, size_map)


# template source lookup: YAML template_source -> Store attribute
_TEMPLATE_MANAGERS = {
	'system': lambda: Store.tm,
	'biomolecule': lambda: Store.btm,
	'user': lambda: Store.utm,
}

# deferred import to avoid circular dependency
from bkchem.singleton_store import Store
