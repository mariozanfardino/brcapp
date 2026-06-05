import os
BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
DB_PATH         = os.path.join("/home/zanfardino/.local/share", "data", "breastcare.db")
WEKA_MODEL_DIR  = os.path.join(BASE_DIR, "models_weka")
WEKA_MODEL_FILE = os.path.join(WEKA_MODEL_DIR, "model.model")
JAVA_HEAP       = "512m"
APP_NAME        = "BrCapp"
APP_VERSION     = "1.0.0"
LOGO_PATH       = os.path.join(BASE_DIR, "assets", "logo.png")
PINK            = "#D63384"
PURPLE          = "#4A235A"
PINK_L          = "#F8D7E8"
PURP_L          = "#EDE7F6"
WEKA_FEATURES   = [
    "age","bmi","tumor_size_mm","tumor_quadrant","histology_type","grade",
    "er_status","pr_status","her2_status","ki67_percent",
    "multifocality","lymph_node_positive","eating_habit_score","physical_activity",
]
CLASS_LABELS    = {0: "BCS", 1: "Mastectomy"}
