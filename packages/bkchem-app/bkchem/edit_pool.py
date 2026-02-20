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

"""The 'edit pool' widget resides here.

Buttons are defined in modes.yaml under edit_pool_buttons and created
via create_buttons() so they can live in the submode ribbon instead of
occupying a permanent row.
"""

import builtins
import os
import re
import tkinter
from tkinter import Frame, Button, Entry

from xml.sax import saxutils

from bkchem import bkchem_utils
from bkchem import bkchem_config

from bkchem.keysym_loader import get_keysyms
from bkchem.singleton_store import Store
from bkchem.group_lib import GROUPS_TABLE


# gettext i18n translation fallback
_ = builtins.__dict__.get( '_', lambda m: m)



class editPool( Frame):

	# YAML command key -> Python method name, or (method_name, arg) tuple
	COMMAND_MAP = {
		'interpret': '_interpretButtonPressed',
		'asis': '_setButtonPressed',
		'subnum': '_numbersToSubButtonPressed',
		'tag_i': ('_tag_it', 'i'),
		'tag_b': ('_tag_it', 'b'),
		'tag_sub': ('_tag_it', 'sub'),
		'tag_sup': ('_tag_it', 'sup'),
		'specialchar': '_specialCharButtonPressed',
	}


	def __init__( self, master, **kw):
		Frame.__init__( self, master, **kw)
		self.text = ''
		self.interpret = 1
		self.editPool = Entry(
			self,
			width=50,
			state='disabled',
			font="Helvetica 12",
			disabledbackground=bkchem_config.background_color,
			disabledforeground="#555555",
		)
		self.editPool.pack( side='left')

		self.editPool.bind( '<Return>', self._interpretButtonPressed)
		self.editPool.bind( '<Escape>', self._cancel)

		self.editPool.bind( '<Control-s>', lambda e: self._tag_it( "sub"))
		self.editPool.bind( '<Control-S>', lambda e: self._tag_it( "sup"))
		self.editPool.bind( '<Control-i>', lambda e: self._tag_it( "i"))
		self.editPool.bind( '<Control-b>', lambda e: self._tag_it( "b"))

		self.editPool.bind("<KeyPress>", self._key)

		# initialize button references to None
		self._buttons_by_key = {}
		self.interpretButton = None
		self.setButton = None
		self.numbersToSubButton = None
		self.italic = None
		self.bold = None
		self.subscript = None
		self.superscript = None
		self.specialCharButton = None
		self._button_frame = None
		self.active = False


	#============================================
	def _resolve_command( self, command_key: str):
		"""Map a YAML command key to a callable."""
		entry = self.COMMAND_MAP[command_key]
		if isinstance(entry, tuple):
			method_name, arg = entry
			return bkchem_utils.lazy_apply(getattr(self, method_name), (arg,))
		return getattr(self, entry)


	#============================================
	def create_buttons( self, parent: Frame) -> Frame:
		"""Create edit-pool buttons from YAML config inside a new Frame.

		Returns the frame so the caller can pack/grid it in the ribbon.
		"""
		from bkchem.modes.config import get_edit_pool_config
		self._button_frame = Frame( parent)
		groups = get_edit_pool_config()
		self._buttons_by_key = {}

		for group_idx, group in enumerate(groups):
			# vertical separator between groups (skip before first)
			if group_idx > 0:
				sep = Frame(self._button_frame, width=1, bg='#b0b0b0')
				sep.pack(side='left', fill='y', padx=2, pady=1)

			for opt in group['options']:
				pix = Store.app.request('pixmap', name=opt['icon'])
				cmd = self._resolve_command(opt['command'])
				btn = Button(
					self._button_frame,
					image=pix,
					text=opt['name'],
					command=cmd,
					state='disabled',
					bd=bkchem_config.border_width,
				)
				Store.app.balloon.bind(btn, opt['tooltip'])
				btn.pack(side='left')
				self._buttons_by_key[opt['key']] = btn

		# legacy attribute aliases for external references
		self.interpretButton = self._buttons_by_key.get('interpret')
		self.setButton = self._buttons_by_key.get('asis')
		self.numbersToSubButton = self._buttons_by_key.get('subnum')
		self.italic = self._buttons_by_key.get('italic')
		self.bold = self._buttons_by_key.get('bold')
		self.subscript = self._buttons_by_key.get('subscript')
		self.superscript = self._buttons_by_key.get('superscript')
		self.specialCharButton = self._buttons_by_key.get('specialchar')

		return self._button_frame


	#============================================
	def destroy_buttons( self):
		"""Destroy the button frame and reset all button references."""
		if self._button_frame is not None:
			self._button_frame.destroy()
			self._button_frame = None
		self._buttons_by_key = {}
		# clear legacy aliases
		self.interpretButton = None
		self.setButton = None
		self.numbersToSubButton = None
		self.italic = None
		self.bold = None
		self.subscript = None
		self.superscript = None
		self.specialCharButton = None


	#============================================
	def _all_buttons( self) -> list:
		"""Return list of all button widgets (may be empty before create_buttons)."""
		return list(self._buttons_by_key.values())


	def _interpretButtonPressed( self, *e):
		t = self.editPool.get()
		if t.lower() in GROUPS_TABLE:
			self._setText( t)
			#self._setText( GROUPS_TABLE[ string.lower(t)]['text'])
			#self.editPool.insert(0, self.text)
		else:
			self._setText( t)
			self.text = re.sub( "\\\\n", "\n", self.text)
		self._quit()


	def _setButtonPressed( self, *e):
		self._setText( self.editPool.get())
		self.interpret = 0
		self._quit()


	def _numbersToSubButtonPressed( self, *e):
		self._setText( re.sub( r"\d+", r"<sub>\g<0></sub>", self.editPool.get()))
		self._quit()


	def _cancel( self, e):
		self._setText( None)
		self.active = False
		self._quit()


	def _quit( self):
		# release grab on toplevel since buttons may live outside this Frame
		self.winfo_toplevel().grab_release()
		self._disable()
		self._normaly_terminated = 1
		self.active = False
		self.quit()


	def _disable( self):
		# disable all buttons that currently exist
		for btn in self._all_buttons():
			btn.configure( state='disabled')
		self.editPool.configure( state='disabled')


	def _enable( self):
		# enable all buttons that currently exist
		for btn in self._all_buttons():
			btn.configure( state='normal')
		self.editPool.configure( state='normal')


	def _setText( self, text):
		self.text = text
		self._update()


	def _update( self):
		self.editPool.delete(0, last='end')
		if self.text:
			self.editPool.insert(0, self.text)


	def activate( self, text=None, select=1):
		"""activates edit_pool and returns inserted value (None if cancel occured),
		if parameter text is None it preserves the old one, use text='' to delete old text"""
		self.active = True
		self.interpret = 1
		self.focus_set()
		# grab toplevel so buttons in the ribbon (outside this Frame) still work
		self.winfo_toplevel().grab_set()
		self._enable()
		# this is because I need to distinguish whether the mainloop was terminated "from inside"
		# or from outside (this most of the time means the application was killed and the widgets are no longer available)
		self._normaly_terminated = 0
		if text is not None:
			self._setText( text)
		self.editPool.focus_set()
		if select:
			self.editPool.selection_range( 0, 'end')
		self.mainloop()
		if self._normaly_terminated:
			return self.text
		else:
			return None


	def _tag_it( self, tag):
		if self.editPool.selection_present():
			self.editPool.insert( tkinter.SEL_FIRST, '<%s>' % tag)
			self.editPool.insert( tkinter.SEL_LAST, '</%s>' % tag)
		else:
			self.editPool.insert( tkinter.INSERT, '<%s></%s>' % (tag, tag))
			self.editPool.icursor( self.editPool.index( tkinter.INSERT) - len( tag) - 3)


	def _key( self, event):
		if len(event.keysym) > 1 and event.keysym in get_keysyms():
			if self.editPool.selection_present():
				self.editPool.delete( "anchor", "insert")
			self.editPool.insert('insert', get_keysyms()[event.keysym])
			return "break"


	def _specialCharButtonPressed( self):
		dialog = special_character_menu( self._insertText)
		dialog.post( self.specialCharButton.winfo_rootx(), self.specialCharButton.winfo_rooty())


	def _insertText( self, text):
		if text is not None:
			self.editPool.insert( tkinter.INSERT, text)
		self.winfo_toplevel().grab_set()


class special_character_menu( tkinter.Menu):

	chars = {
		_("minus"): "&#8722;",
		_("arrow-left"): "&#x2190;",
		_("arrow-right"): "&#x2192;",
		_("nu"): "&#x3bd;",
		_("new line"): "\\n",
	}

	def __init__( self, callback, **kw):
		self.callback = callback
		tkinter.Menu.__init__( self, Store.app, tearoff=0, **kw)
		keys = sorted(self.chars.keys())
		for k in keys:
			self.add_command( label=k, command=bkchem_utils.lazy_apply( self.itemselected, (k,)))
		self.char = None


	def itemselected( self, k):
		self.callback( saxutils.unescape( self.chars[k]))


	def post( self, x, y):
		tkinter.Menu.post( self, x, y)
		if os.name != 'nt':
			self.grab_set()
