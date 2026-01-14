"""
Custom Exception Hierarchy for Cotabot
Provides specific exception types for better error handling and debugging
"""


class CotabotError(Exception):
    """
    Base exception for all Cotabot-specific errors
    All custom exceptions should inherit from this
    """
    pass


# ==================== Database Errors ====================

class DatabaseError(CotabotError):
    """Base class for all database-related errors"""
    pass


class PlayerNotFoundError(DatabaseError):
    """
    Raised when a player is not found in the database
    
    Example:
        raise PlayerNotFoundError(f"Player with Steam ID {steam_id} not found")
    """
    pass


class DatabaseConnectionError(DatabaseError):
    """
    Raised when database connection fails
    
    Example:
        raise DatabaseConnectionError("Failed to connect to cotabot_dev.db")
    """
    pass


class DatabaseOperationError(DatabaseError):
    """
    Raised when a database operation fails (INSERT, UPDATE, DELETE)
    
    Example:
        raise DatabaseOperationError("Failed to update player stats")
    """
    pass


# ==================== API Errors ====================

class APIError(CotabotError):
    """Base class for external API errors"""
    pass


class BattleMetricsAPIError(APIError):
    """
    BattleMetrics API specific errors
    
    Attributes:
        status_code: HTTP status code from API
        response: API response body
    """
    def __init__(self, message, status_code=None, response=None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class GoogleSheetsAPIError(APIError):
    """
    Google Sheets API specific errors
    
    Example:
        raise GoogleSheetsAPIError("Failed to update sheet: Permission denied")
    """
    pass


class APITimeoutError(APIError):
    """
    Raised when API request times out
    
    Example:
        raise APITimeoutError("BattleMetrics API request timed out after 30s")
    """
    pass


# ==================== Configuration Errors ====================

class ConfigError(CotabotError):
    """Base class for configuration-related errors"""
    pass


class MissingConfigError(ConfigError):
    """
    Raised when required configuration is missing
    
    Example:
        raise MissingConfigError("DISCORD_TOKEN not found in environment")
    """
    pass


class InvalidConfigError(ConfigError):
    """
    Raised when configuration value is invalid
    
    Example:
        raise InvalidConfigError("LOG_LEVEL must be DEBUG, INFO, WARNING, or ERROR")
    """
    pass


# ==================== Discord Errors ====================

class DiscordOperationError(CotabotError):
    """
    Raised when Discord operations fail (message send, channel fetch, etc.)
    
    Example:
        raise DiscordOperationError("Failed to send message to #squad-log")
    """
    pass


class PermissionError(DiscordOperationError):
    """
    Raised when bot lacks required Discord permissions
    
    Example:
        raise PermissionError("Bot lacks MANAGE_CHANNELS permission")
    """
    pass


# ==================== Data Validation Errors ====================

class ValidationError(CotabotError):
    """Base class for data validation failures"""
    pass


class InvalidSteamIDError(ValidationError):
    """
    Raised when Steam ID format is invalid
    
    Example:
        raise InvalidSteamIDError("Steam ID must be 17 digits")
    """
    pass


class InvalidDiscordIDError(ValidationError):
    """
    Raised when Discord ID format is invalid
    
    Example:
        raise InvalidDiscordIDError("Discord ID must be numeric")
    """
    pass


class InvalidInputError(ValidationError):
    """
    Raised when user input is invalid
    
    Example:
        raise InvalidInputError("Score must be a positive integer")
    """
    pass


# ==================== File/Data Errors ====================

class DataError(CotabotError):
    """Base class for data-related errors"""
    pass


class JSONParseError(DataError):
    """
    Raised when JSON parsing fails
    
    Example:
        raise JSONParseError("Failed to parse squad_db.json: Invalid JSON")
    """
    pass


class FileNotFoundError(DataError):
    """
    Raised when required file is not found
    
    Note: This shadows Python's built-in FileNotFoundError
    Use for Cotabot-specific file operations
    
    Example:
        raise FileNotFoundError("squad_db.json not found")
    """
    pass
