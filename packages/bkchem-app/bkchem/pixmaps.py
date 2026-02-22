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

"""Images for buttons all over BKChem.

Loads toolbar icons from per-theme PNG subdirectories.  The active theme
determines which directory is searched first (e.g. ``pixmaps/png-dark/``
for the dark theme), falling back to ``pixmaps/png/`` for the light theme.
PNGs are pre-generated build artifacts from SVG sources in ``pixmaps/src/``.
Do not hand-edit PNGs; run ``tools/generate_theme_icons.py`` instead.
"""

# Standard Library
import os

import tkinter

from bkchem import os_support

__all__ = ['images']


#============================================
def _get_theme_icon_subdir() -> str:
	"""Return the theme-specific PNG subdirectory name.

	For the light theme (or when no theme is active), returns 'png'.
	For other themes, returns 'png-{theme_name}' (e.g. 'png-dark').

	Returns:
		str: subdirectory name within the pixmaps directory
	"""
	try:
		from bkchem import theme_manager
		theme_name = theme_manager.get_active_theme_name()
	except Exception:
		theme_name = 'light'
	if theme_name == 'light':
		return 'png'
	return f'png-{theme_name}'


#============================================
def _find_icon_path(name: str) -> str:
	"""Locate the PNG icon file for the given name.

	Searches the theme-specific PNG subdirectory first, then falls
	back to the default png/ subdirectory across all pixmap directories
	registered in os_support.

	Args:
		name: icon filename stem (without extension)

	Returns:
		str: absolute path to the icon file

	Raises:
		KeyError: if no PNG file exists for the name
	"""
	dirs = os_support.get_dirs('pixmap')
	theme_subdir = _get_theme_icon_subdir()
	for base_dir in dirs:
		# try theme-specific subdirectory first (e.g. png-dark/)
		if theme_subdir != 'png':
			theme_path = os.path.join(base_dir, theme_subdir, name + '.png')
			if os.path.isfile(theme_path):
				return theme_path
		# fallback: default png/ subdirectory
		png_path = os.path.join(base_dir, 'png', name + '.png')
		if os.path.isfile(png_path):
			return png_path
	raise KeyError(name)


#============================================
def _load_icon(name: str) -> tkinter.PhotoImage:
	"""Load a pixmap icon by name from the theme-appropriate directory.

	Args:
		name: icon filename stem (without extension)

	Returns:
		tkinter.PhotoImage with proper alpha transparency

	Raises:
		KeyError: if no PNG file exists for the name
	"""
	icon_path = _find_icon_path(name)
	icon = tkinter.PhotoImage(file=icon_path)
	return icon


#============================================
def reload_icons() -> None:
	"""Clear the icon cache so icons are reloaded with current theme colors.

	Call this after a theme switch to force reloading from the new
	theme-specific PNG directory on next access.
	"""
	images.clear()


#============================================
class images_dict(dict):
	"""Paths to pictures.

	If asked about a pixmap it looks to the filesystem and
	adds the path into itself if found.
	"""

	def __getitem__(self, item: str) -> tkinter.PhotoImage:
		# normalize to lowercase for filesystem lookup (handles 2D->2d, 3D->3d, etc.)
		item = item.lower()
		try:
			return dict.__getitem__(self, item)
		except KeyError:
			icon = _load_icon(item)
			self.__setitem__(item, icon)
			return icon

	def __contains__(self, item: object) -> bool:
		# normalize to lowercase for filesystem lookup
		if isinstance(item, str):
			item = item.lower()
		if dict.__contains__(self, item):
			return True
		try:
			icon = _load_icon(item)
			self.__setitem__(item, icon)
			return True
		except KeyError:
			return False

images = images_dict()
