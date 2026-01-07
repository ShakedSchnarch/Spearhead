class IronViewError(Exception):
    """Base exception for Iron-View errors."""
    pass

class ConfigError(IronViewError):
    """Configuration loading specific errors."""
    pass

class DataSourceError(IronViewError):
    """Data ingestion specific errors."""
    pass
