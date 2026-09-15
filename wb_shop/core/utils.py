from uuid import uuid4

from core.constants import PublicIdConstants


def generate_public_id() -> str:
    return uuid4().hex[:PublicIdConstants.MAX_LENGTH]
