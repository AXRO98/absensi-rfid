
from functools import wraps
from flask import redirect, url_for, abort
from flask_login import current_user

def role_required(*roles):
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect('/login')
            if current_user.role not in roles:
                abort(403)
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper

