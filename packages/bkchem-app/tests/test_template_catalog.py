"""Tests for folder-based template catalog discovery."""

# local repo modules
import template_catalog


#============================================
def _write_cdml(path):
	path.write_text("<?xml version=\"1.0\"?><cdml></cdml>", encoding="utf-8")


#============================================
def test_template_catalog_scans_categories(tmp_path):
	carbs = tmp_path / "carbs"
	protein = tmp_path / "protein"
	lipids = tmp_path / "lipids"
	nucleic = tmp_path / "nucleic_acids"
	pyrimidine_dir = nucleic / "pyrimidine"
	purine_dir = nucleic / "purine"
	for folder in (carbs, protein, lipids, pyrimidine_dir, purine_dir):
		folder.mkdir(parents=True, exist_ok=True)

	_write_cdml(carbs / "furanose.cdml")
	_write_cdml(carbs / "pyranose.cdml")
	_write_cdml(protein / "alanine.cdml")
	_write_cdml(lipids / "palmitate.cdml")
	_write_cdml(pyrimidine_dir / "pyrimidine.cdml")
	_write_cdml(purine_dir / "purine.cdml")

	entries = template_catalog.scan_template_tree(str(tmp_path))
	assert len(entries) == 6
	categories = {entry.category for entry in entries}
	assert categories == {"carbs", "protein", "lipids", "nucleic_acids"}
	subcategories = {entry.subcategory for entry in entries}
	assert "pyrimidine" in subcategories
	assert "purine" in subcategories

	catalog = template_catalog.build_category_map(entries)
	assert "carbs" in catalog
	assert "" in catalog["carbs"]
	assert "nucleic_acids" in catalog
	assert "pyrimidine" in catalog["nucleic_acids"]
	assert "purine" in catalog["nucleic_acids"]


#============================================
def test_template_catalog_formats_labels():
	entry = template_catalog.TemplateEntry(
		path="example.cdml",
		name="pyrimidine",
		category="nucleic_acids",
		subcategory="pyrimidine",
	)
	label = template_catalog.format_entry_label(entry)
	assert label == "nucleic acids / pyrimidine"
