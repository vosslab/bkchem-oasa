#!/usr/bin/env python3
"""Convert NIST isotope HTML output to JSON for OASA."""

# Standard Library
import argparse
import html
import json
import os
import random
import re
import time
import urllib.parse
import urllib.request


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_INPUT = os.path.join(REPO_ROOT, "raw_isotope_data.html")
DEFAULT_OUTPUT = os.path.join(
	REPO_ROOT,
	"packages",
	"oasa",
	"oasa_data",
	"isotopes.json",
)
SOURCE_URL = (
	"https://physics.nist.gov/cgi-bin/Compositions/stand_alone.pl?"
	"ele=&ascii=ascii2&isotype=some"
)


#============================================
def parse_args() -> object:
	"""Parse command-line arguments."""
	parser = argparse.ArgumentParser(
		description="Convert NIST isotope HTML output into OASA JSON data."
	)
	parser.add_argument(
		"-i",
		"--input",
		dest="input_path",
		default=None,
		help="Optional path to raw_isotope_data.html (defaults to download).",
	)
	parser.add_argument(
		"-o",
		"--output",
		dest="output_path",
		default=DEFAULT_OUTPUT,
		help="Path to write isotopes.json.",
	)
	return parser.parse_args()


#============================================
def download_source(url: object) -> object:
	"""Download isotope HTML data from the NIST source URL."""
	parsed = urllib.parse.urlparse(url)
	if parsed.scheme not in ("http", "https"):
		raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")
	if parsed.netloc.lower() != "physics.nist.gov":
		raise ValueError(f"Unsupported URL host: {parsed.netloc}")
	time.sleep(random.random())
	request = urllib.request.Request(
		url,
		headers={"User-Agent": "Mozilla/5.0"},
	)
	with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310 - scheme/host validated
		return response.read().decode("utf-8", errors="replace")


#============================================
def extract_pre_text(html_text: object) -> object:
	"""Extract the <pre> block from the raw HTML."""
	start_token = "<pre>"
	end_token = "</pre>"
	start_index = html_text.find(start_token)
	if start_index == -1:
		raise ValueError("Missing <pre> block in HTML data.")
	end_index = html_text.find(end_token, start_index)
	if end_index == -1:
		raise ValueError("Missing </pre> block in HTML data.")
	content = html_text[start_index + len(start_token):end_index]
	content = html.unescape(content)
	content = content.replace("\xa0", " ")
	content = re.sub(r"<[^>]+>", "", content)
	return content


#============================================
def parse_number(text: object) -> object:
	"""Parse a numeric string with optional uncertainty in parentheses."""
	value = text.strip()
	if not value:
		return ""
	value = re.sub(r"\(.*\)$", "", value).strip()
	if not value:
		return ""
	return float(value)


#============================================
def parse_standard_atomic_weight(text: object) -> object:
	"""Parse standard atomic weight values or ranges."""
	value = text.strip()
	if not value:
		return ""
	if value.startswith("[") and value.endswith("]"):
		parts = [part.strip() for part in value[1:-1].split(",") if part.strip()]
		return [float(part) for part in parts]
	return parse_number(value)


#============================================
def parse_isotopic_composition(text: object) -> object:
	"""Parse isotopic composition and convert to percent."""
	value = parse_number(text)
	if value == "":
		return ""
	return value * 100.0


#============================================
def parse_records(pre_text: object) -> object:
	"""Parse key/value records from the preformatted text."""
	records = []
	current = {}
	for line in pre_text.splitlines():
		text = line.strip()
		if not text:
			if current:
				records.append(current)
				current = {}
			continue
		if "=" not in text:
			continue
		key, value = [part.strip() for part in text.split("=", 1)]
		current[key] = value
	if current:
		records.append(current)
	return records


#============================================
def build_isotope_map(records: object) -> object:
	"""Build the nested isotope mapping from parsed records."""
	isotopes = {}
	for record in records:
		atomic_number = int(record["Atomic Number"])
		atomic_symbol = record["Atomic Symbol"]
		mass_number = int(record["Mass Number"])
		relative_atomic_mass = parse_number(record["Relative Atomic Mass"])
		isotopic_composition = parse_isotopic_composition(
			record.get("Isotopic Composition", "")
		)
		standard_atomic_weight = parse_standard_atomic_weight(
			record.get("Standard Atomic Weight", "")
		)
		entry = {
			"Atomic Number": atomic_number,
			"Atomic Symbol": atomic_symbol,
			"Isotopic Composition": isotopic_composition,
			"Mass Number": mass_number,
			"Relative Atomic Mass": relative_atomic_mass,
			"Standard Atomic Weight": standard_atomic_weight,
		}
		isotopes.setdefault(atomic_number, {})[mass_number] = entry
	return isotopes


#============================================
def order_isotopes(isotopes: object) -> object:
	"""Order isotopes by atomic number then mass number."""
	ordered = {}
	for atomic_number in sorted(isotopes):
		mass_map = isotopes[atomic_number]
		ordered_mass = {}
		for mass_number in sorted(mass_map):
			ordered_mass[str(mass_number)] = mass_map[mass_number]
		ordered[str(atomic_number)] = ordered_mass
	return ordered


#============================================
def write_json(data: object, output_path: object) -> None:
	"""Write compact JSON data to disk."""
	with open(output_path, "w") as handle:
		json.dump(data, handle, separators=(",", ":"))


#============================================
def main() -> None:
	"""Run the conversion process."""
	args = parse_args()
	if args.input_path:
		with open(args.input_path, "r") as handle:
			html_text = handle.read()
	else:
		html_text = download_source(SOURCE_URL)
	pre_text = extract_pre_text(html_text)
	records = parse_records(pre_text)
	isotopes = build_isotope_map(records)
	ordered = order_isotopes(isotopes)
	write_json(ordered, args.output_path)


if __name__ == "__main__":
	main()
