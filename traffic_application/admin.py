from django.contrib import admin
from traffic_application.models import Firewall
from traffic_application.models.application import Application, Category

# Register your models here.
@admin.register(Firewall)
class FirewallAdmin(admin.ModelAdmin):
    list_display = ('name',  'created_at')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("label", "tag_id", "name")
    search_fields = ("label", "name", "description")
    ordering = ("label",)
    readonly_fields = ("label", "tag_id", "name", "description")

    # view-only
    def has_view_permission(self, request, obj=None):
        return True
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("application_name", "category")
    search_fields = ("application_name",)          # tuple ✅
    # or: search_fields = ["application_name"]     # list ✅
    list_filter = ("category",)

    readonly_fields = (
        "application_name", "category",
        "domains", "meta", "last_update",
    )
    fieldsets = (
        (None, {"fields": ("application_name", "category")}),
        ("Detection", {"fields": ("domains",)}),
        ("Meta", {"fields": ("meta",)}),
        ("Sync", {"fields": ("last_update",)}),
    )
    def has_view_permission(self, request, obj=None): return True
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False