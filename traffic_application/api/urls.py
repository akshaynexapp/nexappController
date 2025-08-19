from django.urls import path, include
from rest_framework.routers import DefaultRouter
from ..api.views import FirewallViewSet ,ApplicationViewSet , CategoryViewSet

router = DefaultRouter()


router.register('firewall', FirewallViewSet, basename='firewall')
router.register('application', ApplicationViewSet, basename='application')
router.register('category', CategoryViewSet, basename='category')




urlpatterns = [
    path('', include(router.urls)),

]


