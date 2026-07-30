"""Regression tests for molecule graph factories."""

# local repo modules
import oasa.molecule_lib
import oasa.oasa_config


#============================================
class _FrontendLikeMolecule:
	"""Sentinel for the legacy frontend-wide graph configuration."""


#============================================
def test_create_graph_uses_the_calling_molecule_class(monkeypatch: object) -> None:
	"""OASA graph operations must not inherit a frontend global class."""
	monkeypatch.setattr(
		oasa.oasa_config.Config,
		"molecule_class",
		_FrontendLikeMolecule,
	)
	graph = oasa.molecule_lib.Molecule().create_graph()
	assert isinstance(graph, oasa.molecule_lib.Molecule)
