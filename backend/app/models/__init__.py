# Import all models to ensure they're registered with SQLAlchemy
from .document_model import LegalDocument
from .user_model import UserPreference
from .rights_model import DetectedRight
from .citation_model import SLCitation
from .rights_violation_model import RightsViolation
from .user_account_model import UserAccount
from .bookmark_model import Bookmark
from .search_history_model import SearchHistory
from .processing_log_model import ProcessingLog
from .case_similarity_model import CaseSimilarity
from .document_version_model import DocumentVersion
from .audit_log_model import AuditLog
from .legal_entity_model import LegalEntity

__all__ = [
    "LegalDocument",
    "UserPreference", 
    "DetectedRight",
    "SLCitation",
    "RightsViolation",
    "UserAccount",
    "Bookmark",
    "SearchHistory",
    "ProcessingLog",
    "CaseSimilarity",
    "DocumentVersion",
    "AuditLog",
    "LegalEntity"
]