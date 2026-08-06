class AuthError(Exception):
    pass

class UserExistsError(AuthError):
    pass

class InvalidCredentials(AuthError):
    pass

class InactiveUserError(AuthError):
    pass

class PermissionDenied(AuthError):
    pass
