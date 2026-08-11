"""Exact-revision molecular composition facts from authoritative CDML."""

# Standard Library
import dataclasses

# local repo modules
import oasa.cdml_writer
import oasa.cdml_xml
import oasa.periodic_table


class CDMLMoleculeSummaryError(ValueError):
	"""Raised when an authoritative molecule summary cannot be produced."""


@dataclasses.dataclass(frozen=True)
class CDMLMoleculeSummaryQuery:
	"""One exact-revision query for ordered direct-root molecule IDs."""

	expected_revision: int
	molecule_ids: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class CDMLFormulaSummary:
	"""Immutable formula, mass, and elemental-composition facts."""

	formula: str
	molecular_weight: float
	monoisotopic_mass: float
	element_counts: tuple[tuple[str, int], ...]
	mass_percentages: tuple[tuple[str, float], ...]


@dataclasses.dataclass(frozen=True)
class CDMLMoleculeSummaryRecord:
	"""Chemistry facts for one requested direct-root molecule."""

	molecule_id: str
	name: str
	atom_count: int
	bond_count: int
	chemistry: CDMLFormulaSummary


@dataclasses.dataclass(frozen=True)
class CDMLMoleculeSummaryObservation:
	"""One immutable batch result from a single authoritative revision."""

	revision: int
	records: tuple[CDMLMoleculeSummaryRecord, ...]
	aggregate: CDMLFormulaSummary


#============================================
def _local_name(element: object) -> str:
	"""Return a DOM local name without leaking namespace-prefix spelling."""
	return element.localName or element.tagName.split(":")[-1]


#============================================
def _is_core(element: object) -> bool:
	"""Return whether an element belongs to the editable CDML namespace."""
	return getattr(element, "namespaceURI", None) in (
		None, "", oasa.cdml_xml.CDML_NAMESPACE_URI,
	)


#============================================
def _direct_root_molecule(root: object, identifier: str) -> object:
	"""Resolve exactly one direct core molecule by durable ID."""
	for child in root.childNodes:
		if (
			child.nodeType == child.ELEMENT_NODE
			and _is_core(child) and _local_name(child) == "molecule"
			and child.getAttribute("id") == identifier
		):
			return child
	raise CDMLMoleculeSummaryError(
		"molecule summary target is not a direct editable molecule: %s" % identifier,
	)


#============================================
def _validate_query(query: object) -> tuple[str, ...]:
	"""Validate the immutable batch grammar before reading the document."""
	if type(query) is not CDMLMoleculeSummaryQuery:
		raise CDMLMoleculeSummaryError("molecule summary requires an exact query")
	if type(query.expected_revision) is not int:
		raise CDMLMoleculeSummaryError("molecule summary expected_revision must be an int")
	if type(query.molecule_ids) is not tuple or not query.molecule_ids:
		raise CDMLMoleculeSummaryError(
			"molecule summary molecule_ids must be a nonempty tuple",
		)
	if any(type(identifier) is not str or not identifier for identifier in query.molecule_ids):
		raise CDMLMoleculeSummaryError(
			"molecule summary IDs must be nonempty strings",
		)
	if len(set(query.molecule_ids)) != len(query.molecule_ids):
		raise CDMLMoleculeSummaryError("molecule summary IDs must be unique")
	return query.molecule_ids


#============================================
def _formula_summary(formula: object) -> CDMLFormulaSummary:
	"""Freeze one OASA formula into frontend-neutral scalar facts."""
	ordered_symbols = tuple(formula.sorted_keys())
	counts = tuple((symbol, int(formula[symbol])) for symbol in ordered_symbols)
	composition = oasa.periodic_table.dict_to_composition(formula)
	percentages = tuple(
		(symbol, float(composition[symbol])) for symbol in ordered_symbols
	)
	return CDMLFormulaSummary(
		formula=str(formula),
		molecular_weight=float(formula.get_molecular_weight()),
		monoisotopic_mass=float(formula.get_exact_molecular_mass()),
		element_counts=counts,
		mass_percentages=percentages,
	)


#============================================
def query_session(
		session: object, query: object,
		) -> CDMLMoleculeSummaryObservation:
	"""Calculate ordered molecule and aggregate facts without mutation."""
	molecule_ids = _validate_query(query)
	session._check_expected_revision(query.expected_revision)
	root = session._document._dom_document.documentElement
	records = []
	aggregate = oasa.periodic_table.formula_dict()
	for identifier in molecule_ids:
		element = _direct_root_molecule(root, identifier)
		try:
			molecule = oasa.cdml_writer.read_direct_core_cdml_molecule_element(element)
			if molecule is None:
				raise ValueError("CDML molecule has no supported chemistry conversion")
			formula = molecule.get_formula_dict()
		except (AttributeError, IndexError, KeyError, TypeError, ValueError) as error:
			raise CDMLMoleculeSummaryError(
				"molecule summary is unavailable for direct-root molecule: %s" % identifier,
			) from error
		aggregate += formula
		records.append(CDMLMoleculeSummaryRecord(
			molecule_id=identifier,
			name=element.getAttribute("name"),
			atom_count=len(molecule.vertices),
			bond_count=len(molecule.edges),
			chemistry=_formula_summary(formula),
		))
	return CDMLMoleculeSummaryObservation(
		revision=session._revision,
		records=tuple(records),
		aggregate=_formula_summary(aggregate),
	)
