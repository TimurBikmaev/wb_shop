from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView, TokenRefreshView,
)

from api import views
from core.constants import PublicIdConstants


router_v1 = DefaultRouter()

router_v1.register('auth', views.AuthViewSet, basename='auth')
router_v1.register('users', views.UserViewSet, basename='users')
router_v1.register('products', views.ProductViewSet, basename='products')
# router_v1.register(
#     rf'posts/(?P<post_id>{PublicIdConstants.URL_REGEX})/comments',
#     views.CommentViewSet,
#     basename='comments'
# )
# router_v1.register('reports', views.ReportViewSet, basename='reports')
# router_v1.register('videos', views.VideoViewSet, basename='videos')


urlpatterns = [
    path('v1/auth/token/', TokenObtainPairView.as_view()),
    path('v1/auth/token/refresh/', TokenRefreshView.as_view()),
    path('v1/', include(router_v1.urls)),

    # path('v1/search/', views.SearchView.as_view(), name='search'),
    # path('v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    # path(
    #     'v1/docs/',
    #     SpectacularSwaggerView.as_view(url_name='schema'),
    #     name='swagger-ui',
    # )
]
