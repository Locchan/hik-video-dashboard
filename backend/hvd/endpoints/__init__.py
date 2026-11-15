from hvd.endpoints import config as config_endpoint

# User auth/create/remove come from purest builtin endpoints (/api/auth/*).
ENDPOINTS = [
    config_endpoint,
]
