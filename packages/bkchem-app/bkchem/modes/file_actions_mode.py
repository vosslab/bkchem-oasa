"""File actions mode for BKChem Tk.

Provides New, Open, Save, and Save As as submode buttons in the
mode toolbar ribbon. Selecting a submode triggers the corresponding
file operation on the main application.
"""

from bkchem.modes.modes_lib import basic_mode
from bkchem.singleton_store import Store


# maps submode keys to Store.app method names
_FILE_ACTION_METHODS = {
	'new': 'file_new',
	'open': 'file_open',
	'save': 'file_save',
	'save_as': 'file_saveas',
}


#============================================
class file_actions_mode(basic_mode):
	"""Mode that exposes file operations as submode buttons.

	Each submode button (New, Open, Save, Save As) dispatches to the
	corresponding file handler on the main application.
	"""

	#============================================
	def __init__(self):
		"""Initialize the file actions mode."""
		basic_mode.__init__(self)

	#============================================
	def on_submode_switch(self, i, name):
		"""Dispatch to the appropriate file handler.

		Args:
			i: Group index of the changed submode.
			name: Key string of the newly selected submode.
		"""
		method_name = _FILE_ACTION_METHODS.get(name)
		if method_name is None:
			return
		handler = getattr(Store.app, method_name, None)
		if handler is not None:
			handler()
