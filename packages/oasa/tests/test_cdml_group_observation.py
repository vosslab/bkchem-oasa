"""Behavioral coverage for backend-owned direct group projection facts."""

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document


_CDML = """<cdml version="0.15" xmlns="http://www.freesoftware.fsf.org/bkchem/cdml">
<molecule id="m1"><atom id="a1" name="C"><point x="0cm" y="0cm"/></atom>
<group id="g_builtin" name="Me" group-type="builtin"><point x="1cm" y="0cm"/></group>
<group id="g_implicit" name="COOH" group-type="implicit"><point x="2cm" y="0cm"/></group>
<group id="g_rich" name="X" group-type="explicit"><point x="3cm" y="0cm"/><mark/></group>
<bond id="b1" start="a1" end="g_implicit" type="n1"/></molecule>
<foreign:group xmlns:foreign="urn:foreign" id="g_foreign"/></cdml>"""


#============================================
def test_group_observation_exposes_only_backend_approved_group_actions() -> None:
	"""Builtin/explicit labels display while only the exact implicit form expands."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	snapshot = session.snapshot()
	observation = session.group_observation(
		oasa.cdml_document.CDMLGroupObservationQuery(snapshot.revision),
	)
	records = {record.group_type: record for record in observation.records if record.group_type}
	assert records["builtin"].disposition == "selectable" and not records["builtin"].implicit_expandable
	assert records["implicit"].implicit_expandable and records["explicit"].disposition == "display-only"


#============================================
def test_group_observation_rejects_stale_revision_without_mutation() -> None:
	"""A stale group observation cannot observe or change a newer snapshot."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	with pytest.raises(oasa.cdml_document.CDMLRevisionConflictError):
		session.group_observation(oasa.cdml_document.CDMLGroupObservationQuery(1))
	assert session.snapshot().revision == 0


#============================================
def test_group_observation_makes_foreign_duplicate_and_malformed_groups_inert() -> None:
	"""Local-name lookalikes and ambiguous IDs never receive action addresses."""
	cdml = """<cdml version="0.15" xmlns="http://www.freesoftware.fsf.org/bkchem/cdml"
	 xmlns:v="urn:vendor"><molecule id="m1"><atom id="a1" name="C"><point x="0cm" y="0cm"/></atom>
	<v:group id="foreign" name="F" group-type="builtin"><point x="1cm" y="0cm"/></v:group>
	<group id="duplicate" name="D1" group-type="builtin"><point x="2cm" y="0cm"/></group>
	<group id="duplicate" name="D2" group-type="builtin"><point x="3cm" y="0cm"/></group>
	<group id="bad" name="B" group-type="builtin"><point x="nope" y="0cm"/></group>
	</molecule></cdml>"""
	document = oasa.cdml_document.CDMLDocument.parse(cdml, validation="compat")
	observation = document.group_observation(0)
	inert = [record for record in observation.records if record.disposition == "display-only"]
	assert {record.name for record in inert} == {"F", "D1", "D2", "B"}
	assert all(record.molecule_id is None and record.group_id is None for record in inert)
