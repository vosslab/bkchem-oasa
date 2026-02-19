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

"""Main application class.

"""



import builtins
import os
import sys
import oasa
import collections
import importlib.util

from tkinter import Button, Frame, Label, Scrollbar, StringVar, Tk
from tkinter import HORIZONTAL, LEFT, RAISED, SUNKEN, VERTICAL
from tkinter.filedialog import asksaveasfilename, askopenfilename
import tkinter.messagebox

import Pmw
from bkchem import data
from bkchem import bkchem_utils
from bkchem import modes
from bkchem import bkchem_config
from bkchem import export
from bkchem import logger
from bkchem import dialogs
from bkchem import pixmaps
from bkchem import plugins
from bkchem import format_loader
from bkchem import messages
from bkchem import molecule_lib
from bkchem import os_support
from bkchem import interactors
from bkchem import oasa_bridge
from bkchem import safe_xml
from bkchem.paper import chem_paper
from bkchem.edit_pool import editPool
from bkchem.id_manager import id_manager
from bkchem.temp_manager import template_manager
from bkchem.plugin_support import plugin_manager
from bkchem.singleton_store import Store, Screen

_ = builtins.__dict__.get( '_', lambda m: m)



class BKChem( Tk):

  def __init__( self):
    Tk.__init__( self)
    # setting the singleton values
    Store.app = self
    Screen.dpi = self.winfo_fpixels( "1i")

    self.tk.call("tk", "useinputmethods", "1")
    #self.tk.call( "encoding", "system", "iso8859-2")
    #print(self.tk.call( "encoding", "system"))
    #self.option_add( "*Background", "#eaeaea")
    self.option_add( "*Entry*Background", "white")
    self.option_add( "*Entry*Foreground", "#000000")
    self.tk_setPalette( "background", bkchem_config.background_color,
                        "insertBackground","#ffffff")

    oasa.oasa_config.Config.molecule_class = molecule_lib.BkMolecule


  def initialize( self):
    self.in_batch_mode = 0
    self.init_basics()
    # register ABC virtual subclasses so is_chemistry_vertex/edge/graph work
    import bkchem.chem_compat
    bkchem.chem_compat.register_bkchem_classes()

    # main drawing part
    self.papers = []
    self.notebook = Pmw.NoteBook( self.main_frame,
                                  raisecommand=self.change_paper,
                                  borderwidth=bkchem_config.border_width)
    self.add_new_paper()

    # template and group managers
    self.init_singletons()

    # menu initialization
    self.init_menu()
    self.init_plugins_menu()

    # modes initialization
    self.init_modes()
    self.mode = 'draw' # this is normaly not a string but it makes things easier on startup
    self.init_mode_buttons()

    # edit pool (Entry only; buttons are created per-mode in change_mode)
    self.editPool = editPool( self.main_frame, width=60)
    # hidden until an edit_mode-derived mode activates it
    self.editPool.grid( row=3, sticky="wens")
    self.editPool.grid_remove()

    # main drawing part packing
    self.notebook.grid( row=4, sticky="wens")
    self.notebook.setnaturalsize()


    # preferences
    self.init_preferences()

    # init status bar
    self.init_status_bar()

    #
    self.radiobuttons.invoke( self.mode)

    # protocol bindings
    self.protocol("WM_DELETE_WINDOW", self._quit)


    self.update_menu_after_selection_change( None)

  def initialize_batch( self):
    self.in_batch_mode = 1
    self.init_basics()
    # register ABC virtual subclasses so is_chemistry_vertex/edge/graph work
    import bkchem.chem_compat
    bkchem.chem_compat.register_bkchem_classes()

    # main drawing part
    self.papers = []
    self.notebook = Pmw.NoteBook( self.main_frame,
                                  raisecommand=self.change_paper)
    self.add_new_paper()

    # template and group managers
    self.init_singletons()

    # not very verbose logging strategy
    Store.logger.handling = logger.batch_mode

    # main drawing part packing
    self.notebook.grid( row=4, sticky="wens")

    # protocol bindings
    self.protocol("WM_DELETE_WINDOW", self._quit)

    # modes initialization
    self.mode = 'draw' # this is normaly not a string but it makes things easier on startup


  def init_menu( self):
    # defining menu
    self._use_system_menubar = sys.platform == "darwin"
    if self._use_system_menubar:
      self.menu = Pmw.MainMenuBar( self, balloon=self.menu_balloon)
      self.configure( menu=self.menu)
    else:
      menuf = Frame( self.main_frame, relief=RAISED, bd=bkchem_config.border_width)
      menuf.grid( row=0, sticky="we")

      self.menu = Pmw.MenuBar( menuf, balloon=self.menu_balloon)
      self.menu.pack( side="left", expand=1, fill="both")

    self.menu_template = [
      # file menu
      ( _('File'),  'menu',     _('Open, save, export, and import files'),   'left'),
      #  menu         type        name            accelerator  status help                          command             state variable
      ( _('File'),  'command',  _('New'),       '(C-x C-n)', _("Create a new file in a new tab"), self.add_new_paper, None),
      ( _('File'),  'command',  _('Save'),      '(C-x C-s)', _("Save the file"),                  self.save_CDML,     None),
      ( _("File"),  'command',  _('Save As..'), '(C-x C-w)', _("Save the file under different name"), self.save_as_CDML, None),
      ( _("File"),  'command',  _('Save As Template'), None, _("Save the file as template, certain criteria must be met for this to work"), self.save_as_template, None),
      ( _("File"),  'command',  _('Load'),      '(C-x C-f)', _("Load (open) a file in a new tab"), self.load_CDML,    None),
      ( _("File"),  'command',  _('Load to the same tab'), None, _("Load a file replacing the current one"), lambda : self.load_CDML( replace=1), None),
      ( _("File"),  'cascade',  _("Recent files"), _("The most recently used files")),
      ( _("File"),  'separator'),
      # export cascade
      ( _("File"),  'cascade',  _('Export'),     _("Export the current file")),
      ( _("File"),  'cascade',  _('Import'),     _("Import a non-native file format")),
      ( _("File"),  'separator'),
      ( _("File"),  'command',  _('File properties'), None, _("Set the papers size and other properties of the document"), self.change_properties, None),
      ( _("File"),  'separator'),
      ( _("File"),  'command',  _('Close tab'), '(C-x C-t)', _("Close the current tab, exit when there is only one tab"), self.close_current_paper, None),
      ( _("File"),  'separator'),
      ( _("File"),  'command',  _('Exit'),      '(C-x C-c)', _("Exit BKChem"), self._quit, None),

      # edit menu
      ( _('Edit'),  'menu',     _("Undo, Copy, Paste etc."),   'left'),
      ( _("Edit"),  'command',  _('Undo'),      '(C-z)',     _("Revert the last change made"), lambda : self.paper.undo(), lambda : self.paper.um.can_undo()),
      ( _("Edit"),  'command',  _('Redo'),      '(C-S-z)',   _("Revert the last undo action"), lambda : self.paper.redo(), lambda : self.paper.um.can_redo()),
      ( _("Edit"),  'separator'),
      ( _("Edit"),  'command',  _('Cut'), '(C-w)', _("Copy the selected objects to clipboard and delete them"), lambda : self.paper.selected_to_clipboard( delete_afterwards=1),  'selected'),
      ( _("Edit"),  'command', _('Copy'), '(A-w)', _("Copy the selected objects to clipboard"), lambda : self.paper.selected_to_clipboard(),  'selected'),
      ( _("Edit"),  'command', _('Paste'), '(C-y)', _("Paste the content of clipboard to current paper"), lambda : self.paper.paste_clipboard( None), lambda : self._clipboard),
      ( _("Edit"),  'separator'),
      ( _("Edit"),  'command', _('Selected to clipboard as SVG'), None, _("Create SVG for the selected objects and place it to clipboard in text form"), lambda : self.paper.selected_to_real_clipboard_as_SVG(),  'selected'),
      ( _("Edit"),  'separator'),
      ( _("Edit"),  'command', _('Select all'), '(C-S-a)', _("Select everything on the paper"), lambda : self.paper.select_all(),  None),

      # insert menu
      ( _('Insert'), 'menu', _("Insert templates and reusable structures"), 'left'),
      ( _("Insert"), 'command', _('Biomolecule template'), None, _("Insert a biomolecule template into the drawing"), self.insert_biomolecule_template, None),

      # align menu
      ( _('Align'), 'menu',    _("Aligning of selected objects"), 'left'),
      ( _("Align"), 'command', _('Top'), '(C-a C-t)', _("Align the tops of selected objects"), lambda : self.paper.align_selected( 't'), 'two_or_more_selected'),
      ( _("Align"), 'command', _('Bottom'), '(C-a C-b)', _("Align the bottoms of selected objects"), lambda : self.paper.align_selected( 'b'), 'two_or_more_selected'),
      ( _("Align"), 'command', _('Left'), '(C-a C-l)', _("Align the left sides of selected objects"), lambda : self.paper.align_selected( 'l'), 'two_or_more_selected'),
      ( _("Align"), 'command', _('Right'), '(C-a C-r)', _("Align the rights sides of selected objects"), lambda : self.paper.align_selected( 'r'), 'two_or_more_selected'),
      ( _("Align"), 'separator'),
      ( _("Align"), 'command', _('Center horizontally'), '(C-a C-h)', _("Align the horizontal centers of selected objects"), lambda : self.paper.align_selected( 'h'), 'two_or_more_selected'),
      ( _("Align"), 'command', _('Center vertically'), '(C-a C-v)', _("Align the vertical centers of selected objects"), lambda : self.paper.align_selected( 'v'), 'two_or_more_selected'),

      # object menu
      ( _("Object"), 'menu',    _("Set properties of selected objects"), 'left'),
      ( _("Object"), 'command', _('Scale'), None, _("Scale selected objects"), self.scale, 'selected'),
      ( _("Object"), 'separator'),
      ( _("Object"), 'command', _('Bring to front'), '(C-o C-f)', _("Lift selected objects to the top of the stack"), lambda : self.paper.lift_selected_to_top(), 'selected'),
      ( _("Object"), 'command', _('Send back'), '(C-o C-b)', _("Lower the selected objects to the bottom of the stack"), lambda : self.paper.lower_selected_to_bottom(), 'selected'),
      ( _("Object"), 'command', _('Swap on stack'), '(C-o C-s)', _("Reverse the ordering of the selected objects on the stack"), lambda : self.paper.swap_selected_on_stack(), 'two_or_more_selected'),
      ( _("Object"), 'separator'),
      ( _("Object"), 'command', _('Vertical mirror'), None,
        _("Creates a reflection of the selected objects, the reflection axis is the common vertical axis of all the selected objects"),
        lambda : self.paper.swap_sides_of_selected(), 'selected_mols'),
      ( _("Object"), 'command', _('Horizontal mirror'), None,
        _("Creates a reflection of the selected objects, the reflection axis is the common horizontal axis of all the selected objects"),
        lambda : self.paper.swap_sides_of_selected('horizontal'), 'selected_mols'),
      ( _("Object"), 'separator'),
      ( _("Object"), 'command', _('Configure'), 'Mouse-3', _("Set the properties of the object, such as color, font size etc."), lambda : self.paper.config_selected(), 'selected'),
      #( _("Object"), 'separator')

      # view menu
      ( _('View'), 'menu', _("Zoom and display controls"), 'left'),
      ( _('View'), 'command', _('Zoom In'), '(C-+)', _("Zoom in"), lambda: self.paper.zoom_in(), None),
      ( _('View'), 'command', _('Zoom Out'), '(C--)', _("Zoom out"), lambda: self.paper.zoom_out(), None),
      ( _('View'), 'separator'),
      ( _('View'), 'command', _('Zoom to 100%'), '(C-0)', _("Reset zoom to 100%"), lambda: self.paper.zoom_reset(), None),
      ( _('View'), 'command', _('Zoom to Fit'), None, _("Fit drawing to window"), lambda: self.paper.zoom_to_fit(), None),
      ( _('View'), 'command', _('Zoom to Content'), None, _("Fit and center on drawn content"), lambda: self.paper.zoom_to_content(), None),
      ( _('View'), 'separator'),
      ( _('View'), 'command', _('Show Hex Grid'), '(C-g)', _("Toggle hex grid dot overlay"), lambda: self.paper.toggle_hex_grid(), None),
      ( _('View'), 'command', _('Snap to Hex Grid'), '(S-C-g)', _("Toggle snap-to-grid for atom placement"), lambda: self.paper.toggle_hex_grid_snap(), None),

      # chemistry menu
      ( _('Chemistry'), 'menu', _("Information about molecules, group expansion and other chemistry related stuff"), 'left'),
      ( _("Chemistry"), 'command', _('Info'), '(C-o C-i)', _("Display summary formula and other info on all selected molecules"), lambda : self.paper.display_info_on_selected(), 'selected_mols'),
      ( _("Chemistry"), 'command', _('Check chemistry'), '(C-o C-c)', _("Check if the selected objects have chemical meaning"), lambda : self.paper.check_chemistry_of_selected(), 'selected_mols'),
      ( _("Chemistry"), 'command', _('Expand groups'), '(C-o C-e)', _("Expand all selected groups to their structures"), lambda : self.paper.expand_groups(), 'groups_selected'),
      ( _("Chemistry"), 'separator'),
      ( _("Chemistry"), 'command', _('Compute oxidation number'), None, _("Compute and display the oxidation number of selected atoms"), lambda : interactors.compute_oxidation_number( self.paper), 'selected_atoms'),
      ( _("Chemistry"), 'separator'),
      ( _("Chemistry"), 'command', _('Read SMILES'), None, _("Read a SMILES string and convert it to structure"), self.read_smiles, None),
      ( _("Chemistry"), 'command', _('Read InChI'), None, _("Read an InChI string and convert it to structure"), self.read_inchi, None),
      ( _("Chemistry"), 'command', _('Read Peptide Sequence'), None, _("Read a peptide amino acid sequence and convert it to structure"), self.read_peptide_sequence, None),
      ( _("Chemistry"), 'separator'),
      ( _("Chemistry"), 'command', _('Generate SMILES'), None, _("Generate SMILES for the selected structure"), self.gen_smiles, 'selected_mols'),
      ( _("Chemistry"), 'command', _('Generate InChI'), None, _("Generate an InChI for the selected structure by calling the InChI program"), self.gen_inchi,
        lambda : Store.pm.has_preference("inchi_program_path") and self.paper.selected_mols),
      ( _("Chemistry"), 'separator'),
      #( _("Chemistry"), 'command', _('Set display form'), "(C-o C-d)",
      #  _("The display form is stored in the saved file and tells how the molecule should be displayed in text"),
      #  lambda : interactors.ask_display_form_for_selected( self.paper), 'selected_mols'),
      ( _("Chemistry"), 'command', _('Set molecule name'), None, _("Set the name of the selected molecule"), lambda : interactors.ask_name_for_selected( self.paper), 'selected_mols'),
      ( _("Chemistry"), 'command', _('Set molecule ID'), None, _("Set the ID of the selected molecule"), lambda : interactors.ask_id_for_selected( self.paper), 'one_mol_selected'),
      ( _("Chemistry"), 'separator'),
      ( _("Chemistry"), 'command', _('Create fragment'), None, _("Create a fragment from the selected part of the molecule"), lambda : interactors.create_fragment_from_selected( self.paper), 'one_mol_selected'),
      ( _("Chemistry"), 'command', _('View fragments'), None, _("Show already defined fragments"), lambda : interactors.view_fragments( self.paper), None),
      ( _("Chemistry"), 'separator'),
      ( _("Chemistry"), 'command', _('Convert selection to linear form'), None, _("Convert selected part of chain to linear fragment. The selected chain must not be split."), lambda : interactors.convert_selected_to_linear_fragment( self.paper), 'selected_mols'),
      #

      # options
      ( _('Options'), 'menu',    _("Settings that affect how BKChem works"), 'left'),
      ( _("Options"), 'command', _('Standard'), None, _("Set the default drawing style here"), self.standard_values, None),
      ( _("Options"), 'command', _('Language'), None, _("Set the language used after next restart"), lambda : interactors.select_language( self.paper), None),
      ( _("Options"), 'command', _('Logging'), None, _("Set how messages in BKChem are displayed to you"), lambda : interactors.set_logging( self.paper, Store.logger), None),
      ( _("Options"), 'command', _('InChI program path'), None, _("To use InChI in BKChem you must first give it a path to the InChI program here"),
        interactors.ask_inchi_program_path, None),
      ( _("Options"), 'separator'),
      ( _("Options"), 'command', _('Preferences'), None, _("Preferences"), self.ask_preferences, None),

      # help menu
      ( _('Help'), 'menu', _("Help and information about the program"), "right"),
      ( _("Help"), 'command', _('About'), None, _("General information about BKChem"), self.about, None),

      # plugins menu
      ( _("Plugins"), 'menu', _("Small additional scripts"), "right")
      ]



## ##     hacksButton.pack( side= 'right')
## ##     hacksMenu = Menu( hacksButton, tearoff=0)
## ##     hacksButton['menu'] = hacksMenu
## ##     hacksMenu.add( 'command', label=_('Molecules to separate tabs'), command=self.molecules_to_separate_tabs)
## ##     hacksMenu.add( 'command', label=_('Rings to separate tabs'), command=self.rings_to_separate_tabs)
## ##     hacksMenu.add( 'command', label=_('Normalize aromatic double bonds'), command=self.normalize_aromatic_double_bonds)
## ##     hacksMenu.add( 'command', label=_('Clean'), command=self.clean)


    # CREATION OF THE MENU

    menus = set() # we use this later for plugin entries addition

    for temp in self.menu_template:
      if temp[1] == "menu":
        if self._use_system_menubar:
          self.menu.addmenu( temp[0], temp[2])
        else:
          self.menu.addmenu( temp[0], temp[2], side=temp[3])
        menus.add( temp[0])
      elif temp[1] == "command":
        menu, _ignore, label, accelerator, help, command, state_var = temp
        self.menu.addmenuitem( menu, 'command', label=label, accelerator=accelerator, statusHelp=help, command=command)
      elif temp[1] == "separator":
        self.menu.addmenuitem( temp[0], 'separator')
      elif temp[1] == "cascade":
        self.menu.addcascademenu( temp[0], temp[2], temp[3], tearoff=0)


    # ADDITION OF PLUGINS TO THE MENU

    added_to = set()
    for name in self.plug_man.get_names( type="script"):
      tooltip = self.plug_man.get_description( name)
      menu = self.plug_man.get_menu( name)
      if menu and _(menu) in menus:
        menu = _(menu)
        if not menu in added_to:
          self.menu.addmenuitem( menu, "separator")
      else:
        menu = _("Plugins")

      self.menu.addmenuitem( menu, 'command', label=name,
                               statusHelp=tooltip,
                               command=bkchem_utils.lazy_apply( self.run_plugin, (name,)))
      added_to.add( menu)


  def init_basics( self):
    Pmw.initialise( self)
    # set default font for all widgets
    if sys.platform == 'linux':
      try:
        self.option_add( "*font", ("-adobe-helvetica-medium-r-normal-*-12-*-*-*-p-*-iso10646-1"))
      except:
        print("cannot init default font")
    elif sys.platform != 'darwin':
      # Windows and other platforms
      self.option_add( "*font", ("Helvetica", 10, "normal"))
    # on macOS (darwin), skip setting *font entirely so Tk uses
    # the native system font (San Francisco / Lucida Grande)
    # colors
    #self.option_add( "*background", "#d0d0d0")
    #self.option_add( "*borderwidth", config.border_width)
    self.title( "BKChem")
    self.stat= StringVar()
    self.cursor_position = StringVar()
    self.stat.set( "Idle")
    self.save_dir = '.'
    self.save_file = None
    self.svg_dir = '.'
    self.svg_file = ''
    self._recent_files = []

    self._clipboard = None
    self._clipboard_pos = None

    self._untitled_counter = 0
    self.__tab_name_2_paper = {}
    self.__last_tab = 0

    self._after = None

    self.balloon = Pmw.Balloon( self)
    self.menu_balloon = Pmw.Balloon( self, statuscommand=self.update_status)
    self.main_frame = Frame( self)
    self.main_frame.pack( fill='both', expand=1)
    self.main_frame.rowconfigure( 4, weight=1)
    self.main_frame.columnconfigure( 0, weight=1)

    self.plugins = {}
    if plugins.__all__:
      for name in plugins.__all__:
        plugin = plugins.__dict__[ name]
        self.plugins[ plugin.name] = plugin
    self.format_entries = {}

    self.paper = None


  def init_plugins_menu( self):
    # registry-backed formats
    try:
      self.format_entries = format_loader.load_format_entries()
    except Exception as error:
      Store.log( _("Could not load format manifest: %s") % error)
      self.format_entries = {}

    format_names = sorted( self.format_entries.keys(),
                           key=lambda n: self.format_entries[n]["display_name"].lower())
    for codec_name in format_names:
      entry = self.format_entries[ codec_name]
      local_name = entry["display_name"]
      if entry.get("can_import"):
        self.menu.addmenuitem( _("Import"), 'command', label=local_name,
                               statusHelp=_("Imports %s format.") % local_name,
                               command=bkchem_utils.lazy_apply( self.format_import, (codec_name,)))
      if entry.get("can_export"):
        self.menu.addmenuitem( _("Export"), 'command', label=local_name,
                               statusHelp=_("Exports %s format.") % local_name,
                               command=bkchem_utils.lazy_apply( self.format_export, (codec_name,)))

    # legacy plugin path (GTML import-only)
    names = sorted(self.plugins.keys())
    for name in names:
      plugin = self.plugins[ name]
      local_name = hasattr( plugin, "local_name") and getattr( plugin, "local_name") or plugin.name
      if ('importer' in  plugin.__dict__) and plugin.importer:
        doc_string = hasattr( plugin.importer, "doc_string") and getattr( plugin.importer, "doc_string") or plugin.importer.__doc__
        self.menu.addmenuitem( _("Import"), 'command', label=local_name,
                               statusHelp=doc_string,
                               command=bkchem_utils.lazy_apply( self.plugin_import, (plugin.name,)))
      if ('exporter' in plugin.__dict__) and plugin.exporter:
        doc_string = hasattr( plugin.exporter, "doc_string") and getattr( plugin.exporter, "doc_string") or plugin.exporter.__doc__
        self.menu.addmenuitem( _("Export"), 'command', label=local_name,
                               statusHelp=doc_string,
                               command=bkchem_utils.lazy_apply( self.plugin_export, (plugin.name,)))


  def init_singletons( self):
    # logger
    Store.logger = logger.logger()
    Store.log = Store.logger.log

    # id_manager
    Store.id_manager = id_manager()

    # template_manager
    Store.tm = template_manager()
    Store.tm.add_template_from_CDML( "templates.cdml")

    # manager for user user defined templates
    Store.utm = template_manager()
    self.read_user_templates()

    # manager for biomolecule templates
    Store.btm = template_manager()
    self.read_biomolecule_templates()

    # groups manager
    Store.gm = template_manager()
    Store.gm.add_template_from_CDML( "groups.cdml")
    Store.gm.add_template_from_CDML( "groups2.cdml")

    self.plug_man = plugin_manager()
    self.plug_man.get_available_plugins()


  def init_preferences( self):
    # load the last working directory as def. dir.
    self.save_dir = Store.pm.get_preference( "default-dir")
    # self.paper has to be added before init_preferences (otherwise -> crash)
    # so we need to update the save directory of the file now
    self.paper.file_name = self.get_name_dic()
    for i in range( 5):
      path = Store.pm.get_preference( "recent-file%d" % (i+1))
      if path:
        self._recent_files.append( path)
        self.menu.addmenuitem( _("Recent files"), 'command', label=path,
                               command=bkchem_utils.lazy_apply( self.load_CDML, (path,)))
    if not self.in_batch_mode:
      # we do not load (or save) handling info when in batch mode
      for key in Store.logger.handling:
        value = Store.pm.get_preference( "logging_%s"%key)
        if value:
          Store.logger.set_handling( key, value)


  def init_modes( self):
    # build all mode instances from YAML config
    self.modes = modes.build_all_modes()
    self.modes_sort = modes.get_toolbar_order()

    # import plugin modes
    for plug_name in self.plug_man.get_names( type="mode"):
      plug = self.plug_man.get_plugin_handler( plug_name)
      module_name = plug.get_module_name()
      try:
        spec = importlib.util.spec_from_file_location( module_name, plug.filename)
        if not spec or not spec.loader:
          continue
        module = importlib.util.module_from_spec( spec)
        spec.loader.exec_module( module)
      except ImportError:
        continue
      else:
        self.modes[ module_name.replace("_","")] = module.plugin_mode()
        self.modes_sort.append( module_name.replace("_",""))


  def init_mode_buttons( self):
    # mode selection panel
    radioFrame = Frame( self.main_frame)
    radioFrame.grid( row=1, sticky='we')
    self.radiobuttons = Pmw.RadioSelect(radioFrame,
                                        buttontype = 'button',
                                        selectmode = 'single',
                                        orient = 'horizontal',
                                        command = self.change_mode,
                                        hull_borderwidth = 0,
                                        padx = 0,
                                        pady = 0,
                                        hull_relief = 'flat',

             )
    self.radiobuttons.pack( side=LEFT)
    # Add some buttons to the radiobutton RadioSelect.
    for m in self.modes_sort:
      if m in pixmaps.images:
        recent = self.radiobuttons.add( m, image=pixmaps.images[m], text=self.modes[m].label,
                                        compound='top', activebackground='grey',
                                        relief='flat', borderwidth=bkchem_config.border_width)
        self.balloon.bind( recent, self.modes[ m].name)
      else:
        self.radiobuttons.add( m, text=self.modes[ m].label, borderwidth=bkchem_config.border_width)
    # sub-mode support
    self.subFrame = Frame( self.main_frame)
    self.subFrame.grid( row=2, sticky='we')
    self.subbuttons = []
    # the remaining of sub modes support is now in self.change_mode


  def init_status_bar( self):
    status_frame = Frame( self.main_frame)
    status_frame.grid( row=5, sticky="we")
    status = Label( status_frame, relief=SUNKEN, bd=bkchem_config.border_width, textvariable=self.stat, anchor='w', height=2, justify='l')
    status.pack( side="left", expand=1, fill="both")
    position = Label( status_frame, relief=SUNKEN, bd=bkchem_config.border_width, textvariable=self.cursor_position, anchor='w', height=2, justify='l')
    position.pack( side="right")


  def about( self):
    dialog = Pmw.MessageDialog(self,
                               title = _('About BKChem'),
                               defaultbutton = 0,
                               buttons=(_("OK"),),
                               message_text = "BKChem " + _("version") + " " + bkchem_config.current_BKChem_version + "\n\n" + messages.about_text)
    dialog.iconname('BKChem')
    dialog.activate()


  def change_mode( self, tag):
    old_mode = self.mode
    self.mode = self.modes[ tag]
    if not bkchem_utils.myisstr(old_mode):
      old_mode.cleanup()
      self.mode.copy_settings( old_mode)

    # tear down previous submode widgets (buttons, labels, separators)
    # destroy edit pool buttons before destroying the ribbon frame they live in
    self.editPool.destroy_buttons()
    if self.subbuttons:
      for butts in self.subbuttons:
        if hasattr( butts, 'deleteall()'):
          butts.deleteall()
        butts.destroy()
    self.subbuttons = []
    for widget in getattr(self, '_sub_extra_widgets', []):
      widget.destroy()
    self._sub_extra_widgets = []

    m = self.mode
    # YAML-driven ribbon fields
    mode_icon_map = getattr(m, 'icon_map', {})
    group_labels = getattr(m, 'group_labels', [])
    tooltip_map = getattr(m, 'tooltip_map', {})

    for i in range( len( m.submodes)):
      # render group label before button row (ribbon-style separator)
      label_text = group_labels[i] if i < len(group_labels) else ''
      if label_text:
        # vertical separator line between groups (skip before first group)
        if i > 0:
          sep = Frame(self.subFrame, width=1, bg='#b0b0b0')
          sep.pack(side=LEFT, fill='y', padx=2, pady=1)
          self._sub_extra_widgets.append(sep)
        # compact group label
        lbl = Label(self.subFrame, text=label_text, font=('sans-serif', 8),
                    fg='#666666', anchor='w', padx=1, pady=0)
        lbl.pack(side=LEFT, padx=(2, 0))
        self._sub_extra_widgets.append(lbl)

      # determine layout for this submode group
      layout = 'row'
      if hasattr(m, 'group_layouts') and i < len(m.group_layouts):
        layout = m.group_layouts[i]

      if layout == 'grid':
        # button grid layout (e.g. biomolecule templates with short labels)
        grid_frame = self._build_submode_grid(m, i, tooltip_map)
        self.subbuttons.append(grid_frame)
        grid_frame.pack(side=LEFT, padx=(0, 2))
      elif layout == 'row':
        # normal horizontal button row
        self.subbuttons.append( Pmw.RadioSelect( self.subFrame,
                                                 buttontype = 'button',
                                                 selectmode = 'single',
                                                 orient = 'horizontal',
                                                 command = self.change_submode,
                                                 hull_borderwidth = 0,
                                                 padx = 0,
                                                 pady = 0,
                                                 hull_relief = 'ridge',
                                                 ))
        self.subbuttons[i].pack(side=LEFT, padx=(0, 2))
        for sub in m.submodes[i]:
          # use icon_map for YAML default cascade (key->icon override)
          icon_name = mode_icon_map.get(sub, sub)
          img_name = m.__class__.__name__.replace("_mode","") + "-" + icon_name
          if img_name in pixmaps.images:
            img = pixmaps.images[img_name]
          elif icon_name in pixmaps.images:
            img = pixmaps.images[icon_name]
          else:
            img = None
          # tooltip: prefer YAML tooltip_map, fall back to display name
          sub_idx = m.submodes[i].index(sub)
          display_name = m.submodes_names[i][sub_idx]
          tip_text = tooltip_map.get(sub, display_name)
          if img:
            recent = self.subbuttons[i].add( sub, image=img, activebackground='grey', borderwidth=bkchem_config.border_width)
            self.balloon.bind(recent, tip_text)
          else:
            self.subbuttons[i].add( sub, text=display_name, borderwidth=bkchem_config.border_width)
        # select the default submode
        j = m.submodes[i][ m.submode[i]]
        self.subbuttons[i].invoke( j)
      else:
        # fallback: dropdown menu
        self.subbuttons.append( Pmw.OptionMenu( self.subFrame,
                                                items = m.submodes_names[i],
                                                command = self.change_submode))
        self.subbuttons[i].pack(side=LEFT, padx=(0, 2))

    # add edit pool buttons to ribbon for text-entry modes (YAML show_edit_pool)
    if getattr(m, 'show_edit_pool', False):
      # vertical separator before the button group if submodes already exist
      if self.subbuttons:
        sep = Frame(self.subFrame, width=1, bg='#b0b0b0')
        sep.pack(side=LEFT, fill='y', padx=2, pady=1)
        self._sub_extra_widgets.append(sep)
      bf = self.editPool.create_buttons(self.subFrame)
      bf.pack(side=LEFT)
      self._sub_extra_widgets.append(bf)
      # show the Entry bar
      self.editPool.grid(row=3, sticky="wens")
    else:
      # hide the Entry bar for non-editing modes
      self.editPool.grid_remove()

    # highlight the selected mode button with a thick colored border
    for btn_name in self.modes_sort:
      btn = self.radiobuttons.button(btn_name)
      if btn_name == tag:
        btn.configure(relief='sunken', borderwidth=3,
          highlightbackground='#4a90d9',
          highlightcolor='#4a90d9',
          highlightthickness=2)
      else:
        btn.configure(relief='flat', borderwidth=1,
          highlightthickness=0)

    self.paper.mode = self.mode
    #Store.log( _('mode changed to ')+self.modes[ tag].name)
    self.mode.startup()


  def change_submode( self, tag):
    self.mode.set_submode( tag)


  def _build_submode_grid(self, m, group_index, tooltip_map):
    """Build a Tk Frame with buttons arranged in a grid layout.

    Args:
      m: The current mode object.
      group_index: Index of the submode group.
      tooltip_map: Dict mapping submode keys to tooltip text.

    Returns:
      Frame: A Tk Frame containing the grid of buttons.
    """
    # get column count from YAML config
    yaml_key = type(m).__name__.replace('_mode', '')
    cfg = modes.get_modes_config()['modes'].get(yaml_key, {})
    columns = 4
    submode_groups = cfg.get('submodes', [])
    if group_index < len(submode_groups):
      columns = submode_groups[group_index].get('columns', 4)

    grid_frame = Frame(self.subFrame, relief='ridge', borderwidth=0)
    # track the selected button for this grid
    grid_frame._grid_buttons = {}
    grid_frame._grid_selected = None

    def on_grid_click(name, btn):
      """Handle grid button click -- highlight and set submode."""
      # un-highlight previous selection
      if grid_frame._grid_selected and grid_frame._grid_selected.winfo_exists():
        grid_frame._grid_selected.configure(relief='raised', bg='#d9d9d9')
      # highlight new selection
      btn.configure(relief='sunken', bg='#b0c4de')
      grid_frame._grid_selected = btn
      self.change_submode(name)

    submodes_list = m.submodes[group_index]
    names_list = m.submodes_names[group_index]
    for idx, sub in enumerate(submodes_list):
      row = idx // columns
      col = idx % columns
      display_name = names_list[idx] if idx < len(names_list) else sub
      tip_text = tooltip_map.get(sub, display_name)
      btn = Button(
        grid_frame, text=display_name,
        width=4, padx=1, pady=1,
        relief='raised', borderwidth=bkchem_config.border_width,
        font=('sans-serif', 9),
        command=lambda n=sub, b_idx=idx: on_grid_click(n, grid_frame._grid_buttons[b_idx]),
      )
      btn.grid(row=row, column=col, padx=1, pady=1)
      grid_frame._grid_buttons[idx] = btn
      self.balloon.bind(btn, tip_text)

    # auto-select first button
    if submodes_list and 0 in grid_frame._grid_buttons:
      first_btn = grid_frame._grid_buttons[0]
      first_btn.configure(relief='sunken', bg='#b0c4de')
      grid_frame._grid_selected = first_btn
      self.change_submode(submodes_list[0])

    return grid_frame


  def refresh_submode_buttons(self, group_index):
    """Rebuild the submode widget at the given group index.

    Used when the template list changes (e.g. category switch
    in biomolecule mode).

    Args:
      group_index: Index of the submode group to rebuild.
    """
    if group_index >= len(self.subbuttons):
      return
    m = self.mode
    tooltip_map = getattr(m, 'tooltip_map', {})
    # destroy existing widget
    old_widget = self.subbuttons[group_index]
    old_widget.destroy()
    # determine layout
    layout = 'row'
    if hasattr(m, 'group_layouts') and group_index < len(m.group_layouts):
      layout = m.group_layouts[group_index]
    if layout == 'grid':
      new_widget = self._build_submode_grid(m, group_index, tooltip_map)
    else:
      # rebuild as horizontal row
      new_widget = Pmw.RadioSelect(self.subFrame,
        buttontype='button', selectmode='single',
        orient='horizontal', command=self.change_submode,
        hull_borderwidth=0, padx=0, pady=0, hull_relief='ridge')
      for sub in m.submodes[group_index]:
        sub_idx = m.submodes[group_index].index(sub)
        display_name = m.submodes_names[group_index][sub_idx]
        new_widget.add(sub, text=display_name, borderwidth=bkchem_config.border_width)
      if m.submodes[group_index]:
        new_widget.invoke(m.submodes[group_index][0])
    new_widget.pack(side=LEFT, padx=(0, 2))
    self.subbuttons[group_index] = new_widget


  def update_status( self, signal, time=None):
    """if time is none it is calculated based on the string length"""
    if time is None and signal:
      time = 4 + 0.05 * len( signal)
    if signal:
      self.stat.set( signal)
      if self._after:
        self.after_cancel( self._after)
      self._after = self.after( int( time*1000), func=self.clear_status)


  def change_paper(self, name):
    if self.papers:
      old_paper = self.paper
      # de-highlighting of current tab
      if old_paper in self.papers:
        i = self.papers.index(old_paper)
        self.notebook.tab(i).configure(background=bkchem_config.background_color, fg="black")
      i = self.notebook.index( name)
      # highlighting of current tab
      self.notebook.tab( i).configure( background="#777777", fg="white")
      # the rest
      self.paper = self.papers[i]
      if (hasattr(self, 'mode') and
          not bkchem_utils.myisstr(self.mode) and
          old_paper in self.papers and
          self.paper != old_paper):
        # this is not true on startup and tab closing
        self.mode.on_paper_switch( old_paper, self.paper)


  def add_new_paper( self, name=''):
    # check if the same file is opened
    p = self.check_if_the_file_is_opened( name)
    if p:
      Store.log( _("Sorry but I cannot open the same file twice: ")+"\n"+name, message_type="error")
      return False
    name_dic = self.get_name_dic( name=name)
    # create the tab
    _tab_name = self.get_new_tab_name()
    page = self.notebook.add( _tab_name, tab_text = chem_paper.create_window_name( name_dic))
    paper = chem_paper( page,
                        scrollregion=(-100,-100,'300m','400m'),
                        background="grey",
                        closeenough=3,
                        file_name=name_dic)
    self.__tab_name_2_paper[ _tab_name] = paper
    # the scrolling
    scroll_y = Scrollbar( page, orient = VERTICAL, command = paper.yview, bd=bkchem_config.border_width)
    scroll_x = Scrollbar( page, orient = HORIZONTAL, command = paper.xview, bd=bkchem_config.border_width)
    paper.grid( row=0, column=0, sticky="news")
    page.grid_rowconfigure( 0, weight=1, minsize = 0)
    page.grid_columnconfigure( 0, weight=1, minsize = 0)
    scroll_x.grid( row=1, column=0, sticky='we')
    scroll_y.grid( row=0, column=1, sticky='ns')
    paper['yscrollcommand'] = scroll_y.set
    paper['xscrollcommand'] = scroll_x.set

    # Zoom controls at bottom of each tab page
    zoom_frame = Frame(page)
    zoom_frame.grid(row=2, column=0, columnspan=2, sticky='e')

    zoom_out_btn = Button(zoom_frame, text="\u2212", width=2, command=paper.zoom_out)
    zoom_out_btn.pack(side='left', padx=1)

    zoom_label = Label(zoom_frame, text="100%", width=5, relief=SUNKEN)
    zoom_label.pack(side='left', padx=1)

    zoom_in_btn = Button(zoom_frame, text="+", width=2, command=paper.zoom_in)
    zoom_in_btn.pack(side='left', padx=1)

    zoom_reset_btn = Button(zoom_frame, text="100%", width=4, command=paper.zoom_reset)
    zoom_reset_btn.pack(side='left', padx=2)

    zoom_fit_btn = Button(zoom_frame, text="Fit", width=3, command=paper.zoom_to_fit)
    zoom_fit_btn.pack(side='left', padx=2)

    zoom_content_btn = Button(zoom_frame, text="Content", width=6, command=paper.zoom_to_content)
    zoom_content_btn.pack(side='left', padx=2)

    def update_zoom_label(event=None, lbl=zoom_label, p=paper):
      lbl.config(text="%d%%" % int(p._scale * 100))
    paper.bind('<<zoom-changed>>', update_zoom_label)

    self.papers.append( paper)
    self.change_paper( _tab_name)
    self.notebook.selectpage( Pmw.END)
    paper.bind( "<<selection-changed>>", self.update_menu_after_selection_change)
    paper.bind( "<<clipboard-changed>>", self.update_menu_after_selection_change)
    paper.bind( "<<undo>>", self.update_menu_after_selection_change)
    paper.bind( "<<redo>>", self.update_menu_after_selection_change)
    if not self.paper:
      self.paper = paper  # this is needed for the batch mode, normaly its done in change_paper
    else:
      self.paper.focus_set()
    return True


  def close_current_paper( self, call_quit_if_no_remains=True):
    ret = self.close_paper()
    if self.papers == [] and call_quit_if_no_remains:
      self._quit()
    return ret


  def close_paper( self, paper=None):
    p = paper or self.paper
    if hasattr( self, "editPool") and self.editPool.active:
      self.editPool._cancel(None)

    if p.changes_made and not self.in_batch_mode:
      name = p.file_name['name']
      dialog = Pmw.MessageDialog( self,
                                  title= _("Really close?"),
                                  message_text = _("There are unsaved changes in file %s, what should I do?") % name,
                                  buttons = (_('Close'),_('Save'),_('Cancel')),
                                  defaultbutton = _('Close'))
      result = dialog.activate()
      if result == _('Save'):
        self.save_CDML()
      elif result == _('Cancel'):
        return 0 # we skip away
    self.papers.remove( p)

    # cleanup
    # find the name of the tab
    name = self.get_paper_tab_name( p)
    del self.__tab_name_2_paper[ name]
    p.mrproper()
    self.notebook.delete( name or Pmw.SELECT)
    return 1


  def clear_status( self):
    self.stat.set( '')


  def save_CDML( self, name=None, update_default_dir=1):
    """saves content of self.paper (recent paper) under its filename,
    if the filename was automaticaly given by bkchem it will call save_as_CDML
    in order to ask for the name"""
    if not name:
      if self.paper.file_name['auto']:
        self.save_as_CDML()
        return
      else:
        a = os.path.join( self.paper.file_name['dir'], self.paper.file_name['name'])
        return self._save_according_to_extension( a, update_default_dir=update_default_dir)
    else:
      return self._save_according_to_extension( name, update_default_dir=update_default_dir)


  def save_as_CDML( self):
    """asks the user the name for a file and saves the current paper there,
    dir and name should be given as starting values"""
    d = self.paper.file_name['dir']
    name = self.paper.file_name['name']
    a = asksaveasfilename( defaultextension = ".svg", initialdir = d, initialfile = name,
                           title = _("Save As..."), parent = self,
                           filetypes=((_("CD-SVG file"),".svg"),
                                      (_("Gzipped CD-SVG file"),".svgz"),
                                      (_("CDML file"),".cdml"),
                                      (_("Gzipped CDML file"),".cdgz")))
    if a != '' and a!=():
      if self._save_according_to_extension( a):
        name = self.get_name_dic( a)
        if self.check_if_the_file_is_opened( name['name'], check_current=0):
          tkinter.messagebox.showerror( _("File already opened!"), _("Sorry but you are already editing a file with this name (%s), please choose a different name or close the other file.") % name['name'])
          return None
        self.paper.file_name = self.get_name_dic( a)
        self.notebook.tab( self.get_paper_tab_name( self.paper)).configure( text = self.paper.file_name['name'])
        return self.paper.file_name
      else:
        return None
    else:
      return None


  def _save_according_to_extension( self, filename, update_default_dir=1):
    """decides the format from the file extension and saves self.paper in it"""
    save_dir, save_file = os.path.split( filename)
    if update_default_dir:
      self.save_dir = save_dir
    ext = os.path.splitext( filename)[1]
    if ext == '.cdgz':
      type = _('gzipped CDML')
      success = export.export_CDML( self.paper, filename, gzipped=1)
    elif ext == '.cdml':
      type = _('CDML')
      success = export.export_CDML( self.paper, filename, gzipped=0)
    elif ext == '.svgz':
      type = _('gzipped CD-SVG')
      success = export.export_CD_SVG( self.paper, filename, gzipped=1)
    else:
      type = _('CD-SVG')
      success = export.export_CD_SVG( self.paper, filename, gzipped=0)
    if success:
      Store.log( _("saved to %s file: %s") % (type, os.path.abspath( os.path.join( save_dir, save_file))))
      self._record_recent_file( os.path.abspath( os.path.join( save_dir, save_file)))
      self.paper.changes_made = 0
      return 1
    else:
      Store.log( _("failed to save to %s file: %s") % (type, save_file))
      return 0


  def set_file_name( self, name, check_ext=0):
    """if check_ext is true append a .svg extension if no is present"""
    if check_ext and not os.path.splitext( name)[1]:
      self.paper.file_name = self.get_name_dic( name + ".svg", local_file=1)
    else:
      self.paper.file_name = self.get_name_dic( name, local_file=1)
    self.notebook.tab( self.get_paper_tab_name( self.paper)).configure( text = self.paper.file_name['name'])


  def load_CDML( self, file=None, replace=0):
    """loads a file into a new paper or the current one (depending on replace value),
    file is the name of the file to load (if not supplied dialog is fired),
    if replace == 0 the content of the file is added to the current content of the file"""
    if not file:
      if self.paper.changes_made and replace:
        if tkinter.messagebox.askokcancel( _("Forget changes?"),_("Forget changes in currently visiting file?"), default='ok', parent=self) == 0:
          return 0
      a = askopenfilename( defaultextension = "",
                           initialdir = self.save_dir,
                           title = _("Load"),
                           parent = self,
                           filetypes=((_("All native formats"), (".svg", ".svgz", ".cdml", ".cdgz")),
                                      (_("CD-SVG file"), ".svg"),
                                      (_("Gzipped CD-SVG file"), ".svgz"),
                                      (_("CDML file"),".cdml"),
                                      (_("CDGZ file"),".cdgz"),
                                      (_("Gzipped files"), ".gz"),
                                      (_("All files"),"*")))
    else:
      a = file
    if not a:
      return None
    if self.papers and (replace or (self.paper.file_name['auto'] and not self.paper.changes_made)):
      self.close_paper()
    p = self.add_new_paper( name=a)
    if p != 0:
      self.paper.mode = self.mode # somehow the raise event does not work here
      return self._load_CDML_file( a)
    return 0


  def _load_CDML_file( self, a, draw=True):
    if a != '':
      self.save_dir, save_file = os.path.split( a)
      ## try if the file is gzipped
      # try to open the file
      try:
        import gzip
        inp = gzip.open( a, "rb")
      except IOError:
        # can't read the file
        Store.log( _("cannot open file ") + a)
        return None
      # is it a gzip file?
      it_is_gzip = 1
      try:
        s = inp.read()
      except IOError:
        # not a gzip file
        it_is_gzip = 0
      # if it's gzip file parse it
      if it_is_gzip:
        try:
          doc = safe_xml.parse_dom_from_string( s)
        except:
          Store.log( _("error reading file"))
          inp.close()
          return None
        inp.close()
        del gzip
        doc = [n for n in doc.childNodes if n.nodeType == doc.ELEMENT_NODE][0]
      else:
      ## otherwise it should be normal xml file
        ## try to parse it
        try:
          doc = safe_xml.parse_dom_from_file( a)
        except IndexError:
          Store.log( _("error reading file"))
          return None
        ## if it works check if its CDML of CD-SVG file
        doc = [n for n in doc.childNodes if n.nodeType == doc.ELEMENT_NODE][0]
      ## check if its CD-SVG or CDML
      if doc.nodeName != 'cdml':
        ## first try if there is the right namespace
        if hasattr( doc, 'getElementsByTagNameNS'):
          docs = doc.getElementsByTagNameNS( data.cdml_namespace, 'cdml')
        else:
          Store.log( _("File was not loaded"), message_type="error")
          return None  # I don't know why this happens, but we simply ignore the document
        if docs:
          doc = docs[0]
        else:
          # if not, try it without it
          docs = doc.getElementsByTagName( 'cdml')
          if docs:
            # ask if we should proceed with incorrect namespace
            proceed = tkinter.messagebox.askokcancel(_("Proceed?"),
                                               _("CDML data seem present in SVG but have wrong namespace. Proceed?"),
                                               default='ok',
                                               parent=self)
            if proceed:
              doc = docs[0]
            else:
              Store.log(_("file not loaded"))
              return None
          else:
            ## sorry but there is no cdml in the svg file
            Store.log(_("cdml data are not present in SVG or are corrupted!"))
            return None
      self.paper.clean_paper()
      self.paper.read_package( doc, draw=draw)
      if not bkchem_utils.myisstr(self.mode):
        self.mode.startup()
      Store.log( _("loaded file: ")+self.paper.full_path)
      self._record_recent_file( os.path.abspath( self.paper.full_path))
      return 1


  def save_SVG( self, file_name=None):
    return self.format_export( "svg", filename=file_name)


  def _update_geometry( self, e):
    pass


  def scale( self):
    dialog = dialogs.scale_dialog( self)
    if dialog.result:
      x, y = dialog.result
      self.paper.scale_selected( x/100,
                                 y/100,
                                 fix_centers=dialog.preserve_centers.get(),
                                 scale_font=dialog.scale_fonts.get())


  def get_name_dic( self, name='', local_file=0):
    if not name:
      while 1:
        name = 'untitled%d.svg' % self._untitled_counter
        self._untitled_counter += 1
        if not self.check_if_the_file_is_opened( name):
          break
      name_dic = {'name':name, 'dir':self.save_dir, 'auto': 1, 'ord': 0}
    else:
      d, name = os.path.split(name)
      if not d and not local_file:
        d = self.save_dir
      elif not d:
        # the file should be in the local directory
        d = "./"
      name_dic = {'name': name, 'dir': d, 'auto': 0, 'ord': 0}
      i = self.check_number_of_opened_same_names( name_dic)
      name_dic['ord'] = i
    return name_dic


  def _quit( self):
    while self.papers:
      if not self.close_current_paper( call_quit_if_no_remains=False):
        return
    if not self.in_batch_mode:
      # we dont save configuration if we are in batch mode
      # this leads to window having size 0x0 and similar problems
      if self.svg_dir:
        if self.save_dir is not None:
            Store.pm.add_preference( "default-dir", os.path.abspath( self.save_dir))
      i = 0
      # save recent files
      for name in self._recent_files:
        i += 1
        Store.pm.add_preference( "recent-file%d" % i, name)
      self.save_configuration()
    self.quit()
    if os.name != "nt":
      sys.exit(0)


  def _format_filetypes( self, format_name, extensions):
    types = []
    for ext in extensions:
      types.append( (format_name+" "+_("file"), ext))
    types.append( (_("All files"), "*"))
    return types


  def format_import( self, codec_name, filename=None):
    entry = self.format_entries.get( codec_name)
    if not entry:
      return 0
    if not filename:
      if self.paper.changes_made:
        if tkinter.messagebox.askokcancel(
            _("Forget changes?"),
            _("Forget changes in currently visiting file?"),
            default='ok',
            parent=self) == 0:
          return 0
      types = self._format_filetypes( entry["display_name"], entry.get("extensions", []))
      a = askopenfilename( defaultextension = "",
                           initialdir = self.save_dir,
                           initialfile = self.save_file,
                           title = _("Load")+" "+entry["display_name"],
                           parent = self,
                           filetypes=types)
      if a:
        filename = a
      else:
        return 0
    try:
      mols = format_loader.import_format( codec_name, self.paper, filename)
    except Exception as detail:
      tkinter.messagebox.showerror(
        _("Import error"),
        _("Format import failed with following error:\n %s") % detail)
      return 0
    self.paper.clean_paper()
    self.paper.create_background()
    for m in mols:
      self.paper.stack.append( m)
      m.draw()
    self.paper.add_bindings()
    self.paper.start_new_undo_record()
    Store.log( _("loaded file: ")+filename)
    return 1


  def format_export( self, codec_name, filename=None, interactive=True, on_begin_attrs=None):
    _ = interactive
    _ = on_begin_attrs
    entry = self.format_entries.get( codec_name)
    if not entry:
      return False
    if not filename:
      file_name = self.paper.get_base_name()
      extensions = entry.get("extensions", [])
      if extensions:
        file_name += extensions[0]
      types = self._format_filetypes( entry["display_name"], extensions)
      defaultextension = ""
      if len( types) > 1:
        defaultextension = types[0][1]
      a = asksaveasfilename( defaultextension = defaultextension,
                             initialdir = self.save_dir,
                             initialfile = file_name,
                             title = _("Export")+" "+entry["display_name"],
                             parent = self,
                             filetypes=types)
    else:
      a = filename
    if not a:
      return False
    try:
      format_loader.export_format(
        codec_name,
        self.paper,
        a,
        entry.get("scope", "paper"),
        entry.get("gui_options", []),
      )
    except ValueError as error:
      text = str( error)
      if text == "No molecule selected.":
        tkinter.messagebox.showerror(
          _("No molecule selected."),
          _('You have to select exactly one molecule (any atom or bond will do).'))
      elif text.endswith("molecules selected."):
        tkinter.messagebox.showerror(
          text,
          _('You have to select exactly one molecule (any atom or bond will do).'))
      elif text.startswith("Missing required option 'program_path'"):
        tkinter.messagebox.showerror(
          _("InChI program path"),
          _("To use InChI in BKChem you must first give it a path to the InChI program here"))
      else:
        tkinter.messagebox.showerror(
          _("Export error"),
          _("Format export failed with following error:\n %s") % error)
      return False
    except Exception as error:
      tkinter.messagebox.showerror(
        _("Export error"),
        _("Format export failed with following error:\n %s") % error)
      return False
    Store.log( _("exported file: ")+a)
    return True


  def plugin_import( self, pl_id, filename=None):
    plugin = self.plugins[ pl_id]
    if not filename:
      if self.paper.changes_made:
        if tkinter.messagebox.askokcancel( _("Forget changes?"),_("Forget changes in currently visiting file?"), default='ok', parent=self) == 0:
          return 0
      types = []
      if 'extensions' in plugin.__dict__ and plugin.extensions:
        for e in plugin.extensions:
          types.append( (plugin.name+" "+_("file"), e))
      types.append( (_("All files"),"*"))
      a = askopenfilename( defaultextension = "",
                           initialdir = self.save_dir,
                           initialfile = self.save_file,
                           title = _("Load")+" "+plugin.name,
                           parent = self,
                           filetypes=types)
      if a:
        filename = a
      else:
        return 0
    # we have filename already
    if plugin.importer.gives_molecule:
      # plugins returning molecule need paper instance for molecule initialization
      importer = plugin.importer( self.paper)
    else:
      importer = plugin.importer()
    if importer.on_begin():
      cdml = None
      # some importers give back a cdml dom object
      if importer.gives_cdml:
        cdml = 1
        try:
          doc = importer.get_cdml_dom( filename)
        except plugins.plugin.import_exception as detail:
          tkinter.messagebox.showerror(_("Import error"), _("Plugin failed to import with following error:\n %s") % detail)
          return 0
      # others give directly a molecule object
      elif importer.gives_molecule:
        cdml = 0
        try:
          doc = importer.get_molecules( filename)
        except plugins.plugin.import_exception as detail:
          tkinter.messagebox.showerror(_("Import error"), _("Plugin failed to import with following error:\n %s") % detail)
      self.paper.clean_paper()
      if cdml == 0:
        # doc is a molecule
        self.paper.create_background()
        for m in doc:
          self.paper.stack.append( m)
          m.draw()
        self.paper.add_bindings()
        self.paper.start_new_undo_record()
      elif cdml:
        self.paper.read_package( doc)

      Store.log( _("loaded file: ")+filename)
      return 1


  def plugin_export( self, pl_id, filename=None, interactive=True, on_begin_attrs=None):
    """interactive attribute tells whether the plugin should be run in interactive mode"""
    plugin = self.plugins[ pl_id]
    exporter = plugin.exporter( self.paper)
    exporter.interactive = interactive and not self.in_batch_mode
    attrs = on_begin_attrs or {}
    if not exporter.on_begin( **attrs):
      return False
    if not filename:
      file_name = self.paper.get_base_name()
      types = []
      if 'extensions' in plugin.__dict__ and plugin.extensions:
        file_name += plugin.extensions[0]
        for e in plugin.extensions:
          types.append( (plugin.name+" "+_("file"), e))
      types.append( (_("All files"),"*"))

      a = asksaveasfilename( defaultextension = types[0][1],
                             initialdir = self.save_dir,
                             initialfile = file_name,
                             title = _("Export")+" "+plugin.name,
                             parent = self,
                             filetypes=types)
    else:
      a = filename
    if a:
      if not bkchem_config.debug:
        try:
          exporter.write_to_file( a)
        except Exception as error:
          tkinter.messagebox.showerror(_("Export error"), _("Plugin failed to export with following error:\n %s") % error)
          return False
      else:
        exporter.write_to_file( a)
      Store.log( _("exported file: ")+a)
      return True
    return False


  def change_properties( self):
    dialogs.file_properties_dialog( self, self.paper)


  def standard_values( self):
    dial = dialogs.standard_values_dialog( self, self.paper.standard)
    if dial.change:
      old_standard = self.paper.standard
      self.paper.standard = dial.standard
      # apply all values or only the changed ones
      if dial.apply_all:
        old_standard = None
      if not dial.apply:
        return
      elif dial.apply == 2:
        [o.redraw() for o in self.paper.apply_current_standard( old_standard=old_standard)]
      elif dial.apply == 1:
        [o.redraw() for o in self.paper.apply_current_standard( objects=self.paper.selected, old_standard=old_standard)]
      self.paper.add_bindings()
      self.paper.start_new_undo_record()


  def request( self, type, **options):
    """used by submodules etc. for requests of application wide resources such as pixmaps etc."""
    if type == 'pixmap':
      if 'name' in options:
        name = options['name']
        if name in pixmaps.images:
          return pixmaps.images[ name]
        else:
          return None
      return None


  def read_smiles( self, smiles=None):
    if not oasa_bridge.oasa_available:
      return
    lt = _("Enter a SMILES or IsoSMILES string:")
    if not smiles:
      dial = Pmw.PromptDialog( self,
                               title='SMILES',
                               label_text=lt,
                               entryfield_labelpos = 'n',
                               buttons=(_('OK'),_('Cancel')))
      res = dial.activate()
      if res == _('OK'):
        text = dial.get()
      else:
        return
    else:
      text = smiles

    if text:
      # route through CDML: SMILES -> OASA -> CDML element -> BKChem import
      self.paper.onread_id_sandbox_activate()
      elements = oasa_bridge.smiles_to_cdml_elements( text, self.paper)
      imported = []
      for element in elements:
        mol = self.paper.add_object_from_package( element)
        imported.append( mol)
        mol.draw()
      self.paper.onread_id_sandbox_finish( apply_to=imported)
      self.paper.add_bindings()
      self.paper.start_new_undo_record()
      if len( imported) == 1:
        return imported[0]
      return imported


  def read_peptide_sequence( self):
    if not oasa_bridge.oasa_available:
      return
    # get supported amino acid letters from OASA for the dialog prompt
    from oasa.peptide_utils import AMINO_ACID_SMILES
    supported = sorted(AMINO_ACID_SMILES.keys())
    supported_str = ', '.join(supported)
    lt = _("Enter a single-letter amino acid sequence (e.g. ANKLE):\n"
           "Supported: %s") % supported_str
    dial = Pmw.PromptDialog( self,
                             title=_('Peptide Sequence'),
                             label_text=lt,
                             entryfield_labelpos = 'n',
                             buttons=(_('OK'),_('Cancel')))
    res = dial.activate()
    if res != _('OK'):
      return
    text = dial.get()
    if not text or not text.strip():
      return
    # validate input letters before sending to OASA
    sequence = text.strip().upper()
    bad_letters = [aa for aa in sequence if aa not in AMINO_ACID_SMILES]
    if bad_letters:
      tkinter.messagebox.showerror(
        _("Peptide Sequence Error"),
        _("Unrecognized amino acid code(s): %s\n"
          "Supported: %s") % (', '.join(sorted(set(bad_letters))), supported_str))
      return
    # delegate to OASA via bridge: peptide -> SMILES -> CDML
    try:
      elements = oasa_bridge.peptide_to_cdml_elements( sequence, self.paper)
    except ValueError as err:
      tkinter.messagebox.showerror(
        _("Peptide Sequence Error"), str(err))
      return
    # import the CDML elements onto the canvas
    self.paper.onread_id_sandbox_activate()
    imported = []
    for element in elements:
      mol = self.paper.add_object_from_package( element)
      imported.append( mol)
      mol.draw()
    self.paper.onread_id_sandbox_finish( apply_to=imported)
    self.paper.add_bindings()
    self.paper.start_new_undo_record()
    if len( imported) == 1:
      return imported[0]
    return imported


  def read_inchi( self, inchi=None):
    if not oasa_bridge.oasa_available:
      return
    lt = _("""Before you use his tool, be warned that not all features of InChI are currently supported.
There is no support for stereo-related information, isotopes and a few more things.
The InChI should be entered in the plain text form, e.g.- 1/C7H8/1-7-5-3-2-4-6-7/1H3,2-6H

Enter InChI:""")
    text = None
    if not inchi:
      dial = Pmw.PromptDialog( self,
                               title='InChI',
                               label_text=lt,
                               entryfield_labelpos = 'n',
                               buttons=(_('OK'),_('Cancel')))
      res = dial.activate()
      if res == _('OK'):
        text = dial.get()
    else:
      text = inchi

    if text:
      if bkchem_config.devel:
        # in development mode we do not want to catch the exceptions
        mol = oasa_bridge.read_inchi( text, self.paper)
      else:
        try:
          mol = oasa_bridge.read_inchi( text, self.paper)
        except oasa.oasa_exceptions.oasa_not_implemented_error as error:
          if not inchi:
            tkinter.messagebox.showerror(_("Error processing %s") % 'InChI',
                                   _("Some feature of the submitted InChI is not supported.\n\nYou have most probaly submitted a multicomponent structure (having a . in the sumary layer"))
            return
          else:
            raise ValueError("the processing of inchi failed with following error %s" % error)
        except oasa.oasa_exceptions.oasa_inchi_error as error:
          if not inchi:
            tkinter.messagebox.showerror(_("Error processing %s") % 'InChI',
                                   _("There was an error reading the submitted InChI.\n\nIf you are sure it is a valid InChI, please send me a bug report."))
            return
          else:
            raise ValueError("the processing of inchi failed with following error %s" % error)
        except oasa.oasa_exceptions.oasa_unsupported_inchi_version_error as e:
          if not inchi:
            tkinter.messagebox.showerror(_("Error processing %s") % 'InChI',
                                   _("The submitted InChI has unsupported version '%s'.\n\nYou migth try resubmitting with the version string (the first part of InChI) changed to '1'.") % e.version)
            return
          else:
            raise ValueError("the processing of inchi failed with following error %s" % sys.exc_info()[1])
        except:

          if not inchi:
            tkinter.messagebox.showerror(_("Error processing %s") % 'InChI',
                                   _("The reading of InChI failed with following error:\n\n'%s'\n\nIf you are sure you have submitted a valid InChI, please send me a bug report.") % sys.exc_info()[1])
            return
          else:
            raise ValueError("the processing of inchi failed with following error %s" % sys.exc_info()[1])

      self.paper.stack.append( mol)
      mol.draw()
      self.paper.add_bindings()
      self.paper.start_new_undo_record()


  def gen_smiles(self):
    if not oasa_bridge.oasa_available:
      return
    u, i = self.paper.selected_to_unique_top_levels()
    if not interactors.check_validity(u):
      return
    sms = []
    for m in u:
      if m.object_type == 'molecule':
        sms.append(oasa_bridge.mol_to_smiles(m))
    text = '\n\n'.join(sms)
    dial = Pmw.TextDialog(self,
                          title=_('Generated SMILES'),
                          buttons=(_('OK'),))
    dial.insert('end', text)
    dial.activate()


  def put_to_clipboard( self, xml, pos):
    self._clipboard = xml
    self._clipboard_pos = pos


  def get_clipboard( self):
    return self._clipboard


  def get_clipboard_pos( self):
    return self._clipboard_pos


  def check_if_the_file_is_opened( self, name, check_current=1):
    """check_current says if the self.paper should be also included into the check,
    this is usefull to make it 0 for renames"""
    for p in self.papers:
      if not check_current and p == self.paper:
        continue
      if p.full_path == os.path.abspath( name):
        return p
    return None


  def check_number_of_opened_same_names( self, name):
    """checks if there are papers with same name and returns the highest value"""
    ps = [p.file_name['ord'] for p in self.papers if p.file_name['name'] == name['name']]
    if not ps:
      return 0
    else:
      return max( ps)+1


  def get_new_tab_name( self):
    self.__last_tab += 1
    return "tab"+str(self.__last_tab)


  def get_paper_tab_name( self, paper):
    for k in self.__tab_name_2_paper:
      if self.__tab_name_2_paper[ k] == paper:
        return k
    return None


  def read_user_templates( self):
    [Store.utm.add_template_from_CDML( n) for n in os_support.get_local_templates()]


  def read_biomolecule_templates( self):
    from bkchem import biomolecule_loader
    entries = biomolecule_loader.load_biomolecule_entries()
    for entry in entries:
      Store.btm.register_smiles_template(
        entry['smiles'], name_override=entry['name']
      )


  def gen_inchi( self):
    program = Store.pm.get_preference( "inchi_program_path")
    self.paper.swap_sides_of_selected("horizontal")
    if not oasa_bridge.oasa_available:
      return
    u, i = self.paper.selected_to_unique_top_levels()
    sms = []
    if not interactors.check_validity( u):
      return

    try:
      for m in u:
        if m.object_type == 'molecule':
            inchi, key, warning = oasa_bridge.mol_to_inchi( m, program)
            sms = sms + warning
            sms.append(inchi)
            sms.append("InChIKey="+key)
            sms.append("")
    except oasa.oasa_exceptions.oasa_inchi_error as e:
      sms = [_("InChI generation failed,"),_("make sure the path to the InChI program is correct in 'Options/InChI program path'"), "", str( e)]
    except:
      sms = [_("Unknown error occured during InChI generation, sorry."), _("Please, try to make sure the path to the InChI program is correct in 'Options/InChI program path'")]
    self.paper.swap_sides_of_selected("horizontal")
    text = '\n'.join( sms)
    dial = Pmw.TextDialog( self,
                           title=_('Generated InChIs'),
                           buttons=(_('OK'),))
    dial.insert( 'end', text)
    dial.activate()


  def save_configuration( self):
    Store.pm.add_preference( 'geometry', self.winfo_geometry())
    # store logging settings
    if not self.in_batch_mode:
      # we do not save (or load) handling info when in batch mode
      for key, value in list(Store.logger.handling.items()):
        Store.pm.add_preference("logging_%s" % key, value)
    f = os_support.get_opened_config_file("prefs.xml",
                                          level="personal",
                                          mode="wb")
    if f:
      Store.pm.write_to_file( f)
      f.close()
    else:
      print("Error: Failed to open prefs.xml file.")


  def run_plugin( self, name):
    p = self.paper
    self.plug_man.run_plugin( name)
    if p == self.paper:
      # we update bindings and start_new_undo_record only if the paper did not change during the run
      self.paper.add_bindings()
      self.paper.start_new_undo_record()


  def save_as_template( self):
    name = interactors.save_as_template( self.paper)
    if name:
      self.save_CDML( name=name, update_default_dir=0)
      Store.log( _("The file was saved as a template %s") % name)


  def insert_biomolecule_template( self):
    if not Store.btm or not Store.btm.get_template_names():
      Store.log( _("No biomolecule templates are available"))
      return
    if hasattr( self, 'radiobuttons') and 'biotemplate' in self.modes_sort:
      self.radiobuttons.invoke( 'biotemplate')
    else:
      self.change_mode( 'biotemplate')


  def clean( self):
    self.paper.clean_selected()


  def update_cursor_position( self, x, y):
    self.cursor_position.set( "(%d, %d)" % (x,y))


  #============================================
  def _get_menu_component( self, name):
    """Return the tkinter.Menu component for the given menu name."""
    if getattr( self, '_use_system_menubar', False):
      return self.menu.component( name)
    return self.menu.component( name + "-menu")


  def update_menu_after_selection_change( self, e):
    for temp in self.menu_template:
      if temp[1] == "command" and temp[6] is not None:
        state = temp[6]
        #print(temp)
        #print(state)
        if isinstance(state, collections.abc.Callable):
          state = state() and 'normal' or 'disabled'
        elif state not in  ('normal', 'disabled'):
          state = getattr( self.paper, temp[6]) and 'normal' or 'disabled'
        self._get_menu_component( temp[0]).entryconfigure( temp[2], state=state)


  def _record_recent_file( self, name):
    if name in self._recent_files:
      self._recent_files.remove( name)
    self._recent_files.insert( 0, name)
    if len( self._recent_files) > 5:
      self._recent_files = self._recent_files[0:5]


  def ask_preferences( self):
    pd = dialogs.preferences_dialog( self, Store.pm)
    if pd.result == 1:
      for i in self.papers:
        i._paper_properties['use_real_minus'] = Store.pm.get_preference("use_real_minus")
        [j.redraw() for j in i.stack]


  ## ------------------------------ THE BATCH MODE ------------------------------
  def process_batch( self, opts):

    if opts[0] == "-b":
      plugin_path = opts[1]

      the_globals = {'App': Store.app,
                     'Args': opts[2:]}

      with open(plugin_path) as f:
        code = compile(f.read(), plugin_path, 'exec')
        exec(code, the_globals)  # nosec B102 - explicit batch script execution
