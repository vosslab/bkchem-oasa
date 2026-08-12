"""Route Edit-mode double-clicks from projected items to public edit actions."""

# Standard Library
import collections.abc

# local repo modules
import bkchem_qt.actions.object_actions
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.canvas.items.text_item


#============================================
def open_item_editor(
		item: object,
		atom_editor: collections.abc.Callable[[object], None],
		bond_editor: collections.abc.Callable[[object], None],
		scene: object | None,
		window: object | None,
		) -> None:
	"""Route one projected item to its authoritative detached editing action.

	Atoms and bonds use their captured property editors.  The resulting backend
	patch is revision-bound and either installs one canonical reprojection or
	leaves the authoritative snapshot, history, and dirty state unchanged.
	Text keeps no scene wrapper after selection: the public action re-resolves the
	current durable document selection before it opens the detached dialog.
	"""
	if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
		atom_editor(item)
		return
	if isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem):
		bond_editor(item)
		return
	if not isinstance(item, bkchem_qt.canvas.items.text_item.TextItem):
		return
	if scene is None or window is None:
		return
	scene.clearSelection()
	item.setSelected(True)
	bkchem_qt.actions.object_actions.edit_selected_text(window)
