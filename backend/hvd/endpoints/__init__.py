from hvd.endpoints import alert_video as alert_video_endpoint
from hvd.endpoints import alerts as alerts_endpoint
from hvd.endpoints import config as config_endpoint
from hvd.endpoints import features as features_endpoint
from hvd.endpoints import thumbnail as thumbnail_endpoint

# User auth/create/remove come from purest builtin endpoints (/api/auth/*).
ENDPOINTS = [
    config_endpoint,
    features_endpoint,
    alerts_endpoint,
    thumbnail_endpoint,
    alert_video_endpoint,
]
