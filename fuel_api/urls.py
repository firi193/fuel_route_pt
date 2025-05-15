from django.urls import path
from .views import fuel_route_view

urlpatterns = [
    path('route/', fuel_route_view),
]
