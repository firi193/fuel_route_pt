from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('fuel_api.urls')),  # Or use 'api/' prefix if you want
]
