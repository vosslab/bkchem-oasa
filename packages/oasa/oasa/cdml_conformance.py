"""Read-only CDML compatibility and authored-profile conformance checks."""

# Standard Library
import dataclasses
import json
import pathlib

# local repo modules
import oasa.cdml_document
import oasa.cdml_xml


_COMPAT_PROFILE = "compat"
_AUTHORED_PROFILE = "authored-26.07"
_SUPPORTED_PROFILES = frozenset({_COMPAT_PROFILE, _AUTHORED_PROFILE})
_CORPUS_SCHEMA = "cdml-conformance-corpus-1"
_AUTHORED_SELECTABLE_DIRECT_CHILD_NAMES = frozenset({
	"arrow", "circle", "molecule", "oval", "plus", "polygon", "polyline",
	"reaction", "rect", "square", "text",
})
_AUTHORED_REACTION_ROLE_TARGET_NAMES = {
	"reactant": "molecule",
	"product": "molecule",
	"arrow": "arrow",
	"condition": "text",
	"plus": "plus",
}


@dataclasses.dataclass(frozen=True)
class CDMLConformanceIssue:
	"""One stable, serializable CDML conformance finding."""

	code: str
	severity: str
	path: str
	message: str


@dataclasses.dataclass(frozen=True)
class CDMLConformanceReport:
	"""One immutable report for one explicitly selected conformance profile."""

	profile: str
	issues: tuple[CDMLConformanceIssue, ...]

	@property
	def is_valid(self) -> bool:
		"""Return whether the selected profile found no error-severity issue."""
		valid = not any(issue.severity == "error" for issue in self.issues)
		return valid


@dataclasses.dataclass(frozen=True)
class CDMLConformanceCaseResult:
	"""One manifest case with its requested profile reports and preservation result."""

	case_id: str
	reports: tuple[CDMLConformanceReport, ...]
	preservation_matches: bool


#============================================
#============================================
def _parse_view(text: str) -> oasa.cdml_xml.CDMLXMLInspection | None:
	"""Parse one hardened, node-free XML view or return none for unsafe XML."""
	try:
		view = oasa.cdml_xml.inspect_cdml_xml(text.encode("utf-8"))
	except (UnicodeError, oasa.cdml_xml.CDMLXMLParseError):
		return None
	return view


#============================================
def _is_compatibility_root(view: oasa.cdml_xml.CDMLXMLInspection) -> bool:
	"""Return whether the immutable root metadata describes compatible CDML."""
	is_compatible = (
		view.local_name == "cdml"
		and view.namespace in ("", oasa.cdml_document.CDML_NAMESPACE_URI)
	)
	return is_compatible


#============================================
def _document_issue(issue: oasa.cdml_document.CDMLIssue) -> CDMLConformanceIssue:
	"""Map backend identity/reference findings to stable conformance diagnostics."""
	code_map = {
		"duplicate_id": "CDML-ID-001",
		"provisional_id": "CDML-ID-002",
		"malformed_provisional_id": "CDML-ID-002",
		"unresolved_reference": "CDML-REF-001",
		"provisional_reference": "CDML-REF-002",
		"malformed_provisional_reference": "CDML-REF-002",
		"unresolved_fragment_member": "CDML-REF-003",
	}
	code = code_map[issue.code]
	conformance_issue = CDMLConformanceIssue(
		code=code,
		severity="error",
		path=issue.path,
		message=issue.message,
	)
	return conformance_issue


#============================================
def _xml_issue() -> CDMLConformanceIssue:
	"""Return the stable unsafe-or-malformed XML diagnostic."""
	issue = CDMLConformanceIssue(
		"CDML-XML-001",
		"error",
		"/",
		"CDML XML cannot be safely parsed",
	)
	return issue


#============================================
def _root_issue() -> CDMLConformanceIssue:
	"""Return the stable incompatible-root diagnostic."""
	issue = CDMLConformanceIssue(
		"CDML-ROOT-001",
		"error",
		"/",
		"root must be a CDML element in an accepted compatibility namespace",
	)
	return issue


#============================================
def _authored_selectable_id_issues(
		document: oasa.cdml_document.CDMLDocument,
		) -> tuple[CDMLConformanceIssue, ...]:
	"""Return profile findings for direct selectable records without durable IDs."""
	issues = []
	for record in document.objects():
		if record.opaque or record.local_name not in _AUTHORED_SELECTABLE_DIRECT_CHILD_NAMES:
			continue
		if record.identifier and record.identifier.strip():
			continue
		issues.append(CDMLConformanceIssue(
			"CDML-A2607-003",
			"error",
			record.path,
			f"authored selectable {record.local_name} requires a nonempty durable id",
		))
	return tuple(issues)


#============================================
def _authored_reaction_role_issues(
		document: oasa.cdml_document.CDMLDocument,
		) -> tuple[CDMLConformanceIssue, ...]:
	"""Return authored-profile findings for reaction targets outside their roles."""
	direct_targets = {
		record.identifier: record
		for record in document.objects()
		if (
			not record.opaque
			and record.identifier is not None
			and record.identifier.strip()
			and not record.identifier.startswith("__bkchem_new__")
		)
	}
	issues = []
	for role in document.reaction_roles():
		expected_name = _AUTHORED_REACTION_ROLE_TARGET_NAMES[role.role_name]
		target = direct_targets.get(role.target_identifier)
		if target is not None and target.local_name == expected_name:
			continue
		issues.append(CDMLConformanceIssue(
			"CDML-A2607-004",
			"error",
			role.path,
			(
				f"authored reaction {role.role_name} requires a direct-root "
				f"{expected_name} target with a nonempty durable id"
			),
		))
	return tuple(issues)


#============================================
def inspect_cdml(text: str, *, profile: str = _COMPAT_PROFILE) -> CDMLConformanceReport:
	"""Inspect CDML without allocating IDs, transforming XML, or opening a session.

	Args:
		text: Complete CDML XML text to inspect.
		profile: Either ``compat`` or ``authored-26.07``.

	Returns:
		One immutable report containing stable error values.
	"""
	if profile not in _SUPPORTED_PROFILES:
		raise ValueError(f"unknown CDML conformance profile: {profile}")
	view = _parse_view(text)
	if view is None:
		report = CDMLConformanceReport(profile, (_xml_issue(),))
		return report
	if not _is_compatibility_root(view):
		report = CDMLConformanceReport(profile, (_root_issue(),))
		return report
	# Compatibility promises that the authoritative backend can retain the source,
	# not merely that the inspection parser can read it.
	try:
		document = oasa.cdml_document.CDMLDocument.parse(text, validation="compat")
	except oasa.cdml_document.CDMLParseError:
		report = CDMLConformanceReport(profile, (_xml_issue(),))
		return report
	if profile == _COMPAT_PROFILE:
		report = CDMLConformanceReport(profile, ())
		return report
	issues = []
	if view.version != "26.07":
		issues.append(CDMLConformanceIssue(
			"CDML-A2607-001",
			"error",
			"/cdml",
			"authored 26.07 CDML requires root version 26.07",
		))
	if view.namespace != oasa.cdml_document.CDML_NAMESPACE_URI:
		issues.append(CDMLConformanceIssue(
			"CDML-A2607-002",
			"error",
			"/cdml",
			"authored 26.07 CDML requires the canonical CDML namespace",
		))
	for issue in document.validation_issues(validation="strict"):
		issues.append(_document_issue(issue))
	issues.extend(_authored_selectable_id_issues(document))
	issues.extend(_authored_reaction_role_issues(document))
	report = CDMLConformanceReport(profile, tuple(issues))
	return report


#============================================
def _read_manifest(path: pathlib.Path) -> dict:
	"""Read one JSON corpus manifest and reject an unrelated top-level shape."""
	payload = json.loads(path.read_text(encoding="utf-8"))
	if not isinstance(payload, dict) or payload.get("schema") != _CORPUS_SCHEMA:
		raise ValueError("unsupported CDML conformance corpus manifest")
	if not isinstance(payload.get("cases"), list):
		raise ValueError("CDML conformance corpus manifest requires a cases list")
	return payload


#============================================
def _source_text(case: dict, repository_root: pathlib.Path) -> str:
	"""Load one bounded inline or repository-relative corpus source."""
	source = case["source"]
	if not isinstance(source, dict) or len(source) != 1:
		raise ValueError(f"corpus case {case['id']} requires exactly one source")
	if "inline_xml" in source:
		text = source["inline_xml"]
		if not isinstance(text, str):
			raise ValueError(f"corpus case {case['id']} inline_xml must be text")
		return text
	if "repo_path" not in source:
		raise ValueError(f"corpus case {case['id']} has an unknown source kind")
	relative_path = pathlib.PurePosixPath(source["repo_path"])
	if relative_path.is_absolute():
		raise ValueError(f"corpus case {case['id']} repo_path must be relative")
	path = (repository_root / relative_path).resolve()
	if not path.is_relative_to(repository_root.resolve()):
		raise ValueError(f"corpus case {case['id']} repo_path escapes repository root")
	text = path.read_text(encoding="utf-8")
	return text


#============================================
def inspect_manifest(manifest_path: pathlib.Path, repository_root: pathlib.Path) -> tuple[CDMLConformanceCaseResult, ...]:
	"""Run the bounded shared corpus without invoking a subprocess or a writer."""
	payload = _read_manifest(manifest_path)
	results = []
	seen_ids = set()
	for case in payload["cases"]:
		if not isinstance(case, dict) or not isinstance(case.get("id"), str):
			raise ValueError("CDML conformance corpus cases require string IDs")
		case_id = case["id"]
		if case_id in seen_ids:
			raise ValueError(f"duplicate CDML conformance corpus case ID: {case_id}")
		seen_ids.add(case_id)
		expect = case.get("expect")
		if not isinstance(expect, dict) or not expect:
			raise ValueError(f"corpus case {case_id} requires profile expectations")
		text = _source_text(case, repository_root)
		reports = []
		for profile, expectation in expect.items():
			if profile not in _SUPPORTED_PROFILES or expectation not in ("valid", "invalid"):
				raise ValueError(f"corpus case {case_id} has an invalid profile expectation")
			report = inspect_cdml(text, profile=profile)
			if report.is_valid != (expectation == "valid"):
				raise ValueError(f"corpus case {case_id} did not meet its {profile} expectation")
			reports.append(report)
		compat_report = inspect_cdml(text, profile=_COMPAT_PROFILE)
		preservation_matches = False
		if compat_report.is_valid:
			document = oasa.cdml_document.CDMLDocument.parse(text, validation="compat")
			original_view = _parse_view(text)
			reloaded_view = _parse_view(document.serialize())
			preservation_matches = (
				original_view is not None
				and reloaded_view is not None
				and original_view.semantic_fingerprint == reloaded_view.semantic_fingerprint
			)
			if not preservation_matches:
				raise ValueError(f"corpus case {case_id} lost semantic XML content")
		result = CDMLConformanceCaseResult(
			case_id=case_id,
			reports=tuple(reports),
			preservation_matches=preservation_matches,
		)
		results.append(result)
	return tuple(results)
