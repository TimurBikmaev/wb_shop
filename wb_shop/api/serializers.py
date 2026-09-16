from django.contrib.auth import get_user_model
from rest_framework import serializers

from user.constants import UserConstants


User = get_user_model()


class ProductSerializer(serializers.ModelSerializer):
    """Сериализатор товара."""

    class Meta:
        model = User
        fields = ['name', 'description', 'price', 'quantity']


class CartSerializer(serializers.ModelSerializer):
    """Сериализатор корзины."""

    class Meta:
        model = User
        fields = ['email', 'first_name', 'balance']


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор пользователя."""
    cart = CartSerializer(many=True)

    class Meta:
        model = User
        fields = ['public_id', 'email', 'first_name', 'balance', 'cart']
