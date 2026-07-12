"""Field type enumeration.

Defines every supported field type for card templates.
Each member represents a distinct category of data that
can be placed on a card.
"""

from enum import Enum


class FieldType(str, Enum):
    """Supported field types for card templates.

    Members are ``str``-enabled so they serialise naturally to
    JSON, databases, and configuration files.
    """

    TEXT = "text"
    PHOTO = "photo"
    QR_CODE = "qr_code"
    BARCODE = "barcode"
    STATIC_IMAGE = "static_image"
    ORGANIZATION_LOGO = "organization_logo"
    SIGNATURE = "signature"
    DATE = "date"
