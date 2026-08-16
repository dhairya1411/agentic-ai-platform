import hashlib
import hmac
from datetime import UTC, datetime

from agentic_ai_api.integrations.webhooks import verify_slack_signature


def test_slack_signature_rejects_replay_and_accepts_valid_payload() -> None:
    secret, timestamp, body = "secret", "1000", b'{"type":"event_callback"}'
    signature = "v0=" + hmac.new(secret.encode(), b"v0:1000:" + body, hashlib.sha256).hexdigest()
    assert verify_slack_signature(secret, timestamp, body, signature, datetime.fromtimestamp(1001, UTC))
    assert not verify_slack_signature(secret, timestamp, body, signature, datetime.fromtimestamp(1301, UTC))
