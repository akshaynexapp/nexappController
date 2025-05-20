def get_ipsec_payloads(tunnel, mgmt_ip_b, mgmt_ip_a, spoke=None):
    """
    Returns a list of dicts {"method":"add-tunnel","payload":…}
    covering both directions, for site-to-site and hub-spoke.
    """
    payloads = []
    hub   = tunnel.device_a
    # remotes = [tunnel.device_b.first()] if tunnel.mode == 'site_to_site' else list(tunnel.device_b.all())
    if spoke:
        remotes = [spoke]
    elif tunnel.mode == 'site_to_site':
        remotes = [tunnel.device_b.first()]
    else:
        remotes = list(tunnel.device_b.all())
    for branch in remotes:
        # mgmt_hub    = mgmt_map[hub.name]
        # mgmt_branch = mgmt_map[branch.name]
 
        common = {
            "ns_name": tunnel.name,
            "ike": {
              "hash_algorithm": tunnel.ike_integrity_algorithm,
              "encryption_algorithm": tunnel.ike_encryption_algorithm,
              "dh_group": tunnel.ike_diffie_hellman_group,
              "rekeytime": tunnel.ike_key_lifetime
            },
            "esp": {
              "hash_algorithm": tunnel.esp_integrity_algorithm,
              "encryption_algorithm": tunnel.esp_encryption_algorithm,
              "dh_group": tunnel.esp_diffie_hellman_group,
              "rekeytime": tunnel.esp_key_lifetime
            },         # copy your existing esp block
            "ipcomp":            "true" if tunnel.ipcomp else "false",
            "enabled":           "1"    if tunnel.is_enabled else "0",
            "dpdaction":         tunnel.dpdaction,
            "keyexchange":       tunnel.ike_version,
            "pre_shared_key":    tunnel.pre_shared_key,
        }
        # Hub → Branch
        ab = common.copy()
        ab.update({
            "local_ip":          mgmt_ip_a,
            "gateway":           mgmt_ip_b,
            "local_subnet":      [tunnel.device_a_subnet],
            "remote_subnet":     [tunnel.device_b_subnet],
            "local_identifier":  tunnel.local_identifier,
            "remote_identifier": tunnel.remote_identifier,
        })
        payloads.append({"method":"add-tunnel","payload":ab})
 
        # Branch → Hub
        ba = common.copy()
        ba.update({
            "local_ip":          mgmt_ip_b,
            "gateway":           mgmt_ip_a,
            "local_subnet":      [tunnel.device_b_subnet],
            "remote_subnet":     [tunnel.device_a_subnet],
            "local_identifier":  tunnel.remote_identifier,
            "remote_identifier": tunnel.local_identifier,
        })
        payloads.append({"method":"add-tunnel","payload":ba})
    print("payloads",payloads)
    return payloads