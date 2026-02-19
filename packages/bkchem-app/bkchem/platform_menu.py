"""Platform-aware menu adapter for BKChem.

Wraps Pmw.MainMenuBar (macOS) and Pmw.MenuBar (Linux/Windows) behind
a uniform interface so the menu builder does not need to know which
platform is in use.
"""

# Standard Library
import sys


#============================================
class PlatformMenuAdapter:
	"""Uniform wrapper around Pmw menubar widgets."""

	#============================================
	def __init__(self, parent_window, balloon, main_frame=None):
		"""Create the appropriate menubar for the current platform.

		Args:
			parent_window: the top-level Tk window (for MainMenuBar on macOS)
			balloon: the Pmw.Balloon for status help
			main_frame: the main frame widget (for MenuBar on Linux/Windows)
		"""
		# import Pmw here to allow testing without Tk
		import Pmw
		from tkinter import Frame, RAISED

		# detect platform once and store for later use
		self._use_system_menubar: bool = sys.platform == "darwin"
		if self._use_system_menubar:
			# macOS uses native system menubar via MainMenuBar
			self._menubar = Pmw.MainMenuBar(parent_window, balloon=balloon)
			parent_window.configure(menu=self._menubar)
		else:
			# Linux/Windows uses an in-window MenuBar on a frame
			from bkchem import bkchem_config
			menuf = Frame(main_frame, relief=RAISED, bd=bkchem_config.border_width)
			menuf.grid(row=0, sticky="we")
			self._menubar = Pmw.MenuBar(menuf, balloon=balloon)
			self._menubar.pack(side="left", expand=1, fill="both")

	#============================================
	def add_menu(self, name: str, help_text: str, side: str = 'left') -> None:
		"""Add a top-level menu.

		Args:
			name: menu label (translated)
			help_text: balloon help text
			side: 'left' or 'right' (ignored on macOS)
		"""
		if self._use_system_menubar:
			# macOS MainMenuBar does not support side argument
			self._menubar.addmenu(name, help_text)
		else:
			self._menubar.addmenu(name, help_text, side=side)

	#============================================
	def add_command(self, menu_name: str, label: str,
					accelerator: str, help_text: str,
					command: object) -> None:
		"""Add a command entry to a menu.

		Args:
			menu_name: parent menu label
			label: command label
			accelerator: keyboard shortcut string or None
			help_text: status bar help
			command: callable to invoke
		"""
		self._menubar.addmenuitem(
			menu_name, 'command',
			label=label, accelerator=accelerator,
			statusHelp=help_text, command=command,
		)

	#============================================
	def add_separator(self, menu_name: str) -> None:
		"""Add a separator to a menu.

		Args:
			menu_name: parent menu label
		"""
		self._menubar.addmenuitem(menu_name, 'separator')

	#============================================
	def add_cascade(self, menu_name: str, cascade_name: str,
					help_text: str) -> None:
		"""Add a cascade submenu.

		Args:
			menu_name: parent menu label
			cascade_name: cascade label
			help_text: balloon help text
		"""
		self._menubar.addcascademenu(
			menu_name, cascade_name, help_text, tearoff=0,
		)

	#============================================
	def add_command_to_cascade(self, cascade_name: str, label: str,
								help_text: str, command: object) -> None:
		"""Add a command to an existing cascade submenu.

		Args:
			cascade_name: the cascade to add to
			label: command label
			help_text: status help text
			command: callable to invoke
		"""
		self._menubar.addmenuitem(
			cascade_name, 'command',
			label=label, statusHelp=help_text, command=command,
		)

	#============================================
	def get_menu_component(self, menu_name: str):
		"""Get the underlying Tk menu widget for a menu.

		Args:
			menu_name: the menu label

		Returns:
			the Tk Menu widget
		"""
		return self._menubar.component(menu_name + '-menu')

	#============================================
	def set_item_state(self, menu_name: str, label: str,
						enabled: bool) -> None:
		"""Enable or disable a menu item.

		Args:
			menu_name: parent menu label
			label: the item label to configure
			enabled: True for normal, False for disabled
		"""
		state = 'normal' if enabled else 'disabled'
		menu_widget = self.get_menu_component(menu_name)
		menu_widget.entryconfigure(label, state=state)
