from django.urls import path, include
from rest_framework.routers import DefaultRouter

# from . import views

 
router = DefaultRouter()

urlpatterns = [
    path('/', include(router.urls)),
    # path('', views.tunnelconfig_form, name='tunnelconfig_form'), 
]