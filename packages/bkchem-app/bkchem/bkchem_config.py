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

# local repo modules
import bkchem.versioning

debug = 0
devel = 0

current_CDML_version = '26.07'

current_BKChem_version = bkchem.versioning.application_version()



# border width for all components of interface
border_width = 1



#============================================
def get_background_color() -> str:
	"""Return the active theme's background color."""
	from bkchem import theme_manager
	return theme_manager.get_color('background')


#============================================
def get_toolbar_color() -> str:
	"""Return the active theme's toolbar color."""
	from bkchem import theme_manager
	return theme_manager.get_color('toolbar')


#============================================
def get_separator_color() -> str:
	"""Return the active theme's separator color."""
	from bkchem import theme_manager
	return theme_manager.get_color('separator')


#============================================
def get_hover_color() -> str:
	"""Return the active theme's hover color."""
	from bkchem import theme_manager
	return theme_manager.get_color('hover')


#============================================
def get_active_mode_color() -> str:
	"""Return the active theme's active mode button color."""
	from bkchem import theme_manager
	return theme_manager.get_color('active_mode')
