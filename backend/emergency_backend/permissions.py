from rest_framework.permissions import BasePermission, SAFE_METHODS


def is_admin_user(user):
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser or user.is_staff:
        return True

    profile = getattr(user, 'profile', None)
    return profile is not None and profile.role == 'admin'


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return is_admin_user(request.user)


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user and request.user.is_authenticated

        return is_admin_user(request.user)