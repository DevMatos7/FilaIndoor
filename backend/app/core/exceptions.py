class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str = "app_error"):
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str = "Recurso não encontrado"):
        super().__init__(message, status_code=404, code="not_found")


class ConflictError(AppError):
    def __init__(self, message: str = "Conflito"):
        super().__init__(message, status_code=409, code="conflict")


class ForbiddenError(AppError):
    def __init__(self, message: str = "Permissão negada"):
        super().__init__(message, status_code=403, code="forbidden")


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Não autenticado"):
        super().__init__(message, status_code=401, code="unauthorized")


class InvalidTransitionError(AppError):
    def __init__(self, message: str = "Transição de status inválida"):
        super().__init__(message, status_code=422, code="invalid_transition")


class ValidationError(AppError):
    def __init__(self, message: str = "Dados inválidos"):
        super().__init__(message, status_code=422, code="validation_error")
