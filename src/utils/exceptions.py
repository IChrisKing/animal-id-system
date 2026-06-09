"""自定义异常层次结构"""


class AnimalIDError(Exception):
    """Base exception for Animal ID System"""
    pass


# ── Input Errors ────────────────────────────────────────────

class InputError(AnimalIDError):
    """Base for input-related errors"""
    pass


class FileNotFoundError(InputError):
    """Media file does not exist"""
    pass


class UnsupportedFormatError(InputError):
    """Media file format is not supported"""
    pass


class CorruptedFileError(InputError):
    """Media file is corrupted or unreadable"""
    pass


class FileTooLargeError(InputError):
    """Media file exceeds size limit"""
    pass


# ── Recognition Errors ──────────────────────────────────────

class RecognitionError(AnimalIDError):
    """Base for recognition-related errors"""
    pass


class ModelNotFoundError(RecognitionError):
    """Model weight file is missing"""
    pass


class InferenceError(RecognitionError):
    """Inference failed"""
    pass


class NoAnimalDetectedError(RecognitionError):
    """No animal found in image (non-critical)"""
    pass


# ── API Errors ──────────────────────────────────────────────

class APIError(AnimalIDError):
    """Base for API-related errors"""
    pass


class APIConnectionError(APIError):
    """Cannot connect to API endpoint"""
    pass


class APITimeoutError(APIError):
    """API request timed out"""
    pass


class APIRateLimitError(APIError):
    """API rate limit exceeded"""
    pass


class APIAuthError(APIError):
    """API key is invalid"""
    pass


class APIClassificationError(APIError):
    """Classification failed after all retries"""
    pass


class ClassificationParseError(APIError):
    """Failed to parse API response"""
    pass


# ── Storage Errors ──────────────────────────────────────────

class StorageError(AnimalIDError):
    """Base for storage-related errors"""
    pass


class DatabaseConnectionError(StorageError):
    """Cannot connect to database"""
    pass


class DatabaseWriteError(StorageError):
    """Database write failed"""
    pass


class StorageFullError(StorageError):
    """Disk space exhausted"""
    pass


# ── Configuration Errors ────────────────────────────────────

class ConfigurationError(AnimalIDError):
    """Base for configuration-related errors"""
    pass


class InvalidConfigError(ConfigurationError):
    """Configuration file is malformed"""
    pass


class ModelPathNotFoundError(ConfigurationError):
    """Configured model path does not exist"""
    pass
