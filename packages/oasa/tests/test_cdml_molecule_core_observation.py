"""Behavior tests for the revision-bound molecule-core projection facts."""

import pytest

from oasa import cdml_document


#============================================
def test_molecule_core_observation_retains_directed_bond_fact_order() -> None:
	"""One valid directed bond keeps its authored endpoint direction and depiction."""
	session = cdml_document.CDMLDocumentSession.load(
		"<cdml><molecule id='m'><atom id='a' name='C'><point x='1cm' y='2cm'/></atom>"
		"<atom id='b' name='O'><point x='2cm' y='2cm'/></atom>"
		"<bond id='e' start='a' end='b' type='w1' wedge_width='8'/></molecule></cdml>",
	)
	observation = session.molecule_core_observation(
		cdml_document.CDMLMoleculeCoreObservationQuery(session.revision),
	)
	bond = observation.records[0].bonds[0]
	assert (bond.start_id, bond.end_id, bond.bond_type, bond.wedge_width) == ("a", "b", "w", 8.0)
	assert bond.addressable


#============================================
def test_molecule_core_observation_rejects_stale_query_without_mutation() -> None:
	"""An obsolete observation request cannot change the retained snapshot."""
	session = cdml_document.CDMLDocumentSession.load("<cdml/>")
	before = session.snapshot()
	with pytest.raises(cdml_document.CDMLRevisionConflictError):
		session.molecule_core_observation(cdml_document.CDMLMoleculeCoreObservationQuery(1))
	assert session.snapshot() == before


#============================================
def test_molecule_core_observation_keeps_idless_geometry_displayable() -> None:
	"""Legacy finite geometry can project without becoming an edit address."""
	document = cdml_document.CDMLDocument.parse(
		"<cdml><molecule><atom name='C'><point x='0cm' y='0cm'/></atom></molecule></cdml>",
		validation="compat",
	)
	atom = document.molecule_core_observation(0).records[0].atoms[0]
	assert atom.renderable and not atom.addressable


#============================================
def test_molecule_core_observation_projects_authored_font_size_as_an_integer() -> None:
	"""An authored atom font size crosses the projection boundary as its CDML integer."""
	document = cdml_document.CDMLDocument.parse(
		"<cdml><molecule id='m'><atom id='a' name='C'><point x='0cm' y='0cm'/>"
		"<font size='12'/></atom></molecule></cdml>", validation="strict",
	)
	atom = document.molecule_core_observation(0).records[0].atoms[0]

	assert atom.font_size == 12
	assert type(atom.font_size) is int


#============================================
@pytest.mark.parametrize("font_size", ("12.5", "twelve", "0", "-1"))
def test_molecule_core_observation_preserves_unprojectable_font_size(
		font_size: str,
		) -> None:
	"""Compatibility font values remain source content while their atom stays inert."""
	source = (
		"<cdml><molecule id='m'><atom id='a' name='C'><point x='0cm' y='0cm'/>"
		"<font size='%s'/></atom></molecule></cdml>" % font_size
	)
	document = cdml_document.CDMLDocument.parse(source, validation="compat")
	atom = document.molecule_core_observation(0).records[0].atoms[0]

	assert 'size="%s"' % font_size in document.serialize()
	assert not atom.renderable and atom.reason == "atom has a malformed font field"


#============================================
def test_molecule_core_observation_requires_a_durable_parent_for_child_actions() -> None:
	"""A visible child cannot become an action address without its root address."""
	document = cdml_document.CDMLDocument.parse(
		"<cdml><molecule><atom id='a' name='C'><point x='0cm' y='0cm'/></atom>"
		"<atom id='b' name='O'><point x='1cm' y='0cm'/></atom>"
		"<bond id='e' start='a' end='b' type='n1'/></molecule></cdml>",
		validation="compat",
	)
	record = document.molecule_core_observation(0).records[0]
	assert record.renderable and not record.addressable
	assert all(not child.addressable for child in (*record.atoms, *record.bonds))


#============================================
def test_molecule_core_observation_does_not_render_ambiguous_bond_endpoints() -> None:
	"""Duplicate atom IDs remain visible but cannot select an arbitrary bond endpoint."""
	document = cdml_document.CDMLDocument.parse(
		"<cdml><molecule id='m'><atom id='a' name='C'><point x='0cm' y='0cm'/></atom>"
		"<atom id='a' name='N'><point x='1cm' y='0cm'/></atom>"
		"<atom id='c' name='O'><point x='2cm' y='0cm'/></atom>"
		"<bond id='e' start='a' end='c' type='n1'/></molecule></cdml>",
		validation="compat",
	)
	bond = document.molecule_core_observation(0).records[0].bonds[0]
	assert not bond.renderable
	assert bond.reason == "bond endpoints do not name two observed direct atoms"
