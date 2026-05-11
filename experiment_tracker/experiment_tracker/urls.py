"""
URL configuration for experiment_tracker project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin  # Django admin site module
from django.urls import path, include      # Function used to define URL patterns
from django.conf import settings           # Access project settings
from django.conf.urls.static import static  # Helper function to serve static files during development

# URL configuration for the project
urlpatterns = [
    path('admin/', admin.site.urls),  # Routes /admin/ to Django admin interface
    path('', include('expt_webapp.urls')), # Routes all other URLs to the URL patterns defined in the expt_webapp application
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)  # Serve media files during development
