def get_hub_spoke_ipsec_payloads(tunnel):
    """
    Returns a list of dicts {"method":"add-tunnel","payload":…}
    covering both directions, for site-to-site and hub-spoke.
    """
   
    hub    = tunnel.device_a
    spokes = list(tunnel.device_b.all())

    # Grab the “hub” subnet from the Tunnel
    hub_subnet = getattr(tunnel, 'device_a_subnet', None)
    if not hub_subnet:
        raise AttributeError("Tunnel has no attribute 'device_a_subnet'")

    # If your Tunnel model has a single device_b_subnet, use it as a fallback
    default_spoke_subnet = getattr(tunnel, 'device_b_subnet', None)

    # helper to resolve each spoke’s subnet
    def _get_spoke_subnet(spoke):
        # debug line: uncomment to verify object type at runtime
        # print(f"DEBUG: spoke is a {type(spoke)} with attrs {spoke.__dict__.keys()}")
        if hasattr(spoke, 'device_b_subnet'):
            return spoke.device_b_subnet
        if default_spoke_subnet:
            return default_spoke_subnet
        raise AttributeError(
            f"No subnet field found for spoke '{getattr(spoke, 'name', spoke)}' "
            f"and no Tunnel.device_b_subnet to fall back on."
        )

    # Common crypto/control settings
    common = {
        "service":        "enable",
        "keyexchange":    tunnel.ike_version,
        "shared_key":     tunnel.pre_shared_key,
        "dpdaction":      tunnel.dpdaction,
        "ipcomp":         "yes" if tunnel.ipcomp else "no",
        "forceencaps":    "no",
        "ike": {
            "hash_algorithm":       tunnel.ike_integrity_algorithm,
            "encryption_algorithm": tunnel.ike_encryption_algorithm,
            "dh_group":             tunnel.ike_diffie_hellman_group,
            "rekeytime":            tunnel.ike_key_lifetime,
        },
        "esp": {
            "hash_algorithm":       tunnel.esp_integrity_algorithm,
            "encryption_algorithm": tunnel.esp_encryption_algorithm,
            "dh_group":             tunnel.esp_diffie_hellman_group,
            "rekeytime":            tunnel.esp_key_lifetime,
        },
    }

    out = []

    # 1) Hub payload — aggregates all spoke subnets
    hub_payload = {
        **common,
        "local_identifier":  tunnel.local_identifier,
        "remote_identifier": "%any",
        "subnet": [
            {
                "local_subnet":  hub_subnet,
                "remote_subnet": _get_spoke_subnet(spoke)
            }
            for spoke in spokes
        ],
    }
    out.append({"device": hub.name, "payload": hub_payload})

    # 2) One payload per spoke — single subnet
    for spoke in spokes:
        spoke_sub = _get_spoke_subnet(spoke)
        spoke_payload = {
            **common,
            "local_identifier":  tunnel.remote_identifier,
            "remote_identifier": tunnel.local_identifier,
            "subnet": [
                {"local_subnet": spoke_sub, "remote_subnet": hub_subnet}
            ],
        }
        out.append({"device": spoke.name, "payload": spoke_payload})

    return out