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

"""

import tkinter

from bkchem import os_support

__all__ = ['images']



#============================================
def _load_icon(name: str) -> tkinter.PhotoImage:
	"""Load a pixmap icon by name, trying PNG first then GIF fallback.

	Args:
		name: icon filename stem (without extension)

	Returns:
		tkinter.PhotoImage loaded from the found file

	Raises:
		KeyError: if no PNG or GIF file exists for the name
	"""
	# try PNG first, then GIF fallback
	png_path = os_support.get_path(name + '.png', 'pixmap')
	if png_path:
		icon = tkinter.PhotoImage(file=png_path)
		return icon
	gif_path = os_support.get_path(name + '.gif', 'pixmap')
	if gif_path:
		icon = tkinter.PhotoImage(file=gif_path)
		return icon
	raise KeyError(name)


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
