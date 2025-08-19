from datetime import timedelta
from django.utils.timezone import now

CSV_HEADERS = {
    "Device_Health_report": ["device_name", "serial_no", "management_ip", "memory_used_mb", "uptime"],
    "logs_report": ["ts","device_id","device_name","facility","severity","app","msg"],
    "bandwidth_links": ["site_id","site_name","device_id","device_name","ifname","provider","avg_mbps","peak_mbps","p95_mbps","total_gb","peak_time"],
    "qos_sla": ["device_id","device_name","hub_id","hub_name","path","latency_avg_ms","latency_p95_ms","jitter_avg_ms","jitter_p95_ms","loss_pct","availability_pct"],
    "availability": ["site_id","site_name","device_id","device_name","ifname","start","end","duration_s","root_cause"],
    "faults": ["site_id","site_name","device_id","device_name","category","faults","mtbf_hours","mttr_hours"],
    "dpi": ["application","protocol","site_id","site_name","device_id","device_name","bytes_down","bytes_up","flows","local_hosts","remote_hosts"],
    "traffic_throughput": ["site_id","site_name","total_down_gb","total_up_gb","peak_mbps","p95_mbps"],
    "network_performance": ["site_id","site_name","sli_pct","latency_ms","loss_pct","availability_pct"],
    "application_performance": ["application","latency_ms","loss_pct","outages","bytes_total"],
    "sla_violations": ["scope","metric","threshold","observed","start","end","duration_s","impact_gb","dedup_key"],
    "top_users": ["user_id","user_name","site_id","site_name","bytes_down","bytes_up","sessions","peak_mbps"],
    "cpe_health": ["site_id","site_name","device_id","device_name","uptime_s","cpu_pct","mem_used_mb","mem_total_mb","load1","load5"],
}

def csv_headers_for_report(slug: str):
    return CSV_HEADERS.get(slug)


def build_report_context(request, slug: str, ids=None):
    org = {"name": "Nexapp Demo Org", "logo_url": request.build_absolute_uri("/static/img/logo.png")}
    period = {"start": (now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M"),
              "end": now().strftime("%Y-%m-%d %H:%M")}
    devices = demo_devices()
    if ids:
        idset = set(ids)
        devices = [d for d in devices if d.get("id") in idset]
    ctx = {
        "org": org,
        "title": pretty_title(slug),
        "period": period,
        "timezone": "Asia/Kolkata",
        "generated_at": now().strftime("%Y-%m-%d %H:%M"),
        "filters_summary": "All sites; last 7 days",
        "kpis": demo_kpis(slug),
        "open_incidents": demo_open_incidents(),
        "recent_errors": demo_recent_errors(),
        "ranked_links": demo_ranked_links(),
        "paths": demo_paths(),
        "outages": demo_outages(),
        "fault_rows": demo_fault_rows(),
        "apps": demo_apps(),
        "top_sites": demo_top_sites(),
        "perf": demo_perf(),
        "app_perf": demo_app_perf(),
        "violations": demo_violations(),
        "users": demo_users(),
        "devices": devices,
        "dashboards": demo_dashboards(),
    }
    return ctx


def build_rows_for_report(slug: str, request, ctx):
    mapping = {
        "Device_Report": ctx["devices"],
        "logs_report": ctx["recent_errors"],
        "bandwidth_links": ctx["ranked_links"],
        "qos_sla": ctx["paths"],
        "availability": ctx["outages"],
        "faults": ctx["fault_rows"],
        "dpi": ctx["apps"],
        "traffic_throughput": ctx["top_sites"],
        "network_performance": ctx["perf"],
        "application_performance": ctx["app_perf"],
        "sla_violations": ctx["violations"],
        "top_users": ctx["users"],
        "cpe_health": ctx["devices"],
    }
    return mapping.get(slug, [])


def pretty_title(slug):
    return slug.replace("_", " ").title()

# ---- Demo data (replace with real OpenWISP queries) ----

def demo_kpis(slug):
    return [
        {"label": "Sites", "value": 42},
        {"label": "Devices", "value": 113},
        {"label": "Availability", "value": "99.91%"},
        {"label": "Incidents (7d)", "value": 12, "sub": "MTTR 38m"},
    ]


def demo_open_incidents():
    return [
        {"severity": "high", "event_type": "LinkDown", "device_name": "edge-01", "site_name": "Mumbai DC",
         "first_seen": "2025-08-11 10:21", "last_seen": "2025-08-11 10:45", "occurrences": 3, "status": "open"},
    ]


def demo_recent_errors():
    return [
        {"ts": "2025-08-12 09:12", "device_name": "ap-12", "facility": "daemon", "severity": "err", "app": "hostapd", "msg": "client disconnect"},
    ]


def demo_ranked_links():
    return [
        {"site_name": "Pune-01", "device_name": "edge-02", "ifname": "wan0", "provider": "Airtel", "avg_mbps": 120,
         "peak_mbps": 310, "p95_mbps": 280, "total_gb": 920},
    ]
def demo_dashboards():
    return [
        {"name": "Device Health", "meta": "All Device Health Report", "href": "/reports/device_health_report/"},
        {"name": "Network Performance", "meta": "SLA/Latency · Last 7d", "href": "/reports/network_performance/"},
        {"name": "Traffic & Throughput", "meta": "Top Sites · Last 7d", "href": "/reports/traffic_throughput/"},
        {"name": "CPE Health", "meta": "Uptime · CPU · Mem", "href": "/reports/cpe_health/"},
        {"name": "DPI ", "meta": "Uptime · CPU · Mem", "href": "/reports/cpe_health/"},
        {"name": "Alarm", "meta": "Uptime · CPU · Mem", "href": "/reports/cpe_health/"},
    ]

def demo_paths():
    return [
        {"device_name": "edge-03", "hub_name": "Hub-West", "path": "IPSec-1", "lat_avg": 18, "lat_p95": 27,
         "jit_avg": 2, "jit_p95": 5, "loss_pct": 0.1, "availability_pct": 99.95},
    ]


def demo_outages():
    return [
        {"site_name": "Navi Mumbai", "device_name": "edge-04", "ifname": "wan1", "start": "2025-08-10 01:10",
         "end": "2025-08-10 01:22", "duration": "00:12", "cause": "Provider"},
    ]


def demo_fault_rows():
    return [
        {"site_name": "Pune-01", "device_name": "edge-02", "category": "Interface", "count": 4, "mtbf_h": 230, "mttr_h": 0.6},
    ]


def demo_apps():
    return [
        {"application": "Teams", "protocol": "TLS", "bytes_down": 3_100_000_000, "bytes_up": 900_000_000,
         "flows": 4200, "local_hosts": 120, "remote_hosts": 35},
    ]


def demo_top_sites():
    return [
        {"site_name": "Pune-01", "total_down_gb": 420, "total_up_gb": 95, "peak_mbps": 310, "p95_mbps": 260},
    ]


def demo_perf():
    return [
        {"site_name": "Mumbai HQ", "sli_pct": 99.9, "latency_ms": 15, "loss_pct": 0.1, "availability_pct": 99.95},
    ]


def demo_app_perf():
    return [
        {"application": "SAP", "latency_ms": 110, "loss_pct": 0.4, "outages": 1, "bytes_total": 800_000_000},
    ]


def demo_violations():
    return [
        {"scope": "WAN: Pune-01", "metric": "Latency", "threshold": "< 80ms", "observed": "110ms", "start": "2025-08-09 10:00",
         "end": "2025-08-09 10:30", "duration": "00:30", "impact_gb": 5.2},
    ]


def demo_users():
    return [
        {"user_name": "rajiv.k", "site_name": "Mumbai HQ", "bytes_down": 120_000_000_000, "bytes_up": 15_000_000_000,
         "sessions": 88, "peak_mbps": 180},
    ]


def demo_devices():
    # Replace with real OpenWISP query later
    return [
        {
            "id": 101,
            "device_name": "edge-01",
            "serial_no": "SN-EDG-0001",
            "management_ip": "10.0.1.11",
            "memory_used_mb": 820,
            "uptime": "12d 04h",
        },
        {
            "id": 102,
            "device_name": "edge-02",
            "serial_no": "SN-EDG-0002",
            "management_ip": "10.0.1.12",
            "memory_used_mb": 640,
            "uptime": "5d 18h",
        },
        {
            "id": 103,
            "device_name": "ap-12",
            "serial_no": "SN-AP-0012",
            "management_ip": "10.0.2.55",
            "memory_used_mb": 256,
            "uptime": "3d 02h",
        },
    ]