from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.validators import RegexValidator
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.serializers import ValidationError

from api.constants import SerializerConstants
from api.mixins import BaseSerializerMixin
from product.models import Cart, CartItem, Order, Product
from user.constants import AuthConstants


User = get_user_model()


class ShortProductSerializer(serializers.ModelSerializer):
    """
    Краткое отображения товаров.

    Включает публичный id, наименование и количество.
    """

    class Meta:
        model = Product
        fields = ['public_id', 'name']


class ProductListSerializer(serializers.ModelSerializer):
    """
    Отображение каталога товаров для обычного пользователя.

    Включает поля ShortProduct и цену, количество статус удаления.
    """

    class Meta(ShortProductSerializer.Meta):
        fields = [
            'public_id', 'name', 'price',
            'warehouse_quantity', 'is_deleted'
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    """
    Подробное отображение товара для обычного пользователя.

    Включает поля ProductList и описание товара.
    """

    class Meta(ProductListSerializer.Meta):
        fields = ['public_id', 'name', 'price', 'is_deleted', 'description']


class ProductAdminListSerializer(BaseSerializerMixin):
    """
    Отображение каталога товаров для админа.

    Включает поля ProductList
    и даты создания, обновления, удаления.
    """

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + [
            'created_at', 'updated_at', 'deleted_at'
        ]


class ProductAdminSerializer(BaseSerializerMixin):
    """
    Подробное отображение, создание и изменение товара для админа.

    Включает поля ProductAdminList + описание товара.

    Обязательные поля при создании: наименование, описание, цена, количество.
    Обновить можно те же поля.
    """

    class Meta(ProductAdminListSerializer.Meta):
        fields = ProductAdminListSerializer.Meta.fields + ['description']
        read_only_fields = ['is_deleted']


class PatchCartItemSerializer(serializers.ModelSerializer):
    """Изменение количества позиций одного товара."""

    class Meta:
        model = CartItem
        fields = ['item_quantity']


class CartItemSerializer(serializers.ModelSerializer):
    """
    Отображение позиций в корзине покупок.

    Включает публичный id, наименование,
    количество в корзине и цену продукта.
    """
    public_id = serializers.ReadOnlyField(source='product.public_id')
    name = serializers.ReadOnlyField(source='product.name')
    price = serializers.ReadOnlyField(source='product.price')

    class Meta(PatchCartItemSerializer.Meta):
        fields = ['public_id', 'name', 'item_quantity', 'price']


class CartSerializer(serializers.ModelSerializer):
    """
    Отображение корзины покупок.

    Включает добавленные товары, общую стоимость,
    даты создания и обновления.
    """
    products = CartItemSerializer(many=True)
    total_price = ...

    class Meta:
        model = Cart
        fields = ['products', 'total_price', 'created_at', 'updated_at']


class ShortUserSerializer(serializers.ModelSerializer):
    """
    Краткое отображение пользователя.

    Включает публиный id и email.
    """

    class Meta:
        model = User
        fields = ['public_id', 'email']


# class OrderListCreateSerializer(serializers.ModelSerializer):
#     """
#     Отображение и создание заказов для обычного пользователя.

#     Включает публичный id, общую стоимость, адрес,
#     статус, даты создания и обновления, кратко продукты.

#     Обязательные поля при создании: address.
#     """
#     # Количество товаров нужно отображать из корзины
#     products = ShortProductSerializer(many=True)
#     total_price = ...  # read_only

#     class Meta:
#         model = Order
#         fields = SerializerConstants.ORDER_COMMON_FIELDS + ['products']


# class OrderDetailSerializer(serializers.ModelSerializer):
#     """
#     Подробное отображение для обычного пользователя.

#     Включает публичный id, общую стоимость, адрес,
#     статус, даты создания и обновления, продукты.
#     """
#     # Количество товаров нужно отображать из корзины
#     products = ProductListSerializer(many=True)
#     total_price = ...  # read_only

#     class Meta(OrderListCreateSerializer.Meta):
#         fields = SerializerConstants.ORDER_COMMON_FIELDS + ['products']


# class OrderAdminListSerializer(serializers.ModelSerializer):
#     """
#     Отображение заказа для админа.

#     Включает публичный id, общую стоимость,
#     адрес, статус, даты создания и обновления,
#     количество продуктов, кратко пользователя.
#     """
#     user = ShortUserSerializer()
#     total_products = ...  # read_only
#     total_price = ...  # read_only

#     class Meta(OrderListCreateSerializer.Meta):
#         fields = SerializerConstants.ORDER_COMMON_FIELDS + [
#             'total_products', 'user'
#         ]


# class OrderAdminSerializer(serializers.ModelSerializer):
#     """
#     Подробное отображение и обновление заказа для админа.

#     Включает публичный id, общую стоимость, адрес,
#     статус, даты создания и обновления, продукты,
#     кратко пользователя.

#     Обновить можно только статус.
#     """
#     user = ShortUserSerializer()
#     # Количество товаров нужно отображать из корзины
#     products = ProductListSerializer(many=True)
#     total_price = ...  # read_only

#     class Meta(OrderDetailSerializer.Meta):
#         fields = SerializerConstants.ORDER_COMMON_FIELDS + [
#             'products', 'user'
#         ]
#         read_only_fields = ['address']


class ProfileSerializer(serializers.ModelSerializer):
    """
    Отображение и редактирование своего профиля.

    Включает публиный id, email, имя,
    баланс, корзину и заказы пользователя.

    Обновить можно только имя.
    """
    # cart = CartSerializer()
    # orders = OrderListCreateSerializer(mane=True)

    class Meta(ShortUserSerializer.Meta):
        fields = [
            'public_id', 'email', 'first_name',
            'balance',
            # 'cart', 'orders'
        ]
        read_only_fields = ['balance', 'cart', 'orders', 'email']


class BalanceSerializer(serializers.ModelSerializer):
    """
    Редактирование своего баланса.

    Включает баланс пользователя.
    """

    class Meta(ShortUserSerializer.Meta):
        fields = ['balance']


class AdminListUserSerializer(serializers.ModelSerializer):
    """
    Отображение пользователей для админа.

    Включает публиный id, email, имя,
    количество заказов, сумму заказов.
    """
    # total_orders = ...  # read_only
    # total_purchases = ...  # read_only

    class Meta(ShortUserSerializer.Meta):
        fields = [
            'public_id', 'email', 'first_name',
            # 'total_orders', 'total_purchases'
        ]


class AdminUserSerializer(serializers.ModelSerializer):
    """
    Подробное отображение, обновления пользователя для админа.

    Включает публиный id, email, имя, баланс,
    количество заказов, сумму заказов, заказы.
    """
    # total_orders = ...  # read_only
    # total_purchases = ...  # read_only
    # orders = OrderListCreateSerializer(mane=True)

    class Meta(ShortUserSerializer.Meta):
        fields = [
            'public_id', 'email', 'first_name', 'balance',
            # 'total_orders', 'total_purchases', 'orders',
        ]
        read_only_fields = [
            'email', 'first_name', 'balance',
            # 'orders'
        ]


class AuthSerializer(serializers.ModelSerializer):
    """
    Регистрация и аутентификаця пользователя.

    Необходимо указать email и пароль.
    """
    password = serializers.CharField(validators=[validate_password])

    class Meta(ShortUserSerializer.Meta):
        fields = ['email', 'first_name', 'password']


class SendCodeSerializer(serializers.Serializer):
    """Повторая отправка кода для подтверждения email."""
    email = serializers.EmailField()


class VerifyEmailSerializer(serializers.Serializer):
    """
    Потверждение указанной пользователем почты.

    Необходимо указать email и код подтверждения.
    """
    email = serializers.EmailField()
    code = serializers.CharField(
        validators=[RegexValidator(AuthConstants.EMAIL_CODE_REGEX)],
    )


class ChangeEmailSerializer(serializers.Serializer):
    """
    Смена email.

    Необходимо указать старую почту, пароль и новую почту.
    """
    email = serializers.EmailField()
    password = serializers.CharField()
    new_email = serializers.EmailField()

    def validate(self, attrs):
        """Старая и новая почты должны быть различны."""
        if attrs['email'] == attrs['new_email']:
            raise ValidationError('Новая почта должна отличаться от старой.')

        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """
    Смена пароля.

    Необходимо указать код потверждения и новый пароль.
    """
    email = serializers.EmailField()
    code = serializers.CharField(
        validators=[RegexValidator(AuthConstants.EMAIL_CODE_REGEX)],
        error_messages={
            'required': (
                'Для обновления пароля необходимо ввести код подтверждения '
                'из почты. Сделайте POST-запрос на auth/send-code.'
            ),
        },
    )
    new_password = serializers.CharField(validators=[validate_password])
