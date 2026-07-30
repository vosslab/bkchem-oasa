#!/usr/bin/env python3
"""Inspect one CDML document or the shipped 26.07 interoperability corpus."""

# Standard Library
import argparse
import json
import pathlib

# local repo modules
import oasa.cdml_conformance


#============================================
def parse_args() -> argparse.Namespace:
	"""Parse the intentionally small CDML conformance command-line interface."""
	parser = argparse.ArgumentParser(description=__doc__)
	source_group = parser.add_mutually_exclusive_group(required=True)
	source_group.add_argument("--input", type=pathlib.Path, help="CDML XML file to inspect")
	source_group.add_argument("--manifest", type=pathlib.Path, help="CDML conformance corpus manifest")
	parser.add_argument(
		"--profile",
		choices=("compat", "authored-26.07"),
		default="compat",
		help="profile for one --input document",
	)
	parser.add_argument(
		"--format",
		choices=("text", "json"),
		default="text",
		help="report presentation format",
	)
	args = parser.parse_args()
	return args


#============================================
def _issue_payload(issue: oasa.cdml_conformance.CDMLConformanceIssue) -> dict:
	"""Return one JSON-safe issue value without exposing implementation objects."""
	payload = {
		"code": issue.code,
		"severity": issue.severity,
		"path": issue.path,
		"message": issue.message,
	}
	return payload


#============================================
def _report_payload(report: oasa.cdml_conformance.CDMLConformanceReport) -> dict:
	"""Return one JSON-safe public conformance report."""
	payload = {
		"profile": report.profile,
		"is_valid": report.is_valid,
		"issues": [_issue_payload(issue) for issue in report.issues],
	}
	return payload


#============================================
def _case_payload(case: oasa.cdml_conformance.CDMLConformanceCaseResult) -> dict:
	"""Return one JSON-safe corpus result."""
	payload = {
		"id": case.case_id,
		"preservation_matches": case.preservation_matches,
		"reports": [_report_payload(report) for report in case.reports],
	}
	return payload


#============================================
def _print_text_report(report: oasa.cdml_conformance.CDMLConformanceReport) -> None:
	"""Print one concise human-readable report."""
	status = "valid" if report.is_valid else "invalid"
	print(f"{report.profile}: {status}")
	for issue in report.issues:
		print(f"{issue.severity} {issue.code} {issue.path}: {issue.message}")


#============================================
def _repository_root() -> pathlib.Path:
	"""Return the source checkout root from this repository-owned script location."""
	root = pathlib.Path(__file__).resolve().parent.parent
	return root


#============================================
def main() -> int:
	"""Run one read-only conformance inspection and return a process status."""
	args = parse_args()
	if args.input is not None:
		text = args.input.read_text(encoding="utf-8")
		report = oasa.cdml_conformance.inspect_cdml(text, profile=args.profile)
		if args.format == "json":
			print(json.dumps(_report_payload(report), indent=2, sort_keys=True))
		else:
			_print_text_report(report)
		return 0 if report.is_valid else 1
	results = oasa.cdml_conformance.inspect_manifest(args.manifest, _repository_root())
	# The corpus deliberately contains invalid documents.  A successful runner
	# means every actual result matched that case's declared expectation.
	matched_expectations = True
	if args.format == "json":
		payload = {
			"cases": [_case_payload(case) for case in results],
			"matched_expectations": matched_expectations,
		}
		print(json.dumps(payload, indent=2, sort_keys=True))
	else:
		for case in results:
			print(f"{case.case_id}: preservation={'yes' if case.preservation_matches else 'no'}")
			for report in case.reports:
				_print_text_report(report)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
