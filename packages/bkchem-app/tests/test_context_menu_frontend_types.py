"""Context-menu configuration targets stay on the BKChem presentation layer."""

# PIP3 modules
import pytest

# local repo modules
import bkchem.atom_lib
import bkchem.classes
import bkchem.context_menu
import bkchem.queryatom_lib


#============================================
@pytest.mark.parametrize(
	"vertex_class",
	(bkchem.atom_lib.BkAtom, bkchem.queryatom_lib.BkQueryatom),
)
def test_frontend_atom_types_receive_context_menu_configuration(
		vertex_class: type,
		) -> None:
	"""Each frontend atom type receives symbol and group menu choices."""
	standard = bkchem.classes.standard()
	vertex = vertex_class(standard=standard)
	items, _configured = bkchem.context_menu.configuration_items([vertex])
	assert "Cl" in [choice[3] for choice in items["Atom symbol"]]
	assert "CHO" in [choice[3] for choice in items["Group"]]
