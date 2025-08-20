from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Global limiter instance; initialized with the app in create_app
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://"
)

