from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def role_required(allowed_roles):
    """
    Decorator that checks if a user is authenticated and has one of the allowed roles.
    If the user does not have permission, they are redirected to their own dashboard
    with a warning, or to the login page if not authenticated.
    """
    if isinstance(allowed_roles, str):
        allowed_roles = [allowed_roles]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                # Store the attempted URL so we can redirect back after login
                return redirect(f'login?next={request.path}')
            
            if request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            
            # User is authenticated but does not have the correct role.
            # Redirect to their appropriate dashboard with an error message.
            messages.error(request, "Access Denied: You do not have permission to view that page.")
            
            if request.user.role == 'ADMIN':
                return redirect('admin_dashboard')
            elif request.user.role == 'PROVIDER':
                return redirect('provider_dashboard')
            else:
                return redirect('customer_dashboard')
                
        return _wrapped_view
    return decorator
