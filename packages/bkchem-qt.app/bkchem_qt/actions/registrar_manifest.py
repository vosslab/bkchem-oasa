"""Immutable action-registrar manifest shared by runtime and bundle planning."""


# The order is deliberate: it is the stable startup order for action
# registration and the source authority for frozen hidden imports.
ACTION_REGISTRAR_MODULES = (
	"bkchem_qt.actions.align_actions",
	"bkchem_qt.actions.chemistry_actions",
	"bkchem_qt.actions.edit_actions",
	"bkchem_qt.actions.file_actions",
	"bkchem_qt.actions.haworth_actions",
	"bkchem_qt.actions.help_actions",
	"bkchem_qt.actions.insert_actions",
	"bkchem_qt.actions.object_actions",
	"bkchem_qt.actions.options_actions",
	"bkchem_qt.actions.plugins_actions",
	"bkchem_qt.actions.pubchem_actions",
	"bkchem_qt.actions.repair_actions",
	"bkchem_qt.actions.view_actions",
)


#============================================
def registrar_name(module_name: str) -> str:
	"""Return the required registrar function name for one manifest module.

	Args:
		module_name: Qualified module name from ``ACTION_REGISTRAR_MODULES``.

	Returns:
		The public registrar function name defined by that module.
	"""
	return "register_%s" % module_name.rsplit(".", 1)[-1]
