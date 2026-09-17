from rest_framework import serializers


class BaseSerializerMixin(serializers.ModelSerializer):
    """Базовый сериализатор."""

    def to_representation(self, obj):
        """Исключение null-полей и пустых строк из ответа сериализатора."""
        data = super().to_representation(obj)
        return {
            attr: value for attr, value in data.items()
            if value is not None and value != ''
        }


class LookupMixin:
    """Искать объекты по публичному id."""
    lookup_field = 'public_id'
