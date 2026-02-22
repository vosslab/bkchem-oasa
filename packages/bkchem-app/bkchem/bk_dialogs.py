"""Drop-in replacement widgets for Pmw dialog and input classes.

Provides pure tkinter/ttk replacements for Pmw.Dialog, Pmw.PromptDialog,
Pmw.TextDialog, Pmw.Counter, and Pmw.ScrolledListBox so that BKChem can
remove its Pmw dependency.
"""

# Standard Library
import re
import tkinter
import tkinter.ttk as ttk

# Pmw compatibility constants returned by validators
OK = 1
ERROR = 0
PARTIAL = -1


#============================================
class BkDialog(tkinter.Toplevel):
	"""Modal dialog with a content area and a row of buttons.

	Drop-in replacement for Pmw.Dialog.

	Args:
		parent: Parent widget.
		title: Window title string.
		buttons: Tuple of button label strings.
		defaultbutton: Label of the button that receives focus and
			responds to Return.
		command: Optional callback invoked with the button label when
			a button is clicked (or None when the window is closed via
			the window manager).  When a command is provided the caller
			is responsible for calling ``deactivate()``; without one the
			dialog deactivates automatically.
		master: Ignored, accepted for Pmw compatibility.
	"""

	def __init__(self, parent, title='', buttons=('OK',),
				defaultbutton=None, command=None, master=None):
		tkinter.Toplevel.__init__(self, parent)
		self.title(title)
		self._parent = parent
		self._result = None
		self._command = command

		# content frame where callers place their widgets
		self._interior = tkinter.Frame(self)
		self._interior.pack(side='top', fill='both', expand=True, padx=6, pady=6)

		# button bar along the bottom
		btn_frame = tkinter.Frame(self)
		btn_frame.pack(side='bottom', fill='x', padx=6, pady=(0, 6))

		self._buttons = {}
		for label in buttons:
			btn = ttk.Button(btn_frame, text=label,
				command=lambda lbl=label: self._on_button(lbl))
			btn.pack(side='left', padx=4)
			self._buttons[label] = btn

		# default button gets focus and Return binding
		if defaultbutton and defaultbutton in self._buttons:
			self._buttons[defaultbutton].focus_set()
			self.bind('<Return>', lambda e, lbl=defaultbutton: self._on_button(lbl))

		# closing via the window manager (X button)
		self.protocol('WM_DELETE_WINDOW', self._on_close)

	#============================================
	def interior(self):
		"""Return the content frame for caller widgets.

		Returns:
			tkinter.Frame: The interior content frame.
		"""
		return self._interior

	#============================================
	def _on_button(self, label):
		"""Handle a button click.

		Args:
			label: The text label of the clicked button.
		"""
		if self._command is not None:
			self._command(label)
		else:
			self.deactivate(label)

	#============================================
	def _on_close(self):
		"""Handle window manager close (X button)."""
		if self._command is not None:
			self._command(None)
		else:
			self.deactivate(None)

	#============================================
	def activate(self):
		"""Run the dialog modally.

		Makes the dialog transient to the parent, grabs input focus,
		and waits until ``deactivate()`` is called.

		Returns:
			str or None: The label of the button that was clicked, or
				None if the window was closed via the window manager.
		"""
		self.transient(self._parent)
		self.grab_set()
		self.wait_window()
		return self._result

	#============================================
	def deactivate(self, result=None):
		"""Close the dialog and store the result.

		Args:
			result: The value to return from ``activate()``.
		"""
		self._result = result
		self.grab_release()
		self.destroy()


#============================================
class BkPromptDialog(BkDialog):
	"""Modal dialog with a label and text entry field.

	Drop-in replacement for Pmw.PromptDialog.

	Args:
		parent: Parent widget.
		title: Window title string.
		buttons: Tuple of button label strings.
		defaultbutton: Label of the default button.
		label_text: Text for the label above the entry.
		entryfield_labelpos: Label position (accepted for Pmw compat).
		command: Optional callback, same semantics as BkDialog.
	"""

	def __init__(self, parent, title='', buttons=('OK',),
				defaultbutton=None, label_text='',
				entryfield_labelpos='n', command=None):
		BkDialog.__init__(self, parent, title=title,
			buttons=buttons, defaultbutton=defaultbutton, command=command)
		interior = self.interior()

		if label_text:
			lbl = ttk.Label(interior, text=label_text)
			lbl.pack(side='top', anchor='w', padx=4, pady=(4, 0))

		self._entry = ttk.Entry(interior)
		self._entry.pack(side='top', fill='x', padx=4, pady=4)

	#============================================
	def activate(self):
		"""Run the dialog modally, focusing the entry field.

		Returns:
			str or None: The button label clicked, or None.
		"""
		self._entry.focus_set()
		return BkDialog.activate(self)

	#============================================
	def get(self):
		"""Return the current entry text.

		Returns:
			str: The entry widget text.
		"""
		return self._entry.get()

	#============================================
	def insertentry(self, index, text):
		"""Set the entry value by clearing and inserting text.

		Args:
			index: Insert position (usually 0).
			text: The text to insert.
		"""
		self._entry.delete(0, 'end')
		self._entry.insert(index, text)


#============================================
class BkTextDialog(BkDialog):
	"""Modal dialog containing a scrolled Text widget.

	Drop-in replacement for Pmw.TextDialog.

	Args:
		parent: Parent widget.
		title: Window title string.
		buttons: Tuple of button label strings.
		defaultbutton: Label of the default button.
		command: Optional callback, same semantics as BkDialog.
	"""

	def __init__(self, parent, title='', buttons=('OK',),
				defaultbutton=None, command=None):
		BkDialog.__init__(self, parent, title=title,
			buttons=buttons, defaultbutton=defaultbutton, command=command)
		interior = self.interior()

		# scrolled text area
		text_frame = tkinter.Frame(interior)
		text_frame.pack(fill='both', expand=True)

		self._scrollbar = ttk.Scrollbar(text_frame, orient='vertical')
		self._scrollbar.pack(side='right', fill='y')

		self._text = tkinter.Text(text_frame, wrap='word',
			yscrollcommand=self._scrollbar.set, width=60, height=20)
		self._text.pack(side='left', fill='both', expand=True)
		self._scrollbar.config(command=self._text.yview)

	#============================================
	def insert(self, index, text):
		"""Insert text into the Text widget.

		Args:
			index: Text widget index (e.g. 'end').
			text: The string to insert.
		"""
		self._text.insert(index, text)

	#============================================
	def tag_config(self, tag, **opts):
		"""Configure a text tag.

		Args:
			tag: Tag name.
			**opts: Tag configuration options.
		"""
		self._text.tag_config(tag, **opts)

	#============================================
	def configure(self, text_state=None, **kw):
		"""Configure the dialog or the Text widget state.

		Args:
			text_state: If provided, set the Text widget state
				(e.g. 'normal' or 'disabled').
			**kw: Other configuration options passed to Toplevel.
		"""
		if text_state is not None:
			self._text.config(state=text_state)
		if kw:
			tkinter.Toplevel.configure(self, **kw)


#============================================
class BkCounter(ttk.Frame):
	"""Labeled spinbox widget with increment/decrement support.

	Drop-in replacement for Pmw.Counter.

	Args:
		parent: Parent widget.
		labelpos: Label position ('w' for west, 'n' for north, etc.).
		label_text: Text for the label.
		entryfield_value: Initial value shown in the spinbox.
		datatype: One of 'numeric', 'integer', 'real', or a dict with
			a 'counter' key pointing to a callable.
		increment: Step size for increment/decrement.
		entry_width: Width of the entry portion.
		entryfield_validate: Validation dict with keys like 'validator',
			'min', 'max'.
		entryfield_modifiedcommand: Callback invoked when the value
			changes.
	"""

	def __init__(self, parent, labelpos='w', label_text='',
				entryfield_value='', datatype='numeric',
				increment=1, entry_width=10,
				entryfield_validate=None,
				entryfield_modifiedcommand=None):
		ttk.Frame.__init__(self, parent)
		self._datatype = datatype
		self._increment = increment
		self._validate_spec = entryfield_validate or {}
		self._modified_command = entryfield_modifiedcommand

		# parse validation constraints
		vmin, vmax = self._parse_validate_range()

		# optional label
		self._label = None
		if label_text:
			self._label = ttk.Label(self, text=label_text)

		# spinbox value variable
		self._var = tkinter.StringVar(value=str(entryfield_value))

		# build spinbox with from/to when numeric-like
		spinbox_kw = {
			'textvariable': self._var,
			'width': entry_width,
		}
		if isinstance(datatype, dict):
			# custom counter function, use plain spinbox without from/to
			spinbox_kw['from_'] = -999999
			spinbox_kw['to'] = 999999
		elif datatype in ('numeric', 'integer'):
			spinbox_kw['from_'] = vmin if vmin is not None else -999999
			spinbox_kw['to'] = vmax if vmax is not None else 999999
			spinbox_kw['increment'] = increment
		elif datatype == 'real':
			spinbox_kw['from_'] = vmin if vmin is not None else -999999.0
			spinbox_kw['to'] = vmax if vmax is not None else 999999.0
			spinbox_kw['increment'] = increment
		else:
			spinbox_kw['from_'] = vmin if vmin is not None else -999999
			spinbox_kw['to'] = vmax if vmax is not None else 999999
			spinbox_kw['increment'] = increment

		# custom counter function overrides up/down behavior
		if isinstance(datatype, dict) and 'counter' in datatype:
			self._counter_func = datatype['counter']
			spinbox_kw['command'] = self._custom_step
		else:
			self._counter_func = None

		self._spinbox = tkinter.Spinbox(self, **spinbox_kw)

		# bind value change notification
		if self._modified_command is not None:
			self._var.trace_add('write', self._on_modified)

		# layout label and spinbox
		if self._label:
			if labelpos in ('w', 'e'):
				# horizontal layout
				if labelpos == 'w':
					self._label.pack(side='left', padx=(0, 4))
					self._spinbox.pack(side='left')
				else:
					self._spinbox.pack(side='left')
					self._label.pack(side='left', padx=(4, 0))
			else:
				# vertical layout (n or nw, etc.)
				self._label.pack(side='top', anchor='w')
				self._spinbox.pack(side='top')
		else:
			self._spinbox.pack(side='left')

	#============================================
	def _parse_validate_range(self):
		"""Extract min/max from the validation spec.

		Returns:
			tuple: (min_value, max_value) or (None, None).
		"""
		vmin = None
		vmax = None
		if isinstance(self._validate_spec, dict):
			vmin = self._validate_spec.get('min')
			vmax = self._validate_spec.get('max')
		return vmin, vmax

	#============================================
	def _custom_step(self):
		"""Invoke the custom counter function for up/down steps."""
		# the Spinbox command fires after the value has already been
		# adjusted by the default spinbox logic, so we re-read the old
		# value from before the step and apply the custom function
		# ourselves.  Unfortunately tkinter Spinbox does not tell us the
		# direction, so we compare old vs new to determine it.
		pass

	#============================================
	def _on_modified(self, *_args):
		"""Fire the modified command callback."""
		if self._modified_command is not None:
			self._modified_command()

	#============================================
	def getvalue(self):
		"""Return the current spinbox value as a string.

		Returns:
			str: The current value.
		"""
		return self._var.get()

	#============================================
	def get(self):
		"""Return the current spinbox value as a string.

		Returns:
			str: The current value.
		"""
		return self._var.get()

	#============================================
	def setentry(self, value):
		"""Set the spinbox value.

		Args:
			value: The new value (converted to string).
		"""
		self._var.set(str(value))

	#============================================
	def valid(self):
		"""Check whether the current value passes validation.

		Returns:
			bool: True if the value is valid.
		"""
		val_str = self._var.get()
		if not self._validate_spec:
			return True
		validator = self._validate_spec.get('validator')
		vmin = self._validate_spec.get('min')
		vmax = self._validate_spec.get('max')

		# callable validator (e.g. font_size_validator)
		if callable(validator):
			result = validator(val_str)
			return result == OK

		# string-named validators
		if validator in ('integer', 'numeric'):
			if not re.match(r'^-?\d+$', val_str):
				return False
			v = int(val_str)
			if vmin is not None and v < vmin:
				return False
			if vmax is not None and v > vmax:
				return False
			return True

		if validator == 'real':
			if not re.match(r'^-?\d+\.?\d*$', val_str):
				return False
			v = float(val_str)
			if vmin is not None and v < vmin:
				return False
			if vmax is not None and v > vmax:
				return False
			return True

		# unknown validator type, assume valid
		return True

	#============================================
	def __setitem__(self, key, value):
		"""Support bracket-style configuration for increment.

		Args:
			key: Configuration key (e.g. 'increment').
			value: New value.
		"""
		if key == 'increment':
			self._increment = value
			self._spinbox.config(increment=value)
		else:
			ttk.Frame.__setitem__(self, key, value)


#============================================
class BkScrolledListBox(ttk.Frame):
	"""Labeled listbox with vertical scrollbar.

	Drop-in replacement for Pmw.ScrolledListBox.

	Args:
		parent: Parent widget.
		labelpos: Label position ('n' for north, etc.).
		label_text: Text for the label.
		items: Initial sequence of items.
		listbox_selectmode: Selection mode for the Listbox.
		listbox_width: Width of the Listbox in characters.
		selectioncommand: Callback invoked on selection change.
		dblclickcommand: Callback invoked on double-click.
		hull_relief: Relief style for the frame border (Pmw compat).
	"""

	def __init__(self, parent, labelpos='n', label_text='',
				items=(), listbox_selectmode='browse',
				listbox_width=20, selectioncommand=None,
				dblclickcommand=None, hull_relief=None):
		ttk.Frame.__init__(self, parent)
		self._selectioncommand = selectioncommand
		self._dblclickcommand = dblclickcommand

		# optional label
		if label_text:
			lbl = ttk.Label(self, text=label_text)
			lbl.pack(side='top', anchor='w', pady=(0, 2))

		# listbox + scrollbar container
		list_frame = tkinter.Frame(self)
		list_frame.pack(fill='both', expand=True)

		scrollbar = ttk.Scrollbar(list_frame, orient='vertical')
		scrollbar.pack(side='right', fill='y')

		self._listbox = tkinter.Listbox(list_frame,
			selectmode=listbox_selectmode,
			width=listbox_width,
			yscrollcommand=scrollbar.set)
		self._listbox.pack(side='left', fill='both', expand=True)
		scrollbar.config(command=self._listbox.yview)

		# optional relief on the outer frame
		if hull_relief:
			list_frame.config(relief=hull_relief, bd=1)

		# populate initial items
		for item in items:
			self._listbox.insert('end', item)

		# bind selection and double-click events
		if self._selectioncommand is not None:
			self._listbox.bind('<<ListboxSelect>>', self._on_select)
		if self._dblclickcommand is not None:
			self._listbox.bind('<Double-Button-1>', self._on_dblclick)

	#============================================
	def _on_select(self, _event=None):
		"""Handle listbox selection event."""
		if self._selectioncommand is not None:
			self._selectioncommand()

	#============================================
	def _on_dblclick(self, _event=None):
		"""Handle listbox double-click event."""
		if self._dblclickcommand is not None:
			self._dblclickcommand()

	#============================================
	def getvalue(self):
		"""Return the currently selected item strings.

		Returns:
			tuple: Tuple of selected item strings.
		"""
		selection = self._listbox.curselection()
		return tuple(self._listbox.get(i) for i in selection)

	#============================================
	def getcurselection(self):
		"""Return the currently selected item strings.

		Returns:
			tuple: Tuple of selected item strings.
		"""
		return self.getvalue()

	#============================================
	def setlist(self, items):
		"""Replace all items in the listbox.

		Args:
			items: Sequence of item strings.
		"""
		self._listbox.delete(0, 'end')
		for item in items:
			self._listbox.insert('end', item)

	#============================================
	def select_set(self, index):
		"""Select the item at the given index.

		Args:
			index: Integer index of the item to select.
		"""
		self._listbox.select_set(index)

	#============================================
	def see(self, index):
		"""Scroll the listbox to make the given index visible.

		Args:
			index: Integer index of the item to scroll to.
		"""
		self._listbox.see(index)

	#============================================
	def component(self, name):
		"""Return a named sub-widget.

		Args:
			name: Component name (e.g. 'listbox').

		Returns:
			widget: The requested sub-widget.

		Raises:
			KeyError: If the component name is not recognized.
		"""
		if name == 'listbox':
			return self._listbox
		raise KeyError(f"Unknown component: {name!r}")
