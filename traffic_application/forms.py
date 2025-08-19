# application/forms.py
from django import forms
from .models import Category, Application

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["tag_id", "name", "label", "description"]

class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ["app_id", "slug", "display_name", "categories", "domains", "meta", "last_update"]
