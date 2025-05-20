from sdwan_tunnel.utils.logging_utils import structured_log
import requests

CONTROLLER_API_URL = "https://3.6.121.36/api/v1/controller/device/"
ONLINE_API_URL     = "https://3.6.121.36/api/v1/monitoring/device/"
TOKEN_API_URL      = "https://3.6.121.36/api/v1/users/token/"
USERNAME           = "admin"
PASSWORD           = "Nexapp@123"
 
def get_bearer_token():
    try:
        response = requests.post(
            TOKEN_API_URL,
            data={"username": USERNAME, "password": PASSWORD},
            verify=False ,timeout=10
        )
        # response.raise_for_status()
        return response.json().get("token")
    except Exception as e:
        print(f"[API ERROR] Failed to retrieve bearer token: {e}")
        return None
 
def fetch_online_devices_by_names(device_names):
    print(f"[DEBUG] Requesting devices for names: {device_names}")
    token = get_bearer_token()
    if not token:
       token = '80ee082483ee2a41d520909e571a3970f06d5907'
        

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(ONLINE_API_URL, headers=headers, verify=False, timeout=10)
        print(f"[DEBUG] Response URL: {response.url}")
        print(f"[DEBUG] Status Code: {response.status_code}")
        # response.raise_for_status()

        all_devices = response.json().get("results", [])
        # Keep only devices whose name is in device_names AND monitoring.status == "ok"
        filtered_devices = [
            d for d in all_devices
            if d.get("name") in device_names
               and d.get("monitoring", {}).get("status") == "ok"
        ]
        print(f"[DEBUG] Found {len(filtered_devices)} device(s) with status 'ok'")

        # Print each matched device's name and its monitoring status
        for dev in filtered_devices:
            name = dev.get("name")
            status = dev.get("monitoring", {}).get("status")
            print(f"Device '{name}' monitoring status: '{status}'")

        return filtered_devices

    except requests.RequestException as e:
        print(f"[API ERROR] Failed to fetch devices: {e}")
        return []
 
def fetch_management_ips_by_names(device_names):
    print(f"[DEBUG] Requesting management IPs for device names: {device_names}")
    token = get_bearer_token()
    if not token:
        token = '80ee082483ee2a41d520909e571a3970f06d5907'
 
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
 
    try:
        response = requests.get(CONTROLLER_API_URL, headers=headers, verify=False,timeout=15)
        print(f"[DEBUG] Response URL: {response.url}")
        print(f"[DEBUG] Status Code: {response.status_code}")
        response.raise_for_status()
        all_devices = response.json().get("results", [])
 
        filtered_devices = [d for d in all_devices if d.get("name")  in device_names]
        print(f"[DEBUG] Filtered to {len(filtered_devices)} matched device(s)")
        for dev in filtered_devices:
            print(f"[DEBUG] Matched Name: {dev['name']} | Management IP: {dev.get('management_ip')}")
 
        return {
            d["name"]: d.get("management_ip")
            for d in filtered_devices
        }
    except Exception as e:
        print(f"[API ERROR] Failed to fetch IPs: {e}")
        return {}
 
def get_ipsec_config_by_mgmt_ip(mgmt_ip):
        url = f"https://{mgmt_ip}/api-new/ipsec"
        payload = {
            "method": "get-config",
            "payload": {}
        }
        try:
            response = requests.post(url, json=payload, verify=False, timeout=15)
            response.raise_for_status()
            data = response.json()
            print(f"[DEBUG] Received IPSec config from {mgmt_ip}: {data}")
            return data
        except Exception as e:
           print(f"[API ERROR] Failed to fetch IPSec config from {mgmt_ip}: {e}")
           return {"status": "error", "message": str(e)}
        
def get_ip_config_by_mgmt_ip(mgmt_ip):
        url = f"https://{mgmt_ip}/api-new/ipsec"
        payload = {
            "method": "get-ip",
            "payload": {}
        }
        try:
            response = requests.post(url, json=payload, verify=False, timeout=15)
            response.raise_for_status()
            data = response.json()
            print(f"[DEBUG] Received IPSec config from {mgmt_ip}: {data}")
            return data
        except Exception as e:
           print(f"[API ERROR] Failed to fetch IPSec config from {mgmt_ip}: {e}")
           return {"status": "error", "message": str(e)}
 
   

 
def push_ipsec_config_by_mgmt_ip(mgmt_ip, config_data):
    """
    Push an IPsec tunnel configuration to a device's management API.
    """
    url = f"https://{mgmt_ip}/api-new/ipsec"
    payload = {
        "method": "add-tunnel",
        "payload": config_data
    }
    try:
        response = requests.post(url, json=payload, verify=False, timeout=15)
        response.raise_for_status()
        result = response.json()
        print(f"[DEBUG] Successfully pushed IPSec config to {mgmt_ip}: {result}")
        return result
    except Exception as e:
        print(f"[API ERROR] Failed to push IPSec config to {mgmt_ip}: {e}")
        return {"status": "error", "message": str(e)}