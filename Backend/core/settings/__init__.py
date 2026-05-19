from decouple import config

DJANGO_ENV = config("DJANGO_ENV", default="dev")

if DJANGO_ENV == "prod":
    from .prod import *
elif DJANGO_ENV == "staging":
    from .staging import *
else:
    from .dev import *

from core.env_validation import validate_environment

_issues = validate_environment()
if STARTUP_STRICT_VALIDATION and any(issue.level == "error" for issue in _issues):
    raise RuntimeError("Startup validation failed: " + "; ".join(f"{i.key}={i.message}" for i in _issues))
