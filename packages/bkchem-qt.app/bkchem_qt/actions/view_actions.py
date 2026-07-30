"""View menu action registrations for BKChem-Qt."""

# local repo modules
from bkchem_qt.actions.action_registry import MenuAction


#============================================
def register_view_actions(registry: object, app: object) -> None:
	"""Register all View menu actions.

	Args:
		registry: ActionRegistry instance to register actions with.
		app: The main BKChem-Qt application object providing handler methods.
	"""
	# zoom in on the canvas
	registry.register(MenuAction(
		id='view.zoom_in',
		label_key='Zoom In',
		help_key='Zoom in',
		accelerator='(C-+)',
		handler=app.on_zoom_in,
		enabled_when=None,
	))

	# zoom out on the canvas
	registry.register(MenuAction(
		id='view.zoom_out',
		label_key='Zoom Out',
		help_key='Zoom out',
		accelerator='(C--)',
		handler=app.on_zoom_out,
		enabled_when=None,
	))

	# reset zoom level to 100%
	registry.register(MenuAction(
		id='view.zoom_reset',
		label_key='Zoom to 100%',
		help_key='Reset zoom to 100%',
		accelerator='(C-0)',
		handler=app.on_reset_zoom,
		enabled_when=None,
	))

	# zoom to page
	registry.register(MenuAction(
		id='view.zoom_to_fit',
		label_key='Zoom to Page',
		help_key='Fit drawing to page',
		accelerator=None,
		handler=app.on_zoom_to_fit,
		enabled_when=None,
	))

	# fit and center on drawn content
	registry.register(MenuAction(
		id='view.zoom_to_content',
		label_key='Zoom to Content',
		help_key='Fit and center on drawn content',
		accelerator=None,
		handler=app.on_zoom_to_content,
		enabled_when=None,
	))
