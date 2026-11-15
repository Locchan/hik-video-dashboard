"""Unauthenticated GET /version — backend, frontend, and purest package versions."""

from __future__ import annotations

from purest import api_endp

from hvd.version_info import version_payload

ENDP_PATH = "/version"
LOGIN_REQUIRED = False
DOCSTRING = {
    "GET": "Return backend, frontend, and purest version strings.",
}
RESULT_EXAMPLE = {
    "GET": '{"backend": "0.2.3", "frontend": "0.1.0", "purest": "1.0.0rc-1"}',
}


@api_endp
def impl_GET(headers):
    return version_payload()
