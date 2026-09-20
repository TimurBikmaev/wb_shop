from django.urls import include, path, re_path
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
router_v1.register('orders', views.OrderViewSet, basename='orders')

urlpatterns = [
    re_path(
        rf'cart/item/(?P<product_public_id>{PublicIdConstants.PUBLIC_ID_REGEX})/',
        views.CartItemView.as_view(),
        name='cart_item',
    ),
    path('cart/', views.CartView.as_view(), name='cart'),
    path('auth/token/', TokenObtainPairView.as_view(), name='token'),
    path(
        'auth/token/refresh/',
        TokenRefreshView.as_view(),
        name='token_refresh',
    ),
    path('', include(router_v1.urls)),

    # path('search/', views.SearchView.as_view(), name='search'),
    # path('schema/', SpectacularAPIView.as_view(), name='schema'),
    # path(
    #     'docs/',
    #     SpectacularSwaggerView.as_view(url_name='schema'),
    #     name='swagger-ui',
    # )
]
