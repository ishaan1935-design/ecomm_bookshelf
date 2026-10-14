"""
URL configuration for MEcomm project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
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
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.views.generic import RedirectView
# Import the URL patterns directly from the library
from two_factor.urls import urlpatterns as tf_urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path('',include('store.urls')),
    # Use the directly imported patterns here
    path('', include(tf_urls)),
    # path('', include('two_factor.urls')),
    # path('myauth/login/', RedirectView.as_view(url='/account/login/', permanent=False)),
    path('myauth/', include('django.contrib.auth.urls')),
    path("accounts/", include("allauth.urls")),
]
urlpatterns+=static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)
