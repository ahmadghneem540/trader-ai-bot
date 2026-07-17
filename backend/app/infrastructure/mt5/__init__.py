from app.infrastructure.mt5.connector import MT5Connector

# Singleton instance
_mt5_connector_instance = None

def get_mt5_connector() -> MT5Connector:
    """
    Get the singleton MT5Connector instance.
    
    Returns:
        MT5Connector: The global MT5 connector instance
    """
    global _mt5_connector_instance
    if _mt5_connector_instance is None:
        _mt5_connector_instance = MT5Connector()
    return _mt5_connector_instance
