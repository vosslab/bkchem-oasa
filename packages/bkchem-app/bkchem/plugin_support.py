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
import sys

from bkchem import os_support
from bkchem import dom_extensions as dom_ext
from bkchem import safe_xml

from bkchem.singleton_store import Store



class plugin_manager(object):

  def __init__( self):
    self.plugins = {}
    self.descriptions = {}


  def get_available_plugins( self):
    dir2 = os_support.get_dirs( 'plugin')
    dir1 = os_support.get_bkchem_private_dir()
    dir1 = os.path.join( dir1, 'addons')
    dirs = dir2 + [dir1]
    for dir in dirs:
      if not os.path.isdir( dir):
        continue
      for name in os.listdir( dir):
        base, ext = os.path.splitext( name)
        if ext == ".xml":
          #try:
          self.read_plugin_file( dir, name)
          #except:
          #  debug.log( "could not load plugin file", name)

    return list(self.plugins.keys())


  def read_plugin_file( self, dir, name):
    doc = safe_xml.parse_dom_from_file( os.path.join( dir, name))
    root = doc.childNodes[0]
    plugin_type = root.getAttribute( 'type') or 'script'
    sources = dom_ext.simpleXPathSearch( doc, "/plugin/source")
    if sources:
      source = sources[0]
      files = dom_ext.simpleXPathSearch( source, "file")
      names = dom_ext.simpleXPathSearch( source, "menu-text")
      descs = dom_ext.simpleXPathSearch( source, "/plugin/meta/description")
      menus = dom_ext.simpleXPathSearch( source, "menu")
      if files and names:
        file = dom_ext.getAllTextFromElement( files[0])
        if not os.path.isabs( file):
          file = os.path.normpath( os.path.join( dir, file))
        name = self._select_correct_text( names)
        if menus:
          menu = dom_ext.getAllTextFromElement( menus[0])
        else:
          menu = ""

        plugin = plugin_handler( name, file, type=plugin_type,
                                 desc=self._select_correct_text( descs),
                                 menu=menu)
        self.plugins[ name] = plugin


  def run_plugin( self, name):
    handler = self.plugins[ name]

    if handler.type == "script":
      filename = handler.filename
      dirname = handler.get_directory_name()
      allowed_dirs = [os.path.realpath( d) for d in os_support.get_dirs( 'plugin')]
      personal_dir = os_support.get_bkchem_private_dir()
      if personal_dir:
        allowed_dirs.append( os.path.realpath( os.path.join( personal_dir, 'addons')))
      filename_real = os.path.realpath( filename)
      if not any( filename_real == d or filename_real.startswith( d + os.sep) for d in allowed_dirs):
        raise ValueError("Refusing to load plugin outside plugin directories: %s" % filename)
      sys.path.append( dirname)
      the_globals = {'App': Store.app}
      try:
        with open(filename) as f:
          code = compile(f.read(), filename, 'exec')
          exec(code, the_globals)  # nosec B102 - trusted plugin scripts
          plugin_main = the_globals.get( 'main')
          if callable( plugin_main):
            if hasattr( plugin_main, '__code__') and plugin_main.__code__.co_argcount == 0:
              plugin_main()
            else:
              plugin_main( Store.app)
      finally:
        del sys.path[-1]
    else:
      raise ValueError("Wrong type of plugin %s" % name)


  def get_names( self, type=""):
    if not type:
      return list(self.plugins.keys())
    else:
      return [k for k, v in list(self.plugins.items()) if v.type == type]


  def get_description( self, name):
    handler = self.get_plugin_handler( name)
    if handler:
      return handler.desc
    return ''


  def get_menu( self, name):
    handler = self.get_plugin_handler( name)
    if handler:
      return handler.menu
    return ''


  def get_plugin_handler( self, name):
    return self.plugins.get( name, None)


  def _select_correct_text( self, texts):
    """returns the right text according to the lang attribute"""
    if not texts:
      return ''
    for text in texts:
      lang = text.getAttribute( "lang") or "en"
      if lang == Store.lang:
        return dom_ext.getAllTextFromElement( text)
    # if nothing found, return the first one
    return dom_ext.getAllTextFromElement( texts[0])



class plugin_handler(object):
  """This class stores information about plugin.

  """
  def __init__( self, name, filename, type="script", desc="", menu=""):
    self.name = name
    self.type = type
    self.desc = desc
    self.filename = filename
    self.menu = menu


  def get_module_name( self):
    """returns name of module suitable for loading of this plugin via import"""
    return os.path.splitext( os.path.split( self.filename)[1])[0]


  def get_directory_name( self):
    """returns directory where the plugin resides"""
    return os.path.split( self.filename)[0]
