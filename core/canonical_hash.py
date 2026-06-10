import hashlib
import json


def canonical_json_dumps(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def canonical_json_hash(data):
    payload = canonical_json_dumps(data)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
