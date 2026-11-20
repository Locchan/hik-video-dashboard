from hvd.endpoints import alert_video as alert_video_endpoint
from hvd.endpoints import alerts as alerts_endpoint
from hvd.endpoints import config as config_endpoint
from hvd.endpoints import features as features_endpoint
from hvd.endpoints import streaming_channels as streaming_channels_endpoint
from hvd.endpoints import streaming_recordings as streaming_recordings_endpoint
from hvd.endpoints import streaming_stream as streaming_stream_endpoint
from hvd.endpoints import thumbnail as thumbnail_endpoint
from hvd.endpoints import version as version_endpoint

# User auth/create/remove come from purest builtin endpoints (/api/auth/*).
ENDPOINTS = [
    version_endpoint,
    config_endpoint,
    features_endpoint,
    alerts_endpoint,
    thumbnail_endpoint,
    alert_video_endpoint,
    streaming_channels_endpoint,
    streaming_recordings_endpoint,
    streaming_stream_endpoint,
]
