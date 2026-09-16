from django.contrib.auth import get_user_model
from rest_framework import serializers

from api.constants import SerializerConstants
from product.models import Cart, Order, Product


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

    Включает поля ShortProduct и цену, статус удаления.
    """

    class Meta(ShortProductSerializer.Meta):
        fields = ['public_id', 'name', 'price', 'is_deleted']


class ProductDetailSerializer(serializers.ModelSerializer):
    """
    Подробное отображение товара для обычного пользователя.

    Включает поля ProductList и описание товара.
    """

    class Meta(ProductListSerializer.Meta):
        fields = ['public_id', 'name', 'price', 'is_deleted', 'description']


class ProductAdminListSerializer(serializers.ModelSerializer):
    """
    Отображение каталога товаров для админа.

    Включает поля ProductList
    и даты создания, обновления, удаления.
    """

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + [
            'created_at', 'updated_at', 'deleted_at'
        ]


class ProductAdminSerializer(serializers.ModelSerializer):
    """
    Подробное отображение, создание и изменение товара для админа.

    Включает поля ProductAdminList + описание товара.

    Обязательные поля при создании: наименование, описание, цена, количество.
    Обновить можно те же поля + статус удаления.
    """

    class Meta(ProductAdminListSerializer.Meta):
        fields = ProductAdminListSerializer.Meta.fields + ['description']


class ListCreateCartSerializer(serializers.ModelSerializer):
    """
    Отображения и создание корзин покупок.

    Включает публичный id, наименование, общую стоимость,
    даты создания и обновления, количество товаров в корзине.

    Обязательные поля при создании: name.
    """
    total_products = ...  # read_only
    total_price = ...  # read_only

    class Meta:
        model = Cart
        fields = SerializerConstants.CART_COMMON_FIELDS + ['total_products']


class CartSerializer(serializers.ModelSerializer):
    # Лучше отдельно эндпоинты добавления, удаления товаров
    # в корзине сделать
    """
    Подробное отображение и обновление корзины покупок.

    Включает публичный id, наименование, общую стоимость,
    даты создания и обновления, добавленные товары.

    Обновить можно только наименование и добавленные товары.
    """
    products = ProductListSerializer(many=True)

    class Meta(ListCreateCartSerializer.Meta):
        fields = SerializerConstants.CART_COMMON_FIELDS + ['products']


class ShortUserSerializer(serializers.ModelSerializer):
    """
    Краткое отображение пользователя.

    Включает публиный id и email.
    """

    class Meta:
        model = User
        fields = ['public_id', 'email']


class OrderListCreateSerializer(serializers.ModelSerializer):
    """
    Отображение и создание заказов для обычного пользователя.

    Включает публичный id, общую стоимость, адрес,
    статус, даты создания и обновления, кратко продукты.

    Обязательные поля при создании: address.
    """
    # Количество товаров нужно отображать из корзины
    products = ShortProductSerializer(many=True)
    total_price = ...  # read_only

    class Meta:
        model = Order
        fields = SerializerConstants.ORDER_COMMON_FIELDS + ['products']


class OrderDetailSerializer(serializers.ModelSerializer):
    """
    Подробное отображение для обычного пользователя.

    Включает публичный id, общую стоимость, адрес,
    статус, даты создания и обновления, продукты.
    """
    # Количество товаров нужно отображать из корзины
    products = ProductListSerializer(many=True)
    total_price = ...  # read_only

    class Meta(OrderListCreateSerializer.Meta):
        fields = SerializerConstants.ORDER_COMMON_FIELDS + ['products']


class OrderAdminListSerializer(serializers.ModelSerializer):
    """
    Отображение заказа для админа.

    Включает публичный id, общую стоимость,
    адрес, статус, даты создания и обновления,
    количество продуктов, кратко пользователя.
    """
    user = ShortUserSerializer()
    total_products = ...  # read_only
    total_price = ...  # read_only

    class Meta(OrderListCreateSerializer.Meta):
        fields = SerializerConstants.ORDER_COMMON_FIELDS + [
            'total_products', 'user'
        ]


class OrderAdminSerializer(serializers.ModelSerializer):
    """
    Подробное отображение и обновление заказа для админа.

    Включает публичный id, общую стоимость, адрес,
    статус, даты создания и обновления, продукты,
    кратко пользователя.

    Обновить можно только статус.
    """
    user = ShortUserSerializer()
    # Количество товаров нужно отображать из корзины
    products = ProductListSerializer(many=True)
    total_price = ...  # read_only

    class Meta(OrderDetailSerializer.Meta):
        fields = SerializerConstants.ORDER_COMMON_FIELDS + [
            'products', 'user'
        ]
        read_only_fields = ['address']
