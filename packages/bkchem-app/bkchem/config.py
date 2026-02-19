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


import os

debug = 0
devel = 0

current_CDML_version = '26.02'

def _read_repo_version( key, fallback):
	version_path = os.path.abspath( os.path.join( os.path.dirname( __file__), "..", "..", "..", "version.txt"))
	if not os.path.isfile( version_path):
		return fallback
	with open( version_path, "r") as handle:
		for line in handle:
			text = line.strip()
			if not text or text.startswith( "#"):
				continue
			if "=" not in text:
				continue
			name, value = [part.strip() for part in text.split( "=", 1)]
			if name.lower() == "version" and value:
				return value
			if name.lower() == key.lower() and value:
				return value
	return fallback

current_BKChem_version = _read_repo_version( "bkchem", "26.02")



# border width for all components of interface
border_width = 1

background_color = "#eaeaea"
