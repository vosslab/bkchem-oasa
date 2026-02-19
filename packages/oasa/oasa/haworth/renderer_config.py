#--------------------------------------------------------------------------
#     This file is part of OASA - a free chemical python library
#--------------------------------------------------------------------------

"""Haworth renderer constants and configuration tables."""

from oasa.haworth import PYRANOSE_O_INDEX, FURANOSE_O_INDEX


#============================================
PYRANOSE_SLOTS = ("ML", "TL", "TO", "MR", "BR", "BL")
FURANOSE_SLOTS = ("ML", "BL", "BR", "MR", "TO")

PYRANOSE_SLOT_INDEX = {
	"ML": 0,
	"TL": 1,
	"TO": 2,
	"MR": 3,
	"BR": 4,
	"BL": 5,
}

FURANOSE_SLOT_INDEX = {
	"ML": 0,
	"BL": 1,
	"BR": 2,
	"MR": 3,
	"TO": 4,
}

PYRANOSE_FRONT_EDGE_SLOT = "BR"
FURANOSE_FRONT_EDGE_SLOT = "BL"

PYRANOSE_FRONT_EDGE_INDEX = PYRANOSE_SLOT_INDEX[PYRANOSE_FRONT_EDGE_SLOT]
FURANOSE_FRONT_EDGE_INDEX = FURANOSE_SLOT_INDEX[FURANOSE_FRONT_EDGE_SLOT]

RING_SLOT_SEQUENCE = {
	"pyranose": ("MR", "BR", "BL", "ML", "TL"),
	"furanose": ("MR", "BR", "BL", "ML"),
}

PYRANOSE_SLOT_LABEL_CONFIG = {
	"MR": {"up_dir": (0, -1), "down_dir": (0, 1), "anchor": "start"},
	"BR": {"up_dir": (0, -1), "down_dir": (0, 1), "anchor": "start"},
	"BL": {"up_dir": (0, -1), "down_dir": (0, 1), "anchor": "end"},
	"ML": {"up_dir": (0, -1), "down_dir": (0, 1), "anchor": "end"},
	"TL": {"up_dir": (0, -1), "down_dir": (0, 1), "anchor": "middle"},
}

FURANOSE_SLOT_LABEL_CONFIG = {
	"MR": {"up_dir": (0, -1), "down_dir": (0, 1), "anchor": "start"},
	"BR": {"up_dir": (0, -1), "down_dir": (0, 1), "anchor": "start"},
	"BL": {"up_dir": (0, -1), "down_dir": (0, 1), "anchor": "end"},
	"ML": {"up_dir": (0, -1), "down_dir": (0, 1), "anchor": "end"},
}

RING_RENDER_CONFIG = {
	"pyranose": {
		"ring_size": 6,
		"slot_index": PYRANOSE_SLOT_INDEX,
		"slot_label_cfg": PYRANOSE_SLOT_LABEL_CONFIG,
		"front_edge_index": PYRANOSE_FRONT_EDGE_INDEX,
		"oxygen_index": PYRANOSE_O_INDEX,
	},
	"furanose": {
		"ring_size": 5,
		"slot_index": FURANOSE_SLOT_INDEX,
		"slot_label_cfg": FURANOSE_SLOT_LABEL_CONFIG,
		"front_edge_index": FURANOSE_FRONT_EDGE_INDEX,
		"oxygen_index": FURANOSE_O_INDEX,
	},
}

CARBON_NUMBER_VERTEX_WEIGHT = 0.68
OXYGEN_COLOR = "#8b0000"
HYDROXYL_GLYPH_WIDTH_FACTOR = 0.60
HYDROXYL_O_X_CENTER_FACTOR = 0.30
HYDROXYL_O_Y_CENTER_FROM_BASELINE = 0.52
HYDROXYL_O_RADIUS_FACTOR = 0.30
LEADING_C_X_CENTER_FACTOR = 0.24
HYDROXYL_LAYOUT_CANDIDATE_FACTORS = (1.00, 1.18, 1.34)
HYDROXYL_LAYOUT_INTERNAL_CANDIDATE_FACTORS = (0.88, 1.00, 1.12, 1.26, 1.42)
HYDROXYL_LAYOUT_MIN_GAP_FACTOR = 0.18
HYDROXYL_RING_COLLISION_PENALTY = 1000000.0
INTERNAL_PAIR_OVERLAP_AREA_THRESHOLD = 0.50
INTERNAL_PAIR_LABEL_SCALE = 0.90
INTERNAL_PAIR_LANE_Y_TOLERANCE_FACTOR = 0.12
INTERNAL_PAIR_MIN_H_GAP_FACTOR = 0.75
FURANOSE_TOP_UP_CLEARANCE_FACTOR = 0.08
VALID_DIRECTIONS = ("up", "down")
VALID_ANCHORS = ("start", "middle", "end")
REQUIRED_SIMPLE_JOB_KEYS = (
	"carbon",
	"direction",
	"vertex",
	"dx",
	"dy",
	"length",
	"label",
	"connector_width",
	"font_size",
	"font_name",
	"anchor",
	"line_color",
	"label_color",
)
