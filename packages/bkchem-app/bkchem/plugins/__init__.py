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



import importlib
import sys
import traceback

from bkchem import bkchem_config


__all__ = []

# format/render plugins were removed in Phases A/C; legacy GTML import remains
_names = ["gtml"]

for _name in _names:
  try:
    importlib.import_module(".%s" % _name, __name__)
    __all__.append(_name)
  except Exception as exc:
    sys.stderr.write(
      "Could not load module %s: %s: %s\n" % (_name, exc.__class__.__name__, exc)
    )
    if bkchem_config.debug:
      traceback.print_exc()

del _name
del _names
