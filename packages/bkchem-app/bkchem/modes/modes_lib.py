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

"""Base mode classes: mode, simple_mode, basic_mode."""

import builtins

from warnings import warn

from bkchem import bkchem_utils
from bkchem import messages
from bkchem import interactors
from bkchem.singleton_store import Store
from bkchem.modes.config import get_modes_config, _load_submodes_from_yaml

# gettext i18n translation fallback
_ = builtins.__dict__.get( '_', lambda m: m)


#============================================
def event_to_key( event):
	"""Convert a tkinter key event to a normalized key string."""
	from bkchem import data
	key = event.keysym
	# 2 hacks to prevent ' ' -> 'space', '.' -> 'period' and other conversions
	# first is dealing with "strange keys" (see data.strange_key_symbols for more info)
	if key in data.strange_key_symbols:
		key = data.strange_key_symbols[ key]
	# second is for keys that are more consistent in their behavior (char is not changing with Ctrl)
	elif len(key) > 1 and key.lower() == key:
		key = event.char
	# now special keys as Ctrl, Alt etc.
	elif key in data.special_key_symbols:
		key = data.special_key_symbols[ key]
	else:
		# normal keys should be lowercase, specials uppercase
		if len( key) == 1:
			key = key.lower()
	if key:
		return key
	# empty key happens for modifier-only or dead-key events on macOS
	return ''


## -------------------- PARENT MODES--------------------
class mode( object):
	"""abstract parent for all modes. No to be used for inheritation because the more specialized
	edit mode has all the methods for editing - just override what you need to change"""
	def __init__( self):
		# derive YAML key from class name: draw_mode -> 'draw'
		yaml_key = type(self).__name__.replace('_mode', '')
		cfg = get_modes_config()['modes'].get(yaml_key, {})
		# load name from YAML, fall back to 'mode'
		self.name = _(cfg['name']) if 'name' in cfg else 'mode'
		# short button label: label -> name -> key (all i18n-wrapped)
		self.label = _(cfg.get('label', cfg.get('name', yaml_key)))
		# whether this mode shows edit pool text-entry buttons in the ribbon
		self.show_edit_pool = cfg.get('show_edit_pool', False)
		# load static submodes from YAML (dynamic modes override in their __init__)
		if not cfg.get('dynamic') and cfg.get('submodes'):
			parsed = _load_submodes_from_yaml(cfg)
			self.submodes = parsed[0]
			self.submodes_names = parsed[1]
			self.submode = list(parsed[2])
			self.icon_map = parsed[3]
			self.group_labels = parsed[4]
			self.group_layouts = parsed[5]
			self.tooltip_map = parsed[6]
			self.size_map = parsed[7]
		else:
			self.submodes = []
			self.submodes_names = []
			self.submode = []
			self.icon_map = {}
			self.group_labels = []
			self.group_layouts = []
			self.tooltip_map = {}
			self.size_map = {}
		self._key_sequences = {}
		self._recent_key_seq = ''
		self._specials_pressed = { 'C':0, 'A':0, 'M':0, 'S':0} # C-A-M-S


	def mouse_down( self, event, modifiers=[]):
		pass


	def mouse_down3( self, event, modifiers=[]):
		pass


	def mouse_down2( self, event, modifiers=[]):
		pass


	def mouse_up( self, event):
		pass


	def mouse_click( self, event):
		pass


	def mouse_drag( self, event):
		pass


	def enter_object( self, object, event):
		pass


	def leave_object( self, event):
		pass


	def mouse_move( self, event):
		pass


	def key_pressed( self, event):
		key = event_to_key( event) # Note: event.state can be used to query CAMS
		# first filter off specials (CAMS)
		if len( key) == 1 and key in 'CAMS':
			self._specials_pressed[ key] = 1
		else:
			# then if key is not CAMS update the recent key sequence
			# CAMS modificators first
			first = 1 # to separate each step with ' '
			for a in 'CAMS':
				if self._specials_pressed[ a]:
					if self._recent_key_seq:
						if first:
							self._recent_key_seq += ' ' + a
						else:
							self._recent_key_seq += '-' + a
					else:
						self._recent_key_seq = a
					first = 0
			# then the key itself
			if self._recent_key_seq:
				if first:
					first = 0
					self._recent_key_seq += ' ' + key
				else:
					self._recent_key_seq += '-' + key
			else:
				self._recent_key_seq = key
			# look if the keysequence is registered
			if self._recent_key_seq in self._key_sequences:
				Store.log( self._recent_key_seq)
				self._key_sequences[ self._recent_key_seq]()
				self._recent_key_seq = ''
			else:
				# or its a prefix of some registered sequence
				for key in list(self._key_sequences.keys()):
					if not key.find(self._recent_key_seq):
						Store.log( self._recent_key_seq)
						return None
				# if we get here it means that the key is neither used nor a prefix
				self._recent_key_seq = ''


	def key_released( self, event):
		key = event_to_key( event)
		if len( key) == 1 and key in 'CAMS':
			self._specials_pressed[ key] = 0


	def clean_key_queue( self):
		"""cleans status of all special keys;
		needed because especially after C-x C-f the C-release is grabbed by dialog
		and never makes it to paper, therefore paper calls this after a file was read"""
		for key in list(self._specials_pressed.keys()):
			self._specials_pressed[ key] = 0


	def get_name( self):
		return self.name


	def get_submode( self, i):
		if i < len( self.submodes):
			return self.submodes[i][ self.submode[i]]
		raise ValueError("invalid submode index")


	def set_submode( self, name):
		for sms in self.submodes:
			if name in sms:
				i = self.submodes.index( sms)
				self.submode[i] = sms.index( name)
				txt_name = self.__class__.__name__+'_'+name
				try:
					Store.log( messages.__dict__[txt_name], delay=20, message_type="hint")
				except KeyError:
					pass
				self.on_submode_switch( i, name)
				break


	def register_key_sequence( self, sequence, function, use_warning = 1):
		"""registers a function with its coresponding key sequence
		when use_warning is true (default) than issues warning about overriden
		or shadowed bindings. In most cases its good idea to let it check the bindings."""
		# registering a range
		if sequence.find( "##") >= 0:
			prefix, end = sequence.split('##')
			for c in end:
				self.register_key_sequence( prefix+c, bkchem_utils.lazy_apply( function, (prefix+c,)), use_warning=use_warning)
		# check of already registered values
		if use_warning and sequence in self._key_sequences:
			warn( "binding of sequence %s to function %s overrides its binding to function %s" %
					(sequence, function.__name__, self._key_sequences[ sequence].__name__),
					UserWarning, 2)
		elif use_warning:
			for key in list(self._key_sequences.keys()):
				if not key.find(sequence):
					warn( "binding of sequence %s to function %s shadows %s (binded to %s)" %
							(sequence, function.__name__, key, self._key_sequences[ key].__name__),
							UserWarning, 2)
		# the registration
		self._key_sequences[ sequence] = function


	def register_key_sequence_ending_with_number_range( self, sequence_base, function, numbers=None, attrs=None):
		if not numbers:
			numbers = []
		for i in numbers:
			if sequence_base and sequence_base.endswith( "-"):
				b = sequence_base
			elif sequence_base and not sequence_base.endswith( ' '):
				b = sequence_base+' '
			else:
				b = sequence_base
			self.register_key_sequence( b+str(i), bkchem_utils.lazy_apply( function, (i,), attrs=attrs))


	def unregister_all_sequences( self):
		self._key_sequences = {}


	def cleanup( self, paper=None):
		"""called when switching to another mode"""
		if self.focused:
			self.focused.unfocus()
			self.focused = None


	def startup( self):
		"""called when switching to this mode"""
		txt_name = self.__class__.__name__+"_startup"
		message = messages.__dict__.get( txt_name, "")
		if message:
			Store.log( message, delay=20, message_type="hint")


	def on_submode_switch( self, submode_index, name=''):
		"""called when submode is switched"""
		pass


	def on_paper_switch( self, old_paper, new_paper):
		"""called when paper is switched"""
		pass


	def copy_settings( self, old_mode):
		"""called when modes are changed, enables new mode to copy settings from old_mode"""
		self._specials_pressed = dict( old_mode._specials_pressed)



## -------------------- BASIC MODE --------------------
class simple_mode( mode):
	"""Little more sophisticated parent mode.

	"""
	def __init__( self):
		mode.__init__( self)
		self.focused = None


	def enter_object( self, object, event):
		if self.focused:
			self.focused.unfocus()
		self.focused = object
		self.focused.focus()


	def leave_object( self, event):
		if self.focused:
			self.focused.unfocus()
			self.focused = None


	def on_paper_switch( self, old_paper, new_paper):
		"""called when paper is switched"""
		self.focused = None



class basic_mode( simple_mode):

	def __init__( self):
		simple_mode.__init__( self)
		# name loaded from YAML via base class (no override needed)
		# align
		self.register_key_sequence( 'C-a C-t', lambda : Store.app.paper.align_selected( 't'))
		self.register_key_sequence( 'C-a C-b', lambda : Store.app.paper.align_selected( 'b'))
		self.register_key_sequence( 'C-a C-l', lambda : Store.app.paper.align_selected( 'l'))
		self.register_key_sequence( 'C-a C-r', lambda : Store.app.paper.align_selected( 'r'))
		self.register_key_sequence( 'C-a C-h', lambda : Store.app.paper.align_selected( 'h'))
		self.register_key_sequence( 'C-a C-v', lambda : Store.app.paper.align_selected( 'v'))
		# other
		self.register_key_sequence( 'C-d C-c', lambda : Store.app.paper.toggle_center_for_selected())
		self.register_key_sequence( 'C-d C-w', lambda : Store.app.paper.display_weight_of_selected())
		self.register_key_sequence( 'C-d C-i', lambda : Store.app.paper.display_info_on_selected())
		# object related key bindings
		self.register_key_sequence( 'C-o C-i', lambda : Store.app.paper.display_info_on_selected())
		self.register_key_sequence( 'C-o C-c', lambda : Store.app.paper.check_chemistry_of_selected())
		self.register_key_sequence( 'C-o C-d', lambda : interactors.ask_display_form_for_selected( Store.app.paper))
		# emacs like key bindings
		self.register_key_sequence( 'C-x C-s', Store.app.save_CDML)
		self.register_key_sequence( 'C-x C-w', Store.app.save_as_CDML)
		self.register_key_sequence( 'C-x C-f', Store.app.load_CDML)
		self.register_key_sequence( 'C-x C-c', Store.app._quit)
		self.register_key_sequence( 'C-x C-t', Store.app.close_current_paper)
		self.register_key_sequence( 'C-x C-n', Store.app.add_new_paper)
		self.register_key_sequence( 'C-/', lambda : Store.app.paper.undo())
		self.register_key_sequence( 'C-S-?', lambda : Store.app.paper.redo()) #note that 'S-/' => 'S-?'  !!!
		# windows style key bindings
		self.register_key_sequence( 'C-s', Store.app.save_CDML)
		self.register_key_sequence( 'C-z', self.undo)
		self.register_key_sequence( 'C-S-z', self.redo)
		# 'C-a' from windoze is in use - 'C-S-a' instead
		self.register_key_sequence( 'C-S-a', lambda : Store.app.paper.select_all())
		# arrow moving
		self.register_key_sequence( 'Up', lambda : self._move_selected( 0, -1))
		self.register_key_sequence( 'Down', lambda : self._move_selected( 0, 1))
		self.register_key_sequence( 'Left', lambda : self._move_selected( -1, 0))
		self.register_key_sequence( 'Right', lambda : self._move_selected( 1, 0))
		# manipulation of the paper.stack
		self.register_key_sequence( 'C-o C-f', lambda : Store.app.paper.lift_selected_to_top())
		self.register_key_sequence( 'C-o C-b', lambda : Store.app.paper.lower_selected_to_bottom())
		self.register_key_sequence( 'C-o C-s', lambda : Store.app.paper.swap_selected_on_stack())
		# mode switching
		self.register_key_sequence_ending_with_number_range( 'C-', self.switch_mode, numbers=list(range(1,10)))
		self.register_key_sequence_ending_with_number_range( 'C-A-', self.switch_mode, numbers=list(range(1,10)), attrs={"add":9})

		# debug, simo
		self.register_key_sequence( 'C-p', lambda : Store.app.paper.print_all_coords())
		self.register_key_sequence( 'C-r', lambda : Store.app.paper.redraw_all())

	def undo( self):
		Store.app.paper.undo()
		if self.focused and not Store.app.paper.is_registered_object( self.focused):
			# focused object was deleted
			self.focused = None


	def redo( self):
		Store.app.paper.redo()
		if self.focused and not Store.app.paper.is_registered_object( self.focused):
			# focused object was deleted
			self.focused = None


	def switch_mode( self, n, add=0):
		index = n+add-1
		if index < len( Store.app.modes_sort):
			self.cleanup()
			Store.app.radiobuttons.invoke( index) #change_mode( Store.app.modes_sort[n-1])
