"""View menu action registrations for BKChem."""

# local repo modules
from bkchem.actions.action_registry import MenuAction


#============================================
def register_view_actions(registry, app) -> None:
	"""Register all View menu actions.

	Args:
		registry: The ActionRegistry to register actions with.
		app: The application object providing paper zoom methods.
	"""
	# zoom in on the paper
	registry.register(MenuAction(
		id='view.zoom_in',
		label_key='Zoom In',
		help_key='Zoom in',
		accelerator='(C-+)',
		handler=lambda: app.paper.zoom_in(),
		enabled_when=None,
	))
	# zoom out on the paper
	registry.register(MenuAction(
		id='view.zoom_out',
		label_key='Zoom Out',
		help_key='Zoom out',
		accelerator='(C--)',
		handler=lambda: app.paper.zoom_out(),
		enabled_when=None,
	))
	# reset zoom level to 100%
	registry.register(MenuAction(
		id='view.zoom_reset',
		label_key='Zoom to 100%',
		help_key='Reset zoom to 100%',
		accelerator='(C-0)',
		handler=lambda: app.paper.zoom_reset(),
		enabled_when=None,
	))
	# fit drawing to window
	registry.register(MenuAction(
		id='view.zoom_to_fit',
		label_key='Zoom to Fit',
		help_key='Fit drawing to window',
		accelerator=None,
		handler=lambda: app.paper.zoom_to_fit(),
		enabled_when=None,
	))
	# fit and center on drawn content
	registry.register(MenuAction(
		id='view.zoom_to_content',
		label_key='Zoom to Content',
		help_key='Fit and center on drawn content',
		accelerator=None,
		handler=lambda: app.paper.zoom_to_content(),
		enabled_when=None,
	))
