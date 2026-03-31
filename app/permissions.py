from rest_framework.exceptions import PermissionDenied, AuthenticationFailed
from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework_simplejwt.authentication import JWTAuthentication


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user = request.user

        # Token noto‘g‘ri yoki yo‘q
        if not user or not user.is_authenticated:
            raise AuthenticationFailed("Invalid token or user does not exist")

        if getattr(user, "role", "") != "ADMIN":
            raise PermissionDenied("You do not have permission to perform this action")

        return True


class IsAdminUserCustom:
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "ADMIN"


class AllowGetAnyOtherAuthenticated(BasePermission):
    """
    Allow unrestricted GET requests, but require authentication for other methods.
    Additionally checks object-level permissions for update/delete operations.
    """

    def has_permission(self, request, view):
        # Allow all GET, HEAD, OPTIONS requests
        if request.method in SAFE_METHODS:
            return True

        # For other methods, require authentication
        if not request.user or not request.user.is_authenticated:
            return False

        # Additional checks for POST requests (create)
        if request.method == "POST":
            return self._check_create_permission(request, view)

        return True

    def has_object_permission(self, request, view, obj):
        # Allow GET requests for any object
        if request.method in SAFE_METHODS:
            return True

        # For other methods, check if user owns the object
        if hasattr(obj, "reviewer"):
            return obj.reviewer == request.user

        # Default deny if we can't verify ownership
        return False

    def _check_create_permission(self, request, view):
        """Additional checks for creating ratings"""
        # Example: Check if user has purchased the product before allowing to rate
        product_id = request.data.get("product")
        if not product_id:
            raise PermissionDenied("Product ID is required for rating")

        # Here you could add logic to verify user can rate this product
        # For example, check if they've purchased it
        # from app.models.order import Order
        # if not Order.objects.filter(user=request.user, items__product_id=product_id, status='COMPLETED').exists():
        #     raise PermissionDenied("You can only rate products you've purchased")

        return True


class OptionalJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            header = self.get_header(request)
            if header is None:
                return None
            try:
                return super().authenticate(request)
            except AuthenticationFailed:
                return None
        return super().authenticate(request)
