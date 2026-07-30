# SPDX-License-Identifier: LGPL-3.0-or-later

"""Explicit, dependency-free normalization for PubChem PUG REST responses.

This first layer does not perform network I/O itself.  Callers provide a
transport function so GUI code, command-line tools, and tests each control
when and how a request is made.
"""

# Standard Library
import collections.abc
import dataclasses
import json
import math
import urllib.parse


#============================================
@dataclasses.dataclass(frozen=True)
class PubChemCompound:
	"""Normalized subset of one PubChem compound property record."""
	cid: int
	inchi: str
	inchikey: str
	smiles: str
	display_name: str
	synonyms: tuple[str, ...]
	molecular_formula: str
	molecular_weight: float


#============================================
class PubChemError(ValueError):
	"""Base class for explicit PubChem lookup and payload errors."""


#============================================
class PubChemNotFoundError(PubChemError):
	"""Raised when PubChem reports that the requested compound does not exist."""


#============================================
class PubChemMalformedResponseError(PubChemError):
	"""Raised when a PubChem response lacks the required compound fields."""


#============================================
class PubChemTransportError(PubChemError):
	"""Raised when the caller-supplied PubChem transport cannot fetch a response."""


#============================================
def lookup_by_cid(
	cid: int,
	transport: collections.abc.Callable[[str], str | dict],
) -> PubChemCompound:
	"""Fetch one CID through an injected transport and normalize its response.

	The transport is called once for the property endpoint and once for the
	synonym endpoint. It must return either JSON text or a decoded JSON object.
	OASA intentionally supplies no default transport, preventing library imports
	from making hidden requests.
	"""
	if isinstance(cid, bool) or not isinstance(cid, int) or cid <= 0:
		raise ValueError("PubChem CID must be a positive integer")
	if not callable(transport):
		raise TypeError("PubChem transport must be callable")
	compound = _lookup_compound(f"CID {cid}", _property_url(cid), transport)
	if compound.cid != cid:
		raise PubChemMalformedResponseError(
			f"PubChem response CID {compound.cid} does not match requested CID {cid}"
		)
	return compound


#============================================
def lookup_by_name(
	name: str,
	transport: collections.abc.Callable[[str], str | dict],
) -> PubChemCompound:
	"""Look up exactly one compound by its PubChem name through ``transport``."""
	return _lookup_by_query("name", name, transport)


#============================================
def lookup_by_inchi(
	inchi: str,
	transport: collections.abc.Callable[[str], str | dict],
) -> PubChemCompound:
	"""Look up exactly one compound by its InChI through ``transport``."""
	return _lookup_by_query("inchi", inchi, transport)


#============================================
def lookup_by_inchikey(
	inchikey: str,
	transport: collections.abc.Callable[[str], str | dict],
) -> PubChemCompound:
	"""Look up exactly one compound by its InChIKey through ``transport``."""
	return _lookup_by_query("inchikey", inchikey, transport)


#============================================
def normalize_compound_payload(
	property_payload: object,
	synonyms_payload: object | None = None,
) -> PubChemCompound:
	"""Normalize one property response and its optional separate synonym response."""
	decoded = _decode_payload(property_payload)
	_fault_error(decoded)
	properties = _property_record(decoded)
	cid = _required_positive_int(properties, "CID")
	inchi = _required_text(properties, "InChI")
	inchikey = _required_text(properties, "InChIKey")
	smiles = _smiles(properties)
	display_name = _optional_text(properties, "Title")
	synonyms = ()
	if synonyms_payload is not None:
		synonyms = _synonyms_from_payload(synonyms_payload, cid)
	molecular_formula = _required_text(properties, "MolecularFormula")
	molecular_weight = _required_weight(properties)
	compound = PubChemCompound(
		cid=cid,
		inchi=inchi,
		inchikey=inchikey,
		smiles=smiles,
		display_name=display_name,
		synonyms=synonyms,
		molecular_formula=molecular_formula,
		molecular_weight=molecular_weight,
	)
	return compound


#============================================
def _property_url(cid: int) -> str:
	"""Build the deterministic PubChem PUG REST property URL for one CID."""
	properties = "Title,MolecularFormula,MolecularWeight,SMILES,ConnectivitySMILES,InChI,InChIKey"
	url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/{properties}/JSON"
	return url


#============================================
def _query_property_url(query_type: str, query: str) -> str:
	"""Build a PUG REST property URL with a path-safe query value."""
	properties = "Title,MolecularFormula,MolecularWeight,SMILES,ConnectivitySMILES,InChI,InChIKey"
	encoded_query = urllib.parse.quote(query, safe="")
	url = (
		"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/"
		f"{query_type}/{encoded_query}/property/{properties}/JSON"
	)
	return url


#============================================
def _synonyms_url(cid: int) -> str:
	"""Build the deterministic PubChem PUG REST synonym URL for one CID."""
	url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/synonyms/JSON"
	return url


#============================================
def _fetch(
	request_description: str,
	url: str,
	transport: collections.abc.Callable[[str], str | dict],
) -> str | dict:
	"""Call the supplied transport and expose failures as domain errors."""
	try:
		payload = transport(url)
	except PubChemError:
		raise
	except Exception as exc:
		raise PubChemTransportError(f"Unable to fetch PubChem {request_description}: {exc}") from exc
	return payload


#============================================
def _lookup_by_query(
	query_type: str,
	query: str,
	transport: collections.abc.Callable[[str], str | dict],
) -> PubChemCompound:
	"""Validate a text query and fetch one normalized compound through PUG REST."""
	validated_query = _query_text(query, query_type)
	if not callable(transport):
		raise TypeError("PubChem transport must be callable")
	property_url = _query_property_url(query_type, validated_query)
	request_description = f"{query_type} query '{validated_query}'"
	compound = _lookup_compound(request_description, property_url, transport)
	return compound


#============================================
def _lookup_compound(
	request_description: str,
	property_url: str,
	transport: collections.abc.Callable[[str], str | dict],
) -> PubChemCompound:
	"""Fetch split property and synonym payloads for exactly one compound."""
	property_payload = _fetch(request_description, property_url, transport)
	decoded_properties = _decode_payload(property_payload)
	_fault_error(decoded_properties)
	properties = _property_record(decoded_properties)
	cid = _required_positive_int(properties, "CID")
	synonyms_payload = _fetch(request_description, _synonyms_url(cid), transport)
	compound = normalize_compound_payload(property_payload, synonyms_payload)
	return compound


#============================================
def _query_text(query: str, query_type: str) -> str:
	"""Return one stripped non-empty PubChem query string."""
	if not isinstance(query, str):
		raise ValueError(f"PubChem {query_type} query must be non-empty text")
	text = query.strip()
	if not text:
		raise ValueError(f"PubChem {query_type} query must be non-empty text")
	return text


#============================================
def _decode_payload(payload: object) -> dict:
	"""Return a decoded PubChem object or raise a domain-specific error."""
	if isinstance(payload, str):
		try:
			decoded = json.loads(payload)
		except json.JSONDecodeError as exc:
			raise PubChemMalformedResponseError(f"PubChem returned invalid JSON: {exc}") from exc
	elif isinstance(payload, dict):
		decoded = payload
	else:
		raise PubChemMalformedResponseError("PubChem response must be JSON text or an object")
	if not isinstance(decoded, dict):
		raise PubChemMalformedResponseError("PubChem JSON root must be an object")
	return decoded


#============================================
def _fault_error(payload: dict) -> None:
	"""Translate a PubChem PUG REST fault object into an explicit domain error."""
	if "Fault" not in payload:
		return
	fault = payload["Fault"]
	if not isinstance(fault, dict):
		raise PubChemMalformedResponseError("PubChem Fault must be an object")
	code = _optional_text(fault, "Code")
	message = _optional_text(fault, "Message")
	details = ": ".join(part for part in (code, message) if part)
	if "notfound" in code.lower() or "not found" in message.lower():
		raise PubChemNotFoundError(details or "PubChem compound was not found")
	raise PubChemMalformedResponseError(details or "PubChem returned a fault response")


#============================================
def _property_record(payload: dict) -> dict:
	"""Extract exactly one property record from a PUG REST property payload."""
	try:
		properties = payload["PropertyTable"]["Properties"]
	except (KeyError, TypeError) as exc:
		raise PubChemMalformedResponseError("PubChem response has no PropertyTable.Properties") from exc
	if not isinstance(properties, list) or len(properties) != 1:
		raise PubChemMalformedResponseError("PubChem response must contain exactly one compound")
	record = properties[0]
	if not isinstance(record, dict):
		raise PubChemMalformedResponseError("PubChem property record must be an object")
	return record


#============================================
def _required_positive_int(record: dict, key: str) -> int:
	"""Return one positive integer property or raise a clear payload error."""
	value = record.get(key)
	if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
		raise PubChemMalformedResponseError(f"PubChem property '{key}' must be a positive integer")
	return value


#============================================
def _required_text(record: dict, key: str) -> str:
	"""Return one non-empty text property or raise a clear payload error."""
	value = _optional_text(record, key)
	if not value:
		raise PubChemMalformedResponseError(f"PubChem property '{key}' must be non-empty text")
	return value


#============================================
def _optional_text(record: dict, key: str) -> str:
	"""Normalize a genuine optional PubChem text property."""
	value = record.get(key, "")
	if value == "":
		return ""
	if not isinstance(value, str):
		raise PubChemMalformedResponseError(f"PubChem property '{key}' must be text")
	text = value.strip()
	return text


#============================================
def _smiles(record: dict) -> str:
	"""Prefer isomeric SMILES while accepting legacy canonical property names."""
	for key in ("SMILES", "IsomericSMILES", "ConnectivitySMILES", "CanonicalSMILES"):
		value = _optional_text(record, key)
		if value:
			return value
	raise PubChemMalformedResponseError("PubChem response has no usable SMILES property")


#============================================
def _synonyms_from_payload(payload: object, property_cid: int) -> tuple[str, ...]:
	"""Normalize PubChem's InformationList synonym response for one CID."""
	decoded = _decode_payload(payload)
	_fault_error(decoded)
	try:
		information = decoded["InformationList"]["Information"]
	except (KeyError, TypeError) as exc:
		raise PubChemMalformedResponseError("PubChem response has no InformationList.Information") from exc
	if not isinstance(information, list) or len(information) != 1:
		raise PubChemMalformedResponseError("PubChem synonym response must contain exactly one compound")
	record = information[0]
	if not isinstance(record, dict):
		raise PubChemMalformedResponseError("PubChem synonym record must be an object")
	synonym_cid = _required_positive_int(record, "CID")
	if synonym_cid != property_cid:
		raise PubChemMalformedResponseError(
			f"PubChem synonym CID {synonym_cid} does not match property CID {property_cid}"
		)
	values = record.get("Synonym", [])
	if not isinstance(values, list):
		raise PubChemMalformedResponseError("PubChem synonym record must contain a Synonym list")
	if not values:
		return ()
	normalized = []
	for value in values:
		if not isinstance(value, str):
			raise PubChemMalformedResponseError("PubChem synonyms must be text")
		text = value.strip()
		if text and text not in normalized:
			normalized.append(text)
	result = tuple(normalized)
	return result


#============================================
def _required_weight(record: dict) -> float:
	"""Normalize PubChem molecular weight values accepted as JSON numbers or text."""
	value = record.get("MolecularWeight")
	if isinstance(value, bool) or not isinstance(value, (int, float, str)):
		raise PubChemMalformedResponseError("PubChem property 'MolecularWeight' must be numeric")
	try:
		weight = float(value)
	except ValueError as exc:
		raise PubChemMalformedResponseError("PubChem property 'MolecularWeight' must be numeric") from exc
	if not math.isfinite(weight) or weight <= 0:
		raise PubChemMalformedResponseError(
			"PubChem property 'MolecularWeight' must be a finite positive number"
		)
	return weight
