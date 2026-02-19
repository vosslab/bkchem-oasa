#--------------------------------------------------------------------------
#     This file is part of OASA - a free chemical python library
#--------------------------------------------------------------------------

"""Load sugar code display names from the packaged YAML file."""

# Standard Library
import os

# Third Party
import yaml


DATA_PATH = os.path.abspath(
	os.path.join(os.path.dirname(__file__), "..", "oasa_data", "sugar_codes.yaml")
)


#============================================
def _load_sugar_names() -> dict[str, str]:
	"""Load and flatten family-grouped YAML into a flat {code: name} dict."""
	with open(DATA_PATH, "r") as handle:
		raw_data = yaml.safe_load(handle)
	names = {}
	for _family, entries in raw_data.items():
		if not isinstance(entries, dict):
			continue
		for code, name in entries.items():
			display_name = str(name).title()
			# Fix common title-casing artifacts for chemical prefixes.
			display_name = display_name.replace("-D-", "-D-").replace("-L-", "-L-")
			names[code] = display_name
	return names


_SUGAR_NAMES = _load_sugar_names()


#============================================
def get_sugar_name(code: str) -> str | None:
	"""Return the display name for one sugar code, or None if unknown."""
	return _SUGAR_NAMES.get(code)


#============================================
def all_sugar_names() -> dict[str, str]:
	"""Return a copy of the full {code: display_name} mapping."""
	return dict(_SUGAR_NAMES)
