# application/management/commands/import_netify.py
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from traffic_application.models.application import Category, Application

APP_RE = re.compile(r"^app:(\d+):([A-Za-z0-9._-]+)\s*$")
DOM_RE = re.compile(r"^dom:(\d+):(.+)\s*$")

class Command(BaseCommand):
    help = "Import Netify categories/apps into two Django models (Category, Application)."

    def add_arguments(self, parser):
        parser.add_argument("--json", required=True, help="Path to Netify JSON (with application_tag_index/application_index/last_update)")
        parser.add_argument("--conf", required=True, help="Path to Netify Application Signatures (text)")

    def handle(self, *args, **opts):
        json_path = Path(opts["json"])
        conf_path = Path(opts["conf"])
        if not json_path.exists():
            raise CommandError(f"JSON file not found: {json_path}")
        if not conf_path.exists():
            raise CommandError(f"Conf file not found: {conf_path}")

        # -------- load JSON -----------
        data = json.loads(json_path.read_text())
        tag_index = data.get("application_tag_index", {})  # {"streaming-media": 29, ...}
        app_index = data.get("application_index", [])      # [[tag_id, [app_ids...]], ...]
        last_update = data.get("last_update")

        # create/update categories
        self.stdout.write("Importing categories...")
        id_to_category = {}
        for slug, tag_id in tag_index.items():
            label = slug.replace("-", " ").title()
            cat, _ = Category.objects.update_or_create(
                tag_id=tag_id,
                defaults={"name": slug, "label": label},
            )
            id_to_category[tag_id] = cat

        # map: app_id -> set(category_ids)
        app_to_category_ids = {}
        for pair in app_index:
            if not isinstance(pair, list) or len(pair) != 2:
                continue
            tag_id, app_ids = pair
            for aid in app_ids:
                app_to_category_ids.setdefault(aid, set()).add(tag_id)

        # -------- parse conf -----------
        self.stdout.write("Parsing signatures...")
        app_id_to_slug = {}
        app_id_to_domains = {}

        for line in conf_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = APP_RE.match(line)
            if m:
                app_id = int(m.group(1))
                slug = m.group(2)
                app_id_to_slug[app_id] = slug
                continue
            m = DOM_RE.match(line)
            if m:
                app_id = int(m.group(1))
                domain = m.group(2).lower()
                app_id_to_domains.setdefault(app_id, set()).add(domain)
                continue

       # -------- upsert applications -----------
        dt = None
        if isinstance(last_update, int):
            dt = datetime.fromtimestamp(last_update, tz=timezone.utc)
        
        self.stdout.write("Importing applications...")
        for app_id, slug in app_id_to_slug.items():
            # nice name, e.g. netify.youtube -> "Youtube"
            display_name = slug.split(".")[-1].replace("-", " ").title()
            domains = sorted(list(app_id_to_domains.get(app_id, [])))
        
            # pick one category (e.g. the smallest tag_id) or None
            tag_ids = sorted(app_to_category_ids.get(app_id, []))
            chosen_cat = id_to_category.get(tag_ids[0]) if tag_ids else None
        
            # your model has application_name (no app_id, no slug)
            app, _ = Application.objects.update_or_create(
                application_name=display_name,    # lookup / natural key
                defaults={
                    "category": chosen_cat,
                    "domains": domains,
                    "meta": {
                        "netify_app_id": app_id,  # keep numeric id here
                        "slug": slug,
                        "all_tag_ids": tag_ids,
                    },
                    "last_update": dt,
                },
            )
        
            # ensure FK is set even if the record already existed
            if app.category_id != (chosen_cat.id if chosen_cat else None):
                app.category = chosen_cat
                app.save(update_fields=["category"])

        self.stdout.write(self.style.SUCCESS("Done."))
