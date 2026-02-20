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

"""Modes package - paper operating modes (edit, draw, template, etc.).

Public API:
	build_all_modes()      - instantiate all mode classes from YAML config
	get_toolbar_order()    - toolbar mode ordering from YAML
	get_modes_config()     - cached modes YAML config dict
	get_edit_pool_config() - cached edit pool button config from YAML
	event_to_key()         - convert tkinter key event to normalized key string
"""

# config loaders (public API)
from bkchem.modes.config import get_modes_config
from bkchem.modes.config import get_toolbar_order
from bkchem.modes.config import get_edit_pool_config

# event utility (public API)
from bkchem.modes.modes_lib import event_to_key

# base classes
from bkchem.modes.modes_lib import mode
from bkchem.modes.modes_lib import simple_mode
from bkchem.modes.modes_lib import basic_mode

# edit mode (parent of most leaf modes)
from bkchem.modes.edit_mode import edit_mode

# leaf modes
from bkchem.modes.draw_mode import draw_mode
from bkchem.modes.arrow_mode import arrow_mode
from bkchem.modes.plus_mode import plus_mode
from bkchem.modes.template_mode import template_mode
from bkchem.modes.template_mode import biotemplate_mode
from bkchem.modes.template_mode import usertemplate_mode
from bkchem.modes.text_mode import text_mode
from bkchem.modes.rotate_mode import rotate_mode
from bkchem.modes.bondalign_mode import bondalign_mode
from bkchem.modes.vector_mode import vector_mode
from bkchem.modes.mark_mode import mark_mode
from bkchem.modes.atom_mode import atom_mode
from bkchem.modes.bracket_mode import bracket_mode
from bkchem.modes.misc_mode import misc_mode
from bkchem.modes.repair_mode import repair_mode

# backward-compatible aliases
from bkchem.modes.template_mode import biomolecule_template_mode
from bkchem.modes.template_mode import user_template_mode
from bkchem.modes.bondalign_mode import bond_align_mode


# mode class lookup by YAML key
_MODE_CLASS_MAP = {
	'edit': edit_mode,
	'draw': draw_mode,
	'template': template_mode,
	'biotemplate': biotemplate_mode,
	'usertemplate': usertemplate_mode,
	'atom': atom_mode,
	'mark': mark_mode,
	'arrow': arrow_mode,
	'plus': plus_mode,
	'text': text_mode,
	'bracket': bracket_mode,
	'rotate': rotate_mode,
	'bondalign': bondalign_mode,
	'vector': vector_mode,
	'repair': repair_mode,
	'misc': misc_mode,
}


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
