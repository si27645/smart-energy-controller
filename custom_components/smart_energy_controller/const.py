"""Constants for the Smart Energy Controller integration."""

DOMAIN = "smart_energy_controller"

CONF_RULES = "rules"
CONF_NAME = "name"
CONF_ENTITY_ID = "entity_id"
CONF_ABOVE = "above"
CONF_BELOW = "below"
CONF_STATE = "state"
CONF_SERVICE = "service"
CONF_SERVICE_DATA = "service_data"
CONF_TARGET_ENTITY_ID = "target_entity_id"
CONF_EXPLAIN = "explain"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL_SECONDS = 60

EVENT_DECISION = f"{DOMAIN}_decision"
SERVICE_EVALUATE_NOW = "evaluate_now"
