import os
APP_TITLE = os.getenv("APP_TITLE", "Mad Dog Mock")
APP_VERSION = os.getenv("APP_VERSION", "2.0.0")
CORS_ALLOW_ORIGINS = [o.strip() for o in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",") if o.strip()]
JWKS_TTL = int(os.getenv("JWKS_TTL", "600"))
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "5.0"))
