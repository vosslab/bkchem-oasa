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

from tkinter import Button, Frame, Label, StringVar, Tk
from tkinter import LEFT, RAISED, SUNKEN

import Pmw
from bkchem import bkchem_utils
from bkchem.modes.mode_loader import build_all_modes
from bkchem.modes.config import get_toolbar_order, get_toolbar_separator_positions
from bkchem import bkchem_config
from bkchem import logger
from bkchem import dialogs
from bkchem import pixmaps
from bkchem import format_loader
from bkchem import messages
from bkchem import molecule_lib
from bkchem import os_support
from bkchem import interactors
from bkchem.edit_pool import editPool
from bkchem.id_manager import id_manager
from bkchem.temp_manager import template_manager
from bkchem.singleton_store import Store, Screen

from bkchem.main_lib.main_file_io import MainFileIOMixin
from bkchem.main_lib.main_chemistry_io import MainChemistryIOMixin
from bkchem.main_lib.main_modes import MainModesMixin
from bkchem.main_lib.main_tabs import MainTabsMixin
from bkchem import theme_manager

# gettext i18n translation fallback
_ = builtins.__dict__.get( '_', lambda m: m)


#============================================
def _on_btn_enter(btn, default_bg):
	"""Highlight a toolbar button on mouse hover."""
	# skip hover tint if button is the active (selected) mode
	if str(btn.cget('background')) == theme_manager.get_color('active_mode'):
		return
	btn.configure(background=theme_manager.get_color('hover'))


#============================================
def _on_btn_leave(btn, default_bg):
	"""Restore a toolbar button background when mouse leaves."""
	# keep active mode fill when leaving
	if str(btn.cget('background')) == theme_manager.get_color('active_mode'):
		return
	btn.configure(background=default_bg)


class BKChem(
	MainTabsMixin,
	MainModesMixin,
	MainChemistryIOMixin,
	MainFileIOMixin,
	Tk,
):

	def __init__( self):
		Tk.__init__( self)
		# setting the singleton values
		Store.app = self
		Screen.dpi = self.winfo_fpixels( "1i")

		self.tk.call("tk", "useinputmethods", "1")
		#self.tk.call( "encoding", "system", "iso8859-2")
		#print(self.tk.call( "encoding", "system"))
		# load theme preference from persisted prefs (if available)
		# this sets the module-level active theme before any color lookups
		theme_manager.get_active_theme_name()
		#self.option_add( "*Background", "#eaeaea")
		self.option_add( "*Entry*Background", theme_manager.get_color('entry_bg'))
		self.option_add( "*Entry*Foreground", theme_manager.get_color('entry_fg'))
		self.tk_setPalette( "background", theme_manager.get_color('background'),
												"insertBackground", theme_manager.get_color('entry_insert_bg'))

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
		self.editPool.grid( row=4, sticky="wens")
		self.editPool.grid_remove()

		# main drawing part packing
		self.notebook.grid( row=5, sticky="wens")
		self.notebook.setnaturalsize()


		# preferences
		self.init_preferences()

		# init status bar
		self.init_status_bar()

		#
		self.invoke_mode( self.mode)

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
		self.notebook.grid( row=5, sticky="wens")

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
			( _("Options"), 'command', _('Theme'), None, _("Switch between light and dark color themes"), lambda: self._show_theme_dialog(), None),
			( _("Options"), 'separator'),
			( _("Options"), 'command', _('Preferences'), None, _("Preferences"), self.ask_preferences, None),

			# help menu
			( _('Help'), 'menu', _("Help and information about the program"), "right"),
			( _("Help"), 'command', _('About'), None, _("General information about BKChem"), self.about, None),

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
		self.mode_name_var = StringVar()
		self.zoom_var = StringVar()
		self.stat.set( "Idle")
		self.zoom_var.set( "100%")
		self.save_dir = '.'
		self.save_file = None
		self.svg_dir = '.'
		self.svg_file = ''
		self._recent_files = []

		self._clipboard = None
		self._clipboard_pos = None

		self._untitled_counter = 0
		self._tab_name_2_paper = {}
		self._last_tab = 0

		self._after = None

		self.balloon = Pmw.Balloon( self)
		self.menu_balloon = Pmw.Balloon( self, statuscommand=self.update_status)
		self.main_frame = Frame( self)
		self.main_frame.pack( fill='both', expand=1)
		self.main_frame.rowconfigure( 5, weight=1)
		self.main_frame.columnconfigure( 0, weight=1)

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
		self.modes = build_all_modes()
		self.modes_sort = get_toolbar_order()



	def init_mode_buttons( self):
		# mode selection panel with slightly darker background for visual hierarchy
		_toolbar_bg = theme_manager.get_color('toolbar')
		_btn_active_bg = theme_manager.get_color('button_active_bg')
		_group_sep_color = theme_manager.get_color('group_separator')
		radioFrame = Frame( self.main_frame, bg=_toolbar_bg)
		radioFrame.grid( row=1, sticky='we')
		# build toolbar as separate RadioSelect widgets per group with
		# separator frames between them; Pmw.RadioSelect uses grid internally
		# so we cannot pack separator frames inside it
		sep_positions = set(get_toolbar_separator_positions())
		# split mode list into groups at separator positions
		groups = []
		current_group = []
		for idx, m in enumerate(self.modes_sort):
			if idx in sep_positions and current_group:
				groups.append(current_group)
				current_group = []
			current_group.append(m)
		if current_group:
			groups.append(current_group)
		# shared command that dispatches to change_mode and selects across groups
		self._radio_groups = []
		for gi, group in enumerate(groups):
			# thin separator line between groups
			if gi > 0:
				sep = Frame(radioFrame, width=1, bg=_group_sep_color)
				sep.pack(side=LEFT, fill='y', padx=3, pady=2)
			radio = Pmw.RadioSelect(radioFrame,
															buttontype='button',
															selectmode='single',
															orient='horizontal',
															command=self.change_mode,
															hull_borderwidth=0,
															padx=1,
															pady=1,
															hull_relief='flat')
			radio.pack(side=LEFT)
			# match hull background to toolbar band
			radio.configure(hull_background=_toolbar_bg)
			self._radio_groups.append(radio)
			for m in group:
				if m in pixmaps.images:
					recent = radio.add(m, image=pixmaps.images[m], text=self.modes[m].label,
														compound='top', activebackground=_btn_active_bg,
														background=_toolbar_bg,
														relief='flat', borderwidth=bkchem_config.border_width)
					self.balloon.bind(recent, self.modes[m].name)
				else:
					recent = radio.add(m, text=self.modes[m].label,
														activebackground=_btn_active_bg,
														background=_toolbar_bg,
														borderwidth=bkchem_config.border_width)
				# hover effect: lighten background on mouse enter, restore on leave
				recent.bind('<Enter>', lambda e, btn=recent, bg=_toolbar_bg: _on_btn_enter(btn, bg))
				recent.bind('<Leave>', lambda e, btn=recent, bg=_toolbar_bg: _on_btn_leave(btn, bg))
		# build mode-name-to-group lookup for cross-group button access
		self._mode_to_group = {}
		for radio in self._radio_groups:
			for btn_name in radio._buttonList:
				self._mode_to_group[btn_name] = radio
		# undo/redo buttons on the right side of the toolbar
		sep = Frame(radioFrame, width=1, bg=_group_sep_color)
		sep.pack(side=LEFT, fill='y', padx=4, pady=2)
		# undo button
		undo_kwargs = {'text': _('Undo'), 'command': lambda: self.paper.undo(),
									'relief': 'flat', 'borderwidth': bkchem_config.border_width,
									'activebackground': _btn_active_bg, 'background': _toolbar_bg}
		if 'undo' in pixmaps.images:
			undo_kwargs['image'] = pixmaps.images['undo']
			undo_kwargs['compound'] = 'top'
		self._undo_btn = Button(radioFrame, **undo_kwargs)
		self._undo_btn.pack(side=LEFT, padx=1)
		self.balloon.bind(self._undo_btn, _('Undo (C-z)'))
		# redo button
		redo_kwargs = {'text': _('Redo'), 'command': lambda: self.paper.redo(),
									'relief': 'flat', 'borderwidth': bkchem_config.border_width,
									'activebackground': _btn_active_bg, 'background': _toolbar_bg}
		if 'redo' in pixmaps.images:
			redo_kwargs['image'] = pixmaps.images['redo']
			redo_kwargs['compound'] = 'top'
		self._redo_btn = Button(radioFrame, **redo_kwargs)
		self._redo_btn.pack(side=LEFT, padx=1)
		self.balloon.bind(self._redo_btn, _('Redo (C-S-z)'))

		# horizontal separator between toolbar and submode ribbon
		sep_top = Frame( self.main_frame, height=1, bg=theme_manager.get_color('separator'))
		sep_top.grid( row=2, sticky='we')

		# sub-mode support
		self.subFrame = Frame( self.main_frame)
		self.subFrame.grid( row=3, sticky='we')
		self.subbuttons = []
		# the remaining of sub modes support is now in self.change_mode


	def invoke_mode( self, mode_name_or_index):
		"""Invoke a toolbar mode button by name or global index.

		Looks up the correct RadioSelect group and invokes the button
		within that group.

		Args:
			mode_name_or_index: mode name string or integer index into modes_sort
		"""
		if isinstance(mode_name_or_index, int):
			# convert global index to mode name
			if mode_name_or_index < len(self.modes_sort):
				mode_name_or_index = self.modes_sort[mode_name_or_index]
			else:
				return
		name = str(mode_name_or_index)
		group = self._mode_to_group.get(name)
		if group:
			group.invoke(name)


	def get_mode_button( self, mode_name):
		"""Return the Tk Button widget for the given mode name.

		Args:
			mode_name: mode name string

		Returns:
			Tk Button widget
		"""
		group = self._mode_to_group.get(mode_name)
		if group:
			return group.button(mode_name)
		return None


	def init_status_bar( self):
		status_frame = Frame( self.main_frame)
		status_frame.grid( row=6, sticky="we")
		# status message (expanding)
		status = Label( status_frame, relief=SUNKEN, bd=bkchem_config.border_width, textvariable=self.stat, anchor='w', height=2, justify='l')
		status.pack( side="left", expand=1, fill="both")
		# active mode name
		mode_label = Label( status_frame, relief=SUNKEN, bd=bkchem_config.border_width, textvariable=self.mode_name_var, anchor='center', width=20, height=2)
		mode_label.pack( side="left")
		# zoom percentage
		zoom_label = Label( status_frame, relief=SUNKEN, bd=bkchem_config.border_width, textvariable=self.zoom_var, anchor='center', width=6, height=2)
		zoom_label.pack( side="left")
		# cursor position
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


	def update_status( self, signal, time=None):
		"""if time is none it is calculated based on the string length"""
		if time is None and signal:
			time = 4 + 0.05 * len( signal)
		if signal:
			self.stat.set( signal)
			if self._after:
				self.after_cancel( self._after)
			self._after = self.after( int( time*1000), func=self.clear_status)


	def clear_status( self):
		self.stat.set( '')


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


	def put_to_clipboard( self, xml, pos):
		self._clipboard = xml
		self._clipboard_pos = pos


	def get_clipboard( self):
		return self._clipboard


	def get_clipboard_pos( self):
		return self._clipboard_pos


	def read_user_templates( self):
		[Store.utm.add_template_from_CDML( n) for n in os_support.get_local_templates()]


	def read_biomolecule_templates( self):
		from bkchem import biomolecule_loader
		entries = biomolecule_loader.load_biomolecule_entries()
		for entry in entries:
			Store.btm.register_smiles_template(
				entry['smiles'], name_override=entry['name']
			)


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


	def save_as_template( self):
		name = interactors.save_as_template( self.paper)
		if name:
			self.save_CDML( name=name, update_default_dir=0)
			Store.log( _("The file was saved as a template %s") % name)


	def insert_biomolecule_template( self):
		if not Store.btm or not Store.btm.get_template_names():
			Store.log( _("No biomolecule templates are available"))
			return
		if hasattr( self, '_mode_to_group') and 'biotemplate' in self.modes_sort:
			self.invoke_mode( 'biotemplate')
		else:
			self.change_mode( 'biotemplate')


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


	def ask_preferences( self):
		pd = dialogs.preferences_dialog( self, Store.pm)
		if pd.result == 1:
			for i in self.papers:
				i._paper_properties['use_real_minus'] = Store.pm.get_preference("use_real_minus")
				[j.redraw() for j in i.stack]


	def _show_theme_dialog( self):
		"""Open theme selector and apply the chosen theme."""
		dialog = dialogs.theme_dialog( self)
		if dialog.result:
			theme_manager.set_active_theme( dialog.result)
			Store.pm.add_preference( 'theme', dialog.result)
			theme_manager.apply_gui_theme( self)


	## ------------------------------ THE BATCH MODE ------------------------------
	def process_batch( self, opts):

		if opts[0] == "-b":
			plugin_path = opts[1]

			the_globals = {'App': Store.app,
										'Args': opts[2:]}

			with open(plugin_path) as f:
				code = compile(f.read(), plugin_path, 'exec')
				exec(code, the_globals)  # nosec B102 - explicit batch script execution

