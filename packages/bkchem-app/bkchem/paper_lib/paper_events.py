"""Event binding mixin methods for BKChem paper."""

import sys

from bkchem.singleton_store import Store


class PaperEventsMixin:
	"""Event binding and input handling helpers extracted from paper.py."""

	def set_bindings( self):
		if not Store.app.in_batch_mode:
			self.bind( "<B1-Motion>", self._drag1)
			self.bind( "<ButtonRelease-1>", self._release1)
			self.bind( "<Shift-B1-Motion>", self._drag1)
			self.bind( "<Button-1>", lambda e: self._pressed1( e, mod=[]))
			self.bind( "<Shift-Button-1>", lambda e: self._pressed1( e, mod=['shift']))
			self.bind( "<Control-Button-1>", lambda e: self._pressed1( e, mod=['ctrl']))
			self.bind( "<Control-B1-Motion>", self._drag1)
			self.bind( "<Delete>", self.key_pressed)
			self.bind( "<Key>", self.key_pressed)
			self.bind( "<KeyRelease>", self.key_released)
			self.bind( "<Enter>", self.take_focus)
			self.bind( "<Button-3>", self._n_pressed3)
			self.bind( "<Shift-Button-3>", lambda e: self._n_pressed3( e, mod=["shift"]))
			self.bind( "<Control-Button-3>", lambda e: self._n_pressed3( e, mod=["ctrl"]))
			self.bind( "<Button-2>", self._n_pressed2)
			self.bind( "<Shift-Button-2>", lambda e: self._n_pressed2( e, mod=["shift"]))
			self.bind( "<Control-Button-2>", lambda e: self._n_pressed2( e, mod=["ctrl"]))
			self.bind( "<Motion>", self._move)
			self.bind( "<Leave>", self._leave)
			# scrolling and scroll-wheel zoom
			if sys.platform == 'darwin':
				self.bind('<MouseWheel>', lambda e: self.yview('scroll', -e.delta, 'units'))
				self.bind('<Control-MouseWheel>', lambda e: self.zoom_in() if e.delta > 0 else self.zoom_out())
			else:
				self.bind("<Button-4>", lambda e: self.yview("scroll", -1, "units"))
				self.bind("<Button-5>", lambda e: self.yview("scroll", 1, "units"))
				self.bind('<Control-Button-4>', lambda e: self.zoom_in())
				self.bind('<Control-Button-5>', lambda e: self.zoom_out())

			# zoom keyboard shortcuts
			self.bind('<Control-plus>', lambda e: self.zoom_in())
			self.bind('<Control-equal>', lambda e: self.zoom_in())
			self.bind('<Control-minus>', lambda e: self.zoom_out())
			self.bind('<Control-Key-0>', lambda e: self.zoom_reset())
			# hex grid: Ctrl+G toggles dots, Shift+Ctrl+G toggles snap
			self.bind('<Control-g>', lambda e: self.toggle_hex_grid())
			self.bind('<Shift-Control-G>', lambda e: self.toggle_hex_grid_snap())


	def add_bindings( self, active_names=()):
		self.lower( self.background)
		# show hex grid on first call if flagged for startup display
		if getattr(self, '_hex_grid_show_on_bindings', False):
			self._hex_grid_show_on_bindings = False
			self.show_hex_grid()
		# keep hex grid above background but below chemistry
		if hasattr(self, '_hex_grid_overlay') and self._hex_grid_overlay:
			self.tag_raise("hex_grid", self.background)
		[o.lift() for o in self.stack]
		self._do_not_focus = [] # self._do_not_focus is temporary and is cleaned automatically here
		self.event_generate( "<<selection-changed>>")
		# we generate this event here because this method is often called after some change as a last thing


	def remove_bindings( self, ids=()):
		if not ids:
			for tag in self.all_names_to_bind + ("mark",):
				self.tag_unbind( tag, '<Enter>')
				self.tag_unbind( tag, '<Leave>')
		else:
			[self.tag_unbind( id, '<Enter>') for id in ids]
			[self.tag_unbind( id, '<Leave>') for id in ids]


	## event bound methods
	def _pressed1( self, event, mod=None):
		"button 1"
		event.x = self.canvasx( event.x)
		event.y = self.canvasy( event.y)
		Store.app.mode.mouse_down( event, modifiers=mod or [])


	def _release1( self, event):
		event.x = self.canvasx( event.x)
		event.y = self.canvasy( event.y)
		Store.app.mode.mouse_up( event)


	def _drag1( self, event):
		# unfortunately we need to simulate "enter" and "leave" in this way because
		# when B1 is down such events do not occur
		event.x = self.canvasx( event.x)
		event.y = self.canvasy( event.y)
		Store.app.update_cursor_position( event.x, event.y)
		Store.app.mode.mouse_drag( event)
		b = self.find_overlapping( event.x-2, event.y-2, event.x+2, event.y+2)
		b = list(filter( self.is_registered_id, b))
		a = list(map( self.id_to_object, b))
		a = [i for i in a if i not in self._do_not_focus]
		if a:
			a = a[-1]
		else:
			a = None
		if a:
			if not self._in:
				self._in = a
				Store.app.mode.enter_object( self._in, event)
			elif a != self._in:
				self._in = a
				Store.app.mode.leave_object( event)
				Store.app.mode.enter_object( self._in, event)
		else:
			if self._in or Store.app.mode.focused: # sometimes self._in and Store.app.mode.focused is different
				self._in = None
				Store.app.mode.leave_object( event)


	def _n_pressed3( self, event, mod=None):
		event.x = self.canvasx( event.x)
		event.y = self.canvasy( event.y)
		Store.app.mode.mouse_down3( event, modifiers=mod or [])


	def _n_pressed2( self, event, mod=None):
		event.x = self.canvasx( event.x)
		event.y = self.canvasy( event.y)
		Store.app.mode.mouse_down2( event, modifiers=mod or [])


	def _move( self, event):
		event.x = self.canvasx( event.x)
		event.y = self.canvasy( event.y)

		Store.app.update_cursor_position( event.x, event.y)
		Store.app.mode.mouse_move( event)

		b = self.find_overlapping( event.x-3, event.y-3, event.x+3, event.y+3)
		b = list(filter( self.is_registered_id, b))
		id_objs = [(x, self.id_to_object( x)) for x in b]
		a = [i for i in id_objs if i[1] not in self._do_not_focus]

		if a:
			fid, fobj = a[-1]
		else:
			fid, fobj = None, None

		# Keep focused object stable while pointer hovers attached helper items.
		self._in = Store.app.mode.focused

		if (fobj and
				(fobj != self._in or
					(isinstance(fobj, self.classes_with_per_item_reselection) and
					self._in_id != fid))):
			self._in = fobj
			self._in_id = fid
			Store.app.mode.enter_object( self._in, event)
		elif not fobj and self._in:
			#if not a and Store.app.mode.focused:
			self._in = None
			self._in_id = None
			Store.app.mode.leave_object( event)


	def _enter( self, event):
		Store.app.mode.clean_key_queue()


	def _leave( self, event):
		Store.app.mode.clean_key_queue()


	# item bound methods
	def enter_item( self, event):
		event.x = self.canvasx( event.x)
		event.y = self.canvasy( event.y)

		try:
			a = self.id_to_object( self.find_withtag( 'current')[0])
		except IndexError:
			a = None
		if a and a != self._in:
			self._in = a
			Store.app.mode.enter_object( self._in, event)


	def leave_item( self, event):
		event.x = self.canvasx( event.x)
		event.y = self.canvasy( event.y)
		if self._in:
			self._in = None
			Store.app.mode.leave_object( event)


	def key_pressed( self, event):
		Store.app.mode.key_pressed( event)


	def key_released( self, event):
		Store.app.mode.key_released( event)

	## end of event bound methods


	def take_focus( self, event):
		self.focus_set()
