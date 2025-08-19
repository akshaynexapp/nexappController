from django.http import HttpResponse, Http404
from django.shortcuts import render
from django.views import View
from django.utils.timezone import now
import csv
# controller_reports/admin_views.py
from django.contrib import admin
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.template.loader import select_template
from django.urls import reverse
from .services import build_report_context, build_rows_for_report, csv_headers_for_report
from django.template.loader import select_template


try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except Exception:
    WEASYPRINT_AVAILABLE = False


def reports_dashboard_admin_view(request):
    ctx = build_report_context(request, "all_report")
    ctx.update(admin.site.each_context(request))

    template = select_template([
        "admin/reports/all_report_admin.html",  # preferred (inside admin chrome)
        "reports/all_report_admin.html",        # fallback (you already have this file)
        "reports/all_report.html",              # final fallback (public page)
    ])
    return render(request, template.template.name, ctx)



@never_cache
def admin_report_slug_view(request, slug: str):
    # Reuse your existing report context
    ctx = build_report_context(request, slug)
    # Admin chrome (header/sidebar/user)
    ctx.update(admin.site.each_context(request))
    # Extras for templates
    ctx["slug"] = slug
    ctx["public_url"] = reverse("report", args=[slug])  # e.g. /reports/<slug>/

    # Prefer a dedicated admin template if present; else fall back to a generic iframe wrapper
    template = select_template([
        f"admin/reports/{slug}_admin.html",      # optional per-report admin template
        "admin/reports/generic_iframe.html",    # fallback wrapper
    ])
    return render(request, template.template.name, ctx)



class ReportView(View):
    """
    /reports/<slug>/?format=html|pdf|csv
    slug must match a template name without .html, e.g. 'events_report'
    """
    def get(self, request, slug: str):
        fmt = request.GET.get('format', 'html').lower()

        # parse selected ids like "?ids=101,102"
        ids_param = request.GET.get('ids')
        ids = [int(x) for x in ids_param.split(',') if x.strip().isdigit()] if ids_param else None

        template_name = f"reports/{slug}.html"
        ctx = build_report_context(request, slug, ids=ids)

        if fmt == 'csv':
            headers = csv_headers_for_report(slug)
            if not headers:
                raise Http404("CSV not defined for this report")
            rows = build_rows_for_report(slug, request, ctx)
            resp = HttpResponse(content_type='text/csv')
            resp['Content-Disposition'] = f'attachment; filename="{slug}.csv"'
            writer = csv.writer(resp)
            writer.writerow(headers)
            for r in rows:
                writer.writerow([r.get(h, "") for h in headers])
            return resp

        if fmt == 'pdf':
            if not WEASYPRINT_AVAILABLE:
                return HttpResponse("Install weasyprint to enable PDF export.", status=501)
            # Prefer a compact pdf template if present: reports/<slug>_pdf.html
            pdf_template = select_template([f"reports/{slug}_pdf.html", template_name])
            html_string = render(request, pdf_template.template.name, ctx).content.decode('utf-8')
            pdf = HTML(string=html_string).write_pdf()
            resp = HttpResponse(pdf, content_type='application/pdf')
            resp['Content-Disposition'] = f'inline; filename="{slug}.pdf"'
            return resp

        return render(request, template_name, ctx)