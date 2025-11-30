# sepl_project/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.core.management import call_command
from django.http import HttpResponse

def run_migrations(request):
    call_command("migrate")
    return HttpResponse("Migrations applied!")

urlpatterns = [
    path("run-migrate/", run_migrations),
    path('', include('auction.urls')),
    path('admin/', admin.site.urls),

    
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
