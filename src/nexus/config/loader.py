import yaml
import os
import logging
import copy
from threading import RLock
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Path to the agents config file
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "agents.yaml")

_FULL_CONFIG: Optional[Dict[str, Any]] = None
_CONFIG_MTIME: Optional[float] = None
_CONFIG_LOCK = RLock()

VALID_CAPABILITIES = {
    "classification",
    "reasoning",
    "synthesis",
    "analysis",
    "generation",
    "ranking",
    "embedding",
    "extraction",
    "routing",
    "quality_control"
}

def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively merges two dictionaries.
    """
    result = base.copy()
    for k, v in override.items():
        if isinstance(v, dict) and k in result and isinstance(result[k], dict):
            result[k] = deep_merge(result[k], v)
        else:
            result[k] = v
    return result

def validate_config(config: Dict[str, Any]) -> None:
    """
    Validates the configuration structure and critical values.
    Raises ValueError if configuration is invalid.
    """
    # Validate Schema Version
    if config.get("schema_version") != 1:
        raise ValueError(f"Unsupported schema_version: {config.get('schema_version')}. Expected 1.")

    required_sections = ["system", "llm_router", "agents", "embedding_service"]
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required configuration section: {section}")
    
    # Validate LLM Router
    router = config["llm_router"]
    if "providers" not in router:
        raise ValueError("Missing 'providers' in llm_router")
    
    # Validate Rate Limits
    if "rate_limits" in router:
        limits = router["rate_limits"]
        if not isinstance(limits.get("flash"), int) or not isinstance(limits.get("pro"), int):
             raise ValueError("Rate limits must be integers")

    # Validate Agents
    agents = config["agents"]
    if not agents:
        raise ValueError("No agents defined in configuration")

    for name, agent in agents.items():
        if "description" not in agent:
             logger.warning(f"Agent '{name}' missing description")
        
        # Check Agent Version
        if "version" in agent and not isinstance(agent["version"], int):
            raise ValueError(f"Agent '{name}' version must be integer")
            
        # Validate Capabilities
        capabilities = agent.get("capabilities", [])
        for cap in capabilities:
            if cap not in VALID_CAPABILITIES:
                raise ValueError(f"Invalid capability '{cap}' for agent '{name}'. Must be one of {VALID_CAPABILITIES}")
        
        # Validate cost_tolerance enum if present
        if "cost_tolerance" in agent:
            valid_costs = ["zero", "low", "high"]
            if agent["cost_tolerance"] not in valid_costs:
                raise ValueError(f"Invalid cost_tolerance '{agent['cost_tolerance']}' for agent '{name}'. Must be one of {valid_costs}")

def load_nexus_config() -> Dict[str, Any]:
    """
    Loads and caches the full configuration from agents.yaml.
    Reloads if the file has changed (Hot Reload).
    Returns a deep copy of the complete configuration dictionary.
    Raises RuntimeError if loading or validation fails.
    """
    global _FULL_CONFIG, _CONFIG_MTIME

    if not os.path.exists(CONFIG_PATH):
        logger.error(f"Configuration not found at {CONFIG_PATH}")
        raise RuntimeError(f"Configuration file missing at {CONFIG_PATH}")

    with _CONFIG_LOCK:
        try:
            current_mtime = os.path.getmtime(CONFIG_PATH)
            
            # Check for hot reload
            if _FULL_CONFIG is not None and _CONFIG_MTIME == current_mtime:
                return copy.deepcopy(_FULL_CONFIG)

            # Load and Validate
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                
                try:
                    validate_config(data)
                except ValueError as ve:
                    logger.critical(f"Configuration Validation Failed: {ve}")
                    raise RuntimeError(f"Invalid Nexus configuration: {ve}")

                _FULL_CONFIG = data
                _CONFIG_MTIME = current_mtime
                logger.info(f"Loaded Nexus config from {CONFIG_PATH} (mtime={current_mtime})")
                return copy.deepcopy(_FULL_CONFIG)

        except Exception as e:
            logger.critical(f"Failed to load Nexus config: {e}")
            if isinstance(e, RuntimeError):
                raise e
            raise RuntimeError(f"Config load failure: {e}")

def get_section_config(section_name: str) -> Dict[str, Any]:
    """
    Returns a top-level configuration section (e.g., 'system', 'agents').
    """
    config = load_nexus_config()
    return config.get(section_name, {})

def get_agent_config(agent_name: str) -> Dict[str, Any]:
    """
    Returns the configuration for a specific agent from the 'agents' section,
    deep-merged with global defaults.
    """
    config = load_nexus_config()
    defaults = config.get("defaults", {})
    agents_section = config.get("agents", {})
    agent_specific = agents_section.get(agent_name, {})
    
    # Deep merge defaults with agent specific config
    return deep_merge(defaults, agent_specific)

# Backward compatibility alias
load_agents_config = load_nexus_config
