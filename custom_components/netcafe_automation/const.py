"""Constants for the 网吧智能自动化 integration."""

DOMAIN = "netcafe_automation"

# CSV Fields - v3.0 Simplified Format
FIELD_ROOM_NAME = "room_name"
FIELD_IP_ADDRESS = "ip_address"
FIELD_CLIMATE_ENTITY = "climate_entity"
FIELD_LIGHT_ENTITY = "light_entity"
FIELD_COVER_ENTITY = "cover_entity"

# Legacy fields (backwards compatibility)
FIELD_ENTITY_ID = "entity_id"

# Entity prefixes
PREFIX_DEVICE_TRACKER = "device_tracker."
PREFIX_CLIMATE = "climate."
PREFIX_LIGHT = "light."
PREFIX_COVER = "cover."
PREFIX_INPUT_BOOLEAN = "input_boolean."

# Season values
SEASON_SUMMER = "夏季"
SEASON_WINTER = "冬季"
SEASON_SPRING_AUTUMN = "春秋季"

# Configuration keys
CONF_CSV_FILE = "csv_file"
CONF_CSV_CONTENT = "csv_content"
CONF_ENABLE_AUTOMATION = "enable_automation"
CONF_SEASON_REGION = "season_region"
CONF_WEATHER_ENTITY = "weather_entity"
CONF_TEMPERATURE_ENTITY = "temperature_entity"

# Season regions
REGION_NORTH = "north"
REGION_SOUTH = "south"
REGION_CUSTOM = "custom"

# Service names
SERVICE_RELOAD_CSV = "reload_from_csv"
SERVICE_EXPORT_CSV = "export_csv"
SERVICE_DOWNLOAD_TEMPLATE = "download_template"
SERVICE_IMPORT_CSV_FROM_FILE = "import_csv_from_file"
SERVICE_IMPORT_CSV_DIRECT = "import_csv_direct"

# Default values
DEFAULT_DELAY_SECONDS = 100
DEFAULT_CONSIDER_HOME = 45  # Consider device home for 45 seconds after last seen
PROBE_INTERVAL = 5  # Scan interval in seconds (very fast detection)

# CSV Template - v3.0 Simplified
CSV_TEMPLATE = """room_name,ip_address,climate_entity,light_entity,cover_entity
双包38,192.168.1.38,,,
双包38,192.168.1.39,climate.ac_38,light.light_38,cover.curtain_38
单间40,192.168.1.40,climate.ac_40,light.light_40,
三人包50,192.168.1.50,,,
三人包50,192.168.1.51,,,
三人包50,192.168.1.52,climate.ac_50,light.light_50,"""
