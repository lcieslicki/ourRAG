class DomainError(Exception):
    """Base class for domain-layer failures."""


class WorkspaceAccessDenied(DomainError):
    pass


class DocumentAccessDenied(DomainError):
    pass


class ConversationAccessDenied(DomainError):
    pass
