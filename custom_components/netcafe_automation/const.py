"""Constants for the netcafe_automation integration."""

DOMAIN = "netcafe_automation"
HUB_NAME = "智慧网吧"
HUB_MODEL = "智慧网吧"
HUB_MANUFACTURER = "老师傅 微信：ha33948"

# CSV fields
FIELD_IP_ADDRESS = "ip_address"
FIELD_ROOM_NAME = "room_name"

# Entity prefixes
PREFIX_DEVICE_TRACKER = "device_tracker."

# Config keys
CONF_DEVICES = "devices"
CONF_CSV_CONTENT = "csv_content"

# Service names
SERVICE_RELOAD_CSV = "reload_from_csv"
SERVICE_EXPORT_CSV = "export_csv"
SERVICE_IMPORT_CSV_FROM_FILE = "import_csv_from_file"
SERVICE_IMPORT_CSV_DIRECT = "import_csv_direct"
SERVICE_CLEAR_ALL_DATA = "clear_all_data"
SERVICE_CLEAR_ALL_DEVICE_TRACKERS = "clear_all_device_trackers"

# Defaults
DEFAULT_CONSIDER_HOME = 90
FAST_ONLINE_INTERVAL = 3
PROBE_INTERVAL = FAST_ONLINE_INTERVAL
PING_TIMEOUT_MS_WINDOWS = 1000
PING_TIMEOUT_S_LINUX = 1
PING_WAIT_TIMEOUT = 1.2
PING_CONCURRENCY = 32
PING_RETRY_DELAY_SECONDS = 1
OFFLINE_FAILURE_THRESHOLD = 2
OFFLINE_CONFIRM_SECONDS = 10

CSV_TEMPLATE = """ip_address,room_name
192.168.1.38,双包38
192.168.1.39,双包38
192.168.1.40,单间40
192.168.1.50,三人区50
192.168.1.51,三人区50
192.168.1.52,三人区50"""
