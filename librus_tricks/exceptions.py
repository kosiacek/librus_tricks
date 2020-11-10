class LibrusTricksException(Exception):
    pass


class LibrusTricksAuthException(LibrusTricksException):
    pass


class LibrusTricksWrapperException(LibrusTricksAuthException):
    pass


class LibrusLoginError(LibrusTricksAuthException):
    pass


class SynergiaAPIEndpointNotFound(LibrusTricksWrapperException):
    pass


class LibrusPortalInvalidPasswordError(LibrusTricksAuthException):
    pass


class SynergiaAccessDenied(LibrusTricksWrapperException):
    pass


class WrongHTTPMethod(Exception):
    pass


class SynergiaAPIInvalidRequest(LibrusTricksWrapperException):
    pass


class TokenExpired(LibrusTricksException):
    pass


class SynergiaForbidden(LibrusTricksWrapperException):
    pass


class InvalidCacheManager(LibrusTricksAuthException):
    pass


class CaptchaRequired(LibrusTricksAuthException):
    pass


class SynergiaServerError(LibrusTricksWrapperException):
    pass


class SessionRequired(LibrusTricksWrapperException):
    pass


class APIPathIsEmpty(LibrusTricksWrapperException):
    pass


class OtherHTTPResponse(LibrusTricksWrapperException):
    pass


class SecurityWarning(Warning):
    pass


class PerformanceWarning(Warning):
    pass


class GoodPracticeWarning(Warning):
    pass


class SynergiaMaintenanceError(SynergiaServerError):
    pass
