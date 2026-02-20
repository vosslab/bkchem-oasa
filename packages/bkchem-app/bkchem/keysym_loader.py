#--------------------------------------------------------------------------
#     This file is part of BKChem - a chemical drawing program
#     Copyright (C) 2002-2009 Beda Kosata <beda@zirael.org>

#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 3 of the License, or
#     (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

#     Complete text of GNU GPL can be found in the file gpl.txt in the
#     main directory of the program

#--------------------------------------------------------------------------
"""Cached loader for keysym definition data."""

# Standard Library
import os

# PIP3 modules
import yaml

# local repo modules
from bkchem import os_support

_KEYSYMS_CACHE = None

#============================================
def get_keysyms() -> dict:
	"""Load and cache the keysym-to-Unicode mapping from YAML.

	Returns:
		dict: mapping of keysym names to Unicode characters.
	"""
	global _KEYSYMS_CACHE
	if _KEYSYMS_CACHE is None:
		data_dir = os_support._get_bkchem_data_dir()
		yaml_path = os.path.join(data_dir, "keysymdef.yaml")
		with open(yaml_path) as fh:
			_KEYSYMS_CACHE = yaml.safe_load(fh)
	return _KEYSYMS_CACHE
