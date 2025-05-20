import hashlib
import json
 
 
def compute_hash(payload):
    """Compute SHA-256 hash for a JSON-serializable payload."""
    if isinstance(payload, (dict, list)):
        payload = json.dumps(payload, sort_keys=True)
    elif not isinstance(payload, str):
        payload = str(payload)
    return hashlib.sha256(payload.encode()).hexdigest()
 
 
def compare_hash(old_hash, new_payload):
    """Compare an existing hash to a new payload's hash."""
    return old_hash == compute_hash(new_payload)
