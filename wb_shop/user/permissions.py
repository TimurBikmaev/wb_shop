from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Только для администратора.."""

    def has_permission(self, request, view):
        """Доступ разрешен только администратору."""
        user = request.user
        return user.is_authenticated and user.is_superuser is True
