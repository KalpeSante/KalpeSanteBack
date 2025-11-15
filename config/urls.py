from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from rest_framework.permissions import AllowAny
schema_view = get_schema_view(
    openapi.Info(
        title="KALPÉ SANTÉ API",
        default_version='v1',
        description="API pour la plateforme de santé solidaire KALPÉ SANTÉ",
        terms_of_service="https://www.kalpe-sante.sn/terms/",
        contact=openapi.Contact(email="contact@kalpe-sante.sn"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    path('api/users/', include('apps.users.urls')),
    path('api/wallet/', include('apps.wallet.urls')),
    path('api/healthcare/', include('apps.healthcare.urls')),
    # path('api/pharmacy/', include('apps.pharmacy.urls')),
    # path('api/analytics/', include('apps.analytics.urls')),
    # path('api/v1/notifications/', include('apps.notifications.urls')),
     path("api/schema/", SpectacularAPIView.as_view(permission_classes=[AllowAny]), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema", permission_classes=[AllowAny]), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema", permission_classes=[AllowAny]), name="redoc"),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
