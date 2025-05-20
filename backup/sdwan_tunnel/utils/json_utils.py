import json
from deepdiff import DeepDiff  # ensure deepdiff is in requirements
import jsonpatch
 
def deep_merge(a, b):
    """Recursively merge dict b into dict a."""
    for key, value in b.items():
        if key in a and isinstance(a[key], dict) and isinstance(value, dict):
            deep_merge(a[key], value)
        else:
            a[key] = value
    return a
 
 
def json_diff(old, new):
    """Return the diff between two JSON-serializable objects."""
    return DeepDiff(old, new, ignore_order=True).to_dict()
 
 
def patch_json(original, patch):
    """Apply a JSON patch (RFC 6902) to the original JSON object."""
    # Using jsonpatch library
    patch_obj = jsonpatch.JsonPatch(patch)
    return patch_obj.apply(original)
 