"""YAML submode parser for Qt modes.

Ports the submode parsing logic from the Tk config module so Qt modes
can load their submode groups from the shared modes.yaml.
"""


#============================================
def load_submodes_from_yaml(cfg: dict) -> tuple:
	"""Parse submode groups from a mode's YAML config.

	Each submode group contains a list of options with keys, names,
	icons, tooltips, and layout hints.  Dynamic groups (those without
	an 'options' key) are skipped since they are filled at runtime.

	Args:
		cfg: Mode config dict from YAML (the value under modes.<name>).

	Returns:
		Tuple of (submodes, submodes_names, submode_defaults,
			icon_map, group_labels, group_layouts, tooltip_map, size_map).
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
		# default cascade: name defaults to key
		names = [opt.get('name', opt['key']) for opt in grp['options']]
		submodes.append(keys)
		submodes_names.append(names)
		submode_defaults.append(grp.get('default', 0))
		# group label for ribbon-style display
		label = grp.get('group_label', '')
		group_labels.append(label)
		group_layouts.append(grp.get('layout', 'row'))
		for opt in grp['options']:
			key = opt['key']
			# icon: defaults to key; 'none' means no icon
			icon_val = opt.get('icon', key)
			if icon_val != 'none':
				icon_map[key] = icon_val
			# tooltip: store only if explicitly set
			if 'tooltip' in opt:
				tooltip_map[key] = opt['tooltip']
			# size hint
			if 'size' in opt:
				size_map[key] = opt['size']
	return (submodes, submodes_names, submode_defaults,
			icon_map, group_labels, group_layouts, tooltip_map, size_map)
