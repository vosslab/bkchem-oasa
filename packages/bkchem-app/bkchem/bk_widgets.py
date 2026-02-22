"""Drop-in replacement wrappers for Pmw widget classes.

Provides BkOptionMenu, BkRadioSelect, and BkGroup as native tkinter/ttk
replacements for Pmw.OptionMenu, Pmw.RadioSelect, and Pmw.Group respectively.
Also defines BK_OK, BK_ERROR, and BK_PARTIAL constants replacing Pmw.OK,
Pmw.ERROR, and Pmw.PARTIAL.
"""

# Standard Library
import tkinter
import tkinter.ttk

# -- validation constants (replace Pmw.OK / Pmw.ERROR / Pmw.PARTIAL) --
BK_OK = 1
BK_ERROR = 0
BK_PARTIAL = -1


#============================================
class BkOptionMenu(tkinter.ttk.Frame):
	"""Drop-in replacement for Pmw.OptionMenu using ttk.Combobox.

	Provides a readonly combobox with an optional label, matching the
	Pmw.OptionMenu API used throughout BKChem.
	"""

	def __init__(self, parent, labelpos: str = 'w', label_text: str = '',
				items: tuple = (), command=None, initialitem=None,
				menubutton_width: int = None):
		"""Initialize BkOptionMenu.

		Args:
			parent: Parent tkinter widget.
			labelpos: Label position relative to combobox ('w' for left,
				'n' for top). Only 'w' and 'n' are supported.
			label_text: Text for the optional label. Empty string means
				no label is displayed.
			items: Sequence of string values for the dropdown.
			command: Callback invoked with the selected value string
				when the selection changes.
			initialitem: Initial selection. Can be an index (int) or a
				value string. Defaults to the first item if not given.
			menubutton_width: Width of the combobox in characters.
				None uses the ttk default.
		"""
		tkinter.ttk.Frame.__init__(self, parent)
		self._command = command
		self._items = list(items)
		self._var = tkinter.StringVar(self)

		# optional label
		self._label = None
		if label_text:
			self._label = tkinter.ttk.Label(self, text=label_text)

		# combobox
		combo_kw = {
			'textvariable': self._var,
			'values': self._items,
			'state': 'readonly',
		}
		if menubutton_width is not None:
			combo_kw['width'] = menubutton_width
		self._combo = tkinter.ttk.Combobox(self, **combo_kw)

		# layout based on label position
		if self._label is not None:
			if labelpos == 'n':
				self._label.pack(side='top', anchor='w')
				self._combo.pack(side='top', fill='x')
			else:
				# default: label on the west (left) side
				self._label.pack(side='left', padx=(0, 4))
				self._combo.pack(side='left')
		else:
			self._combo.pack(side='left')

		# set initial selection
		if initialitem is not None:
			if isinstance(initialitem, int):
				if 0 <= initialitem < len(self._items):
					self._var.set(self._items[initialitem])
			else:
				# treat as a value string
				if str(initialitem) in self._items:
					self._var.set(str(initialitem))
		elif self._items:
			self._var.set(self._items[0])

		# bind selection event
		self._combo.bind('<<ComboboxSelected>>', self._on_select)

	#============================================
	def _on_select(self, event=None):
		"""Handle combobox selection change events.

		Clears focus from the combobox and invokes the user callback
		with the newly selected value string.
		"""
		# clear the highlight so the widget does not look stuck
		self._combo.selection_clear()
		if self._command is not None:
			self._command(self._var.get())

	#============================================
	def getvalue(self) -> str:
		"""Return the currently selected value string."""
		return self._var.get()

	#============================================
	def setvalue(self, val: str) -> None:
		"""Set the current selection to val.

		Args:
			val: Value string that should appear in the combobox.
		"""
		self._var.set(val)

	#============================================
	def index(self, val) -> int:
		"""Return the index of val in the item list.

		For Pmw.SELECT compatibility, passing the string 'select'
		returns the index of the currently selected item.

		Args:
			val: A value string to look up, or the literal string
				'select' to get the current selection index.

		Returns:
			Integer index of the value in the item list.

		Raises:
			ValueError: If val is not found in the item list.
		"""
		# Pmw.SELECT is the string 'select'
		if val == 'select':
			val = self._var.get()
		return self._items.index(val)

	#============================================
	def setitems(self, items) -> None:
		"""Replace the item list with a new sequence.

		If the previously selected value exists in the new list it is
		preserved; otherwise the first item becomes selected.

		Args:
			items: New sequence of string values.
		"""
		old_val = self._var.get()
		self._items = list(items)
		self._combo['values'] = self._items
		# preserve selection when possible
		if old_val in self._items:
			self._var.set(old_val)
		elif self._items:
			self._var.set(self._items[0])
		else:
			self._var.set('')


#============================================
class BkRadioSelect(tkinter.Frame):
	"""Drop-in replacement for Pmw.RadioSelect.

	Supports both 'radiobutton' and 'checkbutton' button types using
	native tkinter widgets and a shared StringVar (radio) or per-button
	BooleanVar (check).
	"""

	def __init__(self, parent, labelpos: str = 'n', label_text: str = '',
				buttontype: str = 'radiobutton', orient: str = 'horizontal',
				command=None):
		"""Initialize BkRadioSelect.

		Args:
			parent: Parent tkinter widget.
			labelpos: Label position ('n' for top, 'w' for left).
			label_text: Optional label text.
			buttontype: Either 'radiobutton' or 'checkbutton'.
			orient: 'horizontal' or 'vertical' layout for the buttons.
			command: Callback invoked with the selected value string
				when a button is clicked.
		"""
		tkinter.Frame.__init__(self, parent)
		self._buttontype = buttontype
		self._orient = orient
		self._command = command
		self._buttons = {}

		# shared variable for radiobutton mode
		self._var = tkinter.StringVar(self)

		# per-button BooleanVars for checkbutton mode
		self._check_vars = {}

		# optional label
		self._label = None
		if label_text:
			self._label = tkinter.Label(self, text=label_text)
			if labelpos == 'w':
				self._label.pack(side='left', padx=(0, 4))
			else:
				self._label.pack(side='top', anchor='w')

		# container frame for the buttons
		self._btn_frame = tkinter.Frame(self)
		if self._label is not None and labelpos == 'w':
			self._btn_frame.pack(side='left')
		else:
			self._btn_frame.pack(side='top')

	#============================================
	def add(self, label: str, text: str = None) -> None:
		"""Add a button with the given label.

		Args:
			label: Internal value string used for selection tracking.
			text: Display text on the button. Defaults to label if
				not provided.
		"""
		display = text if text is not None else label
		pack_side = 'left' if self._orient == 'horizontal' else 'top'

		if self._buttontype == 'checkbutton':
			var = tkinter.BooleanVar(self, value=False)
			self._check_vars[label] = var
			btn = tkinter.Checkbutton(
				self._btn_frame,
				text=display,
				variable=var,
				command=lambda lbl=label: self._on_check(lbl),
			)
		else:
			# radiobutton
			btn = tkinter.Radiobutton(
				self._btn_frame,
				text=display,
				variable=self._var,
				value=label,
				command=lambda lbl=label: self._on_radio(lbl),
			)

		btn.pack(side=pack_side, padx=2)
		self._buttons[label] = btn

	#============================================
	def _on_radio(self, label: str) -> None:
		"""Handle radiobutton click events."""
		if self._command is not None:
			self._command(label)

	#============================================
	def _on_check(self, label: str) -> None:
		"""Handle checkbutton click events."""
		if self._command is not None:
			self._command(label)

	#============================================
	def getvalue(self) -> str:
		"""Return the currently selected value string.

		For radiobutton mode, returns the selected radio value.
		For checkbutton mode, returns a comma-separated string of
		all checked labels.
		"""
		if self._buttontype == 'checkbutton':
			# return list of checked labels joined by comma
			checked = [lbl for lbl, var in self._check_vars.items() if var.get()]
			return ','.join(checked)
		return self._var.get()

	#============================================
	def getcurselection(self) -> str:
		"""Alias for getvalue(), provided for Pmw compatibility."""
		return self.getvalue()

	#============================================
	def invoke(self, label) -> None:
		"""Programmatically select the given value.

		For radiobutton mode, sets the shared variable and fires
		the command callback. For checkbutton mode, toggles the
		button and fires the callback.

		Args:
			label: The label string or integer index of the button
				to activate.
		"""
		# accept integer index for Pmw compatibility
		if isinstance(label, int):
			keys = list(self._buttons.keys())
			if 0 <= label < len(keys):
				label = keys[label]
			else:
				return
		if self._buttontype == 'checkbutton':
			if label in self._check_vars:
				var = self._check_vars[label]
				var.set(not var.get())
				self._on_check(label)
		else:
			self._var.set(label)
			self._on_radio(label)

	#============================================
	def index(self, val) -> int:
		"""Return the integer index of a value in the button list.

		Args:
			val: A label string to look up.

		Returns:
			Integer index of the value in button order.

		Raises:
			ValueError: If val is not found.
		"""
		keys = list(self._buttons.keys())
		return keys.index(val)

	#============================================
	def configure(self, **kw) -> None:
		"""Configure the widget.

		Supports Pmw-compatible ``Button_state`` keyword to enable
		or disable all buttons in the group.

		Args:
			**kw: Configuration options.
		"""
		button_state = kw.pop('Button_state', None)
		if button_state is not None:
			state = button_state
			for btn in self._buttons.values():
				btn.configure(state=state)
		if kw:
			tkinter.Frame.configure(self, **kw)

	# alias so `widget.config(...)` works as expected
	config = configure


#============================================
class BkGroup(tkinter.ttk.LabelFrame):
	"""Drop-in replacement for Pmw.Group using ttk.LabelFrame.

	Intentionally minimal: the LabelFrame itself serves as both the
	outer frame and the interior container.
	"""

	def __init__(self, parent, tag_text: str = ''):
		"""Initialize BkGroup.

		Args:
			parent: Parent tkinter widget.
			tag_text: Text displayed on the label frame border.
		"""
		tkinter.ttk.LabelFrame.__init__(self, parent, text=tag_text)

	#============================================
	def interior(self):
		"""Return the interior container widget.

		Returns self because the LabelFrame is its own container.
		"""
		return self
