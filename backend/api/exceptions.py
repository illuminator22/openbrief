"""Custom exceptions for OpenBrief following a consistent error hierarchy."""


class OpenBriefError(Exception):
    """Base exception for OpenBrief."""


class DocumentProcessingError(OpenBriefError):
    """Raised when document processing fails."""


class DocumentValidationError(OpenBriefError):
    """Raised when an uploaded document fails validation."""


class RAGQueryError(OpenBriefError):
    """Raised when RAG pipeline fails."""


class LLMProviderError(OpenBriefError):
    """Raised when LLM API call fails."""


class EncryptionError(OpenBriefError):
    """Raised when API key encryption or decryption fails."""
