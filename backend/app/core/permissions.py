"""Catálogo inicial de permissões (escopo empresa → loja → departamento)."""

QUEUE_ADMIN = "queue.admin"
QUEUE_MANAGER = "queue.manager"
QUEUE_OPERATOR = "queue.operator"
QUEUE_VIEW = "queue.view"

SIGNAGE_ADMIN = "signage.admin"
SIGNAGE_EDITOR = "signage.editor"
SIGNAGE_VIEWER = "signage.viewer"
SIGNAGE_PUBLISH = "signage.publish"

DEVICE_ADMIN = "device.admin"
DEVICE_VIEW = "device.view"

ANALYTICS_VIEW = "analytics.view"
INTEGRATION_ADMIN = "integration.admin"
INTEGRATION_VIEW = "integration.view"

ALL_PERMISSIONS = [
    QUEUE_ADMIN,
    QUEUE_MANAGER,
    QUEUE_OPERATOR,
    QUEUE_VIEW,
    SIGNAGE_ADMIN,
    SIGNAGE_EDITOR,
    SIGNAGE_VIEWER,
    SIGNAGE_PUBLISH,
    DEVICE_ADMIN,
    DEVICE_VIEW,
    ANALYTICS_VIEW,
    INTEGRATION_ADMIN,
    INTEGRATION_VIEW,
]

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "admin": list(ALL_PERMISSIONS),
    "manager": [
        QUEUE_MANAGER,
        QUEUE_OPERATOR,
        QUEUE_VIEW,
        DEVICE_VIEW,
        ANALYTICS_VIEW,
        SIGNAGE_VIEWER,
        INTEGRATION_VIEW,
    ],
    "operator": [QUEUE_OPERATOR, QUEUE_VIEW],
    "viewer": [QUEUE_VIEW, ANALYTICS_VIEW, SIGNAGE_VIEWER, DEVICE_VIEW],
}
