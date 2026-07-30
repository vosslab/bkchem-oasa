"""Load isotope data from the packaged JSON file."""

# Standard Library
import json
import os


SOURCE_URL = (
	"https://physics.nist.gov/cgi-bin/Compositions/stand_alone.pl?"
	"ele=&ascii=ascii2&isotype=some"
)
DATA_PATH = os.path.abspath(
	os.path.join(os.path.dirname(__file__), "..", "oasa_data", "isotopes.json")
)


#============================================
def _load_isotopes() -> object:
	"""Load isotope data from JSON into a nested integer-keyed dict."""
	with open(DATA_PATH, "r") as handle:
		raw_data = json.load(handle)
	isotopes = {}
	for atomic_key, mass_map in raw_data.items():
		atomic_number = int(atomic_key)
		ordered = {}
		for mass_key, entry in mass_map.items():
			mass_number = int(mass_key)
			ordered[mass_number] = entry
		isotopes[atomic_number] = ordered
	return isotopes


isotopes = _load_isotopes()
