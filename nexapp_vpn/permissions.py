 
from rest_framework import permissions
 
class IsOrganizationMember(permissions.BasePermission):
    """
    Custom permission to only allow users to access objects
    belonging to their organization.
    """
    def has_object_permission(self, request, view, obj):
        user_org = getattr(request.user, 'organizationuser', None)
        return user_org and obj.organization == user_org.organization
 
    def has_permission(self, request, view):
        return hasattr(request.user, 'organizationuser')