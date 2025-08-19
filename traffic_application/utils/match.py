# application/utils/match.py
from functools import lru_cache
from application.models import Application

class DomainMatcher:
    def __init__(self):
        self._map = {}  # domain -> Application.id

    def refresh_cache(self):
        self._map.clear()
        for app in Application.objects.only("id", "domains"):
            for d in app.domains or []:
                self._map[d.lower().strip(".")] = app.id

    @lru_cache(maxsize=2048)
    def classify(self, host: str):
        """Return (Application, [Category...]) or (None, [])"""
        if not host:
            return (None, [])
        h = host.lower().strip(".")
        # exact or suffix walk
        parts = h.split(".")
        for i in range(0, len(parts)):
            candidate = ".".join(parts[i:])
            app_id = self._map.get(candidate)
            if app_id:
                app = Application.objects.select_related().prefetch_related("categories").get(id=app_id)
                return (app, list(app.categories.all()))
        return (None, [])
