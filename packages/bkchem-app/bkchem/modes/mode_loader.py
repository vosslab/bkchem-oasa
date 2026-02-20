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

"""Mode discovery and instantiation.

Scans *_mode.py files in the modes package directory, collects mode
classes, and builds mode instances from the YAML config.
"""

# Standard Library
import pathlib
import importlib

# local repo modules
from bkchem.modes.config import get_modes_config

# auto-discover *_mode.py modules and collect mode classes
_MODE_CLASS_MAP = {}
_modes_dir = pathlib.Path(__file__).parent
for _mode_file in sorted(_modes_dir.glob("*_mode.py")):
	_module_name = _mode_file.stem
	try:
		_mod = importlib.import_module(f"bkchem.modes.{_module_name}")
	except ImportError:
		continue
	# collect all classes whose name ends with _mode
	for _attr_name in dir(_mod):
		_attr = getattr(_mod, _attr_name)
		if isinstance(_attr, type) and _attr_name.endswith("_mode"):
			_MODE_CLASS_MAP[_attr_name.removesuffix("_mode")] = _attr


#============================================
def build_all_modes() -> dict:
	"""Instantiate all mode classes from the YAML config.

	Returns:
		dict mapping mode key to mode instance
	"""
	result = {}
	for yaml_key in get_modes_config()['modes']:
		mode_class = _MODE_CLASS_MAP.get(yaml_key)
		if mode_class:
			result[yaml_key] = mode_class()
	return result
