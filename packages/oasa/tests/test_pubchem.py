# SPDX-License-Identifier: LGPL-3.0-or-later

"""Offline unit tests for the explicit OASA PubChem response boundary."""

# Standard Library
import json

# Third Party
import pytest

# local repo modules
import oasa.pubchem


#============================================
class RecordingTransport:
	"""Offline PUG REST fixture that records path choices made by a lookup."""
	def __init__(self) -> None:
		self.calls: list[str] = []

	def __call__(self, url: str) -> dict:
		self.calls.append(url)
		if "/synonyms/" in url:
			return {
				"InformationList": {
					"Information": [{"CID": 962, "Synonym": ["water", "oxidane"]}]
				}
			}
		return {
			"PropertyTable": {
				"Properties": [{
					"CID": 962,
					"MolecularFormula": "H2O",
					"MolecularWeight": 18.015,
					"ConnectivitySMILES": "O",
					"InChI": "InChI=1S/H2O/h1H2",
					"InChIKey": "XLYOFNOQVPJJNP-UHFFFAOYSA-N",
				}]
			}
		}


#============================================
def test_normalize_compound_payload_preserves_chemical_identifiers() -> None:
	payload = {
		"PropertyTable": {
			"Properties": [{
				"CID": 2244,
				"Title": "  Aspirin  ",
				"MolecularFormula": "C9H8O4",
				"MolecularWeight": "180.16",
				"SMILES": "CC(=O)OC1=CC=CC=C1C(=O)O",
				"InChI": "InChI=1S/C9H8O4",
				"InChIKey": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
			}]
		}
	}
	synonyms_payload = {
		"InformationList": {
			"Information": [{
				"CID": 2244,
				"Synonym": ["Aspirin", " acetylsalicylic acid ", "Aspirin"],
			}]
		}
	}
	compound = oasa.pubchem.normalize_compound_payload(
		json.dumps(payload, sort_keys=True), synonyms_payload
	)
	assert (
		compound.cid,
		compound.display_name,
		compound.synonyms,
		compound.molecular_formula,
		compound.molecular_weight,
	) == (2244, "Aspirin", ("Aspirin", "acetylsalicylic acid"), "C9H8O4", 180.16)


#============================================
def test_lookup_by_cid_uses_only_the_supplied_transport() -> None:
	requests = []

	def transport(url: str) -> dict:
		requests.append(url)
		if "/synonyms/" in url:
			return {
				"InformationList": {
					"Information": [{"CID": 962, "Synonym": ["water", "oxidane"]}]
				}
			}
		return {
			"PropertyTable": {
				"Properties": [{
					"CID": 962,
					"MolecularFormula": "H2O",
					"MolecularWeight": 18.015,
					"ConnectivitySMILES": "O",
					"InChI": "InChI=1S/H2O/h1H2",
					"InChIKey": "XLYOFNOQVPJJNP-UHFFFAOYSA-N",
				}]
			}
		}

	compound = oasa.pubchem.lookup_by_cid(962, transport)
	assert (compound.smiles, compound.synonyms, compound.cid) == ("O", ("water", "oxidane"), 962)
	assert "/property/" in requests[0] and "/synonyms/" in requests[1]


#============================================
def test_normalize_compound_payload_reports_a_pubchem_not_found_fault() -> None:
	payload = {"Fault": {"Code": "PUGREST.NotFound", "Message": "No compound found"}}
	with pytest.raises(oasa.pubchem.PubChemNotFoundError, match="NotFound"):
		oasa.pubchem.normalize_compound_payload(payload)


#============================================
def test_normalize_compound_payload_rejects_missing_identifiers() -> None:
	payload = {"PropertyTable": {"Properties": [{"CID": 962}]}}
	with pytest.raises(oasa.pubchem.PubChemMalformedResponseError, match="InChI"):
		oasa.pubchem.normalize_compound_payload(payload)


#============================================
def test_normalize_compound_payload_rejects_synonym_cid_mismatch() -> None:
	properties = {
		"PropertyTable": {
			"Properties": [{
				"CID": 962,
				"MolecularFormula": "H2O",
				"MolecularWeight": 18.015,
				"SMILES": "O",
				"InChI": "InChI=1S/H2O/h1H2",
				"InChIKey": "XLYOFNOQVPJJNP-UHFFFAOYSA-N",
			}]
		}
	}
	synonyms = {"InformationList": {"Information": [{"CID": 2244, "Synonym": ["Aspirin"]}]}}
	with pytest.raises(oasa.pubchem.PubChemMalformedResponseError, match="synonym CID"):
		oasa.pubchem.normalize_compound_payload(properties, synonyms)


#============================================
def test_normalize_compound_payload_rejects_non_finite_molecular_weight() -> None:
	payload = {
		"PropertyTable": {
			"Properties": [{
				"CID": 962,
				"MolecularFormula": "H2O",
				"MolecularWeight": "nan",
				"SMILES": "O",
				"InChI": "InChI=1S/H2O/h1H2",
				"InChIKey": "XLYOFNOQVPJJNP-UHFFFAOYSA-N",
			}]
		}
	}
	with pytest.raises(oasa.pubchem.PubChemMalformedResponseError, match="finite"):
		oasa.pubchem.normalize_compound_payload(payload)


#============================================
def test_lookup_by_cid_wraps_transport_failures() -> None:
	def transport(url: str) -> None:
		raise RuntimeError("offline")

	with pytest.raises(oasa.pubchem.PubChemTransportError, match="CID 962"):
		oasa.pubchem.lookup_by_cid(962, transport)


#============================================
def test_lookup_by_name_encodes_the_query_and_fetches_synonyms() -> None:
	transport = RecordingTransport()
	compound = oasa.pubchem.lookup_by_name("water + salt", transport)
	assert (compound.cid, compound.synonyms) == (962, ("water", "oxidane"))
	assert "/name/water%20%2B%20salt/property/" in transport.calls[0]


#============================================
def test_lookup_by_inchi_encodes_reserved_path_characters() -> None:
	transport = RecordingTransport()
	compound = oasa.pubchem.lookup_by_inchi("InChI=1S/H2O/h1H2", transport)
	assert compound.inchi == "InChI=1S/H2O/h1H2"
	assert "/inchi/InChI%3D1S%2FH2O%2Fh1H2/property/" in transport.calls[0]


#============================================
def test_lookup_by_inchikey_uses_the_returned_cid_for_synonyms() -> None:
	transport = RecordingTransport()
	compound = oasa.pubchem.lookup_by_inchikey("XLYOFNOQVPJJNP-UHFFFAOYSA-N", transport)
	assert (compound.cid, compound.display_name) == (962, "")
	assert "/cid/962/synonyms/" in transport.calls[1]


#============================================
def test_lookup_by_name_rejects_invalid_query_text() -> None:
	transport = RecordingTransport()
	with pytest.raises(ValueError, match="non-empty text"):
		oasa.pubchem.lookup_by_name(" ", transport)
	query: object = None
	with pytest.raises(ValueError, match="non-empty text"):
		oasa.pubchem.lookup_by_inchi(query, transport)


#============================================
def test_lookup_by_name_rejects_ambiguous_property_payload() -> None:
	def transport(url: str) -> dict:
		if "/synonyms/" in url:
			return {"InformationList": {"Information": []}}
		return {
			"PropertyTable": {
				"Properties": [{"CID": 1}, {"CID": 2}]
			}
		}

	with pytest.raises(oasa.pubchem.PubChemMalformedResponseError, match="exactly one"):
		oasa.pubchem.lookup_by_name("ambiguous", transport)
