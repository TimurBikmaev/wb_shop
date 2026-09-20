import logging

from django.contrib.auth import get_user_model, logout
from django.core.mail import send_mail
from django.db.models import Count, Exists, OuterRef, Prefetch, Q, Value
from django.db.models import DecimalField, ExpressionWrapper, F, Sum, Window
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend

from drf_spectacular import utils as swg
from rest_framework import mixins, permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.generics import GenericAPIView
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet, ViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from api import serializers
from api.constants import MsgConstants as MSG
from api.mixins import LookupMixin
from core.constants import PublicIdConstants
from product.constants import CartConstants, ProductConstants
from product.models import Cart, CartItem, Product, Order, OrderItem
from product.services import CartOrderService
from user.models import VarificationCode
from user.services import send_email_code
from user.utils import generate_code
from user.validators import AuthValidator

logger = logging.getLogger(__name__)
User = get_user_model()


class AuthViewSet(ViewSet):
    """
    Аутентификация пользователя перед получением токена.

    Сначала пользователь регистрируется, вводя email и пароль.
    После он подтверждает свой email.
    """
    permission_classes = [AllowAny]

    @action(detail=False, methods=['post'])
    def register(self, request):
        """
        Регистрация пользователя.

        Пользователь указывает почту и пароль.
        В БД создается неактивный пользователь.
        Далее генерится и отправляется код потверждения почты.
        """
        serializer = serializers.AuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        user = User.objects.create_user(
            email=email,
            first_name=serializer.validated_data['first_name'],
            password=serializer.validated_data['password'],
            is_active=False,
        )

        send_email_code(user)

        return Response(
            {'detail': MSG.EMAIL_SEND_CODE.format(email=email)},
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=['post'],
        url_path='send-code'
    )
    def send_code(self, request):
        """Отправляет код подтверждения на почту пользователя."""
        serializer = serializers.SendCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        user = get_object_or_404(User, email=email)

        send_email_code(user)

        return Response(
            {'detail': MSG.EMAIL_SEND_CODE.format(email=email)},
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=['post'],
        url_path='verify-email'
    )
    def verify_email(self, request):
        """
        Потверждение почты пользователя.

        Пользователь указывает почту и код потверждения.
        Если код совпадает, то пользователь активируется.
        Если код не совпадает, то выбрасывается ошибка.

        Также создается корзина покупок, если ее нет.
        """
        serializer = serializers.VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code = serializer.validated_data['code']
        email = serializer.validated_data['email']

        user = get_object_or_404(User, email=email)

        AuthValidator.check_is_verified(user, email)
        AuthValidator.check_confirmation_code(user, code)

        if user.is_active is False:
            user.is_active = True
            user.save(update_fields=['is_active'])

        Cart.objects.get_or_create(user=user)

        return Response(
            {'detail': (
                'Email подтверждён. '
                'Перейдите в auth/token, чтобы получить токен доступа.'
            )},
            status=status.HTTP_200_OK,
        )

    @action(
        detail=False,
        methods=['patch'],
        url_path='change-email'
    )
    def change_email(self, request):
        """
        Смена почты пользователя.

        Пользователь указывает старую почту, пароль и новую почту.
        Нельзя указать одинаковые старую и новую почты.
        Нельзя указать существующую новую почту.
        Новую почту нужно подтвердить, так как пользователь дезактивируется.
        """
        serializer = serializers.ChangeEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        new_email = serializer.validated_data['new_email']

        user = get_object_or_404(User, email=old_email)
        if not user.check_password(password):
            raise ValidationError('Введен неверный пароль.')

        elif User.objects.filter(email=new_email).exists():
            raise ValidationError(
                f'Пользователь с почтой \'{new_email}\' уже существует.'
            )

        user.is_active = False
        user.email = new_email
        user.save(update_fields=['is_active', 'email'])

        return Response(
            {'detail': (
                'Email изменен. Перейдите в auth/send-code, '
                'чтобы получить код потверждения.'
            )},
            status=status.HTTP_200_OK,
        )

    @action(
        detail=False,
        methods=['patch'],
        url_path='change-password'
    )
    def change_password(self, request):
        """
        Смена пароля пользователя.

        Необходимо ввести код подтверждения и новый пароль.
        """
        serializer = serializers.ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        code = serializer.validated_data['code']
        new_password = serializer.validated_data['new_password']

        user = get_object_or_404(User, email=email)
        if user.check_password(new_password):
            raise ValidationError('Старый и новый пароли совпадают.')

        AuthValidator.check_confirmation_code(user, code)

        user.set_password(new_password)
        user.save(update_fields=['password'])

        return Response(
            {'detail': 'Пароль изменен.'},
            status=status.HTTP_200_OK,
        )


class UserViewSet(LookupMixin, ModelViewSet):
    model = User
    queryset = User.objects.all()
    # filter_backends = [DjangoFilterBackend, OrderingFilter]
    # ordering_fields = ['likes_count', 'comments_count']
    # ordering = ['-created_at']
    # parser_classes = [MultiPartParser, JSONParser]

    # def get_permissions(self):
    #     user = self.request.user

    #     if user.is_authenticated and not user.is_user:
    #         if self.action == 'partial_update':
    #             return [
    #                 perm.IsAuthenticated(),
    #                 IsModerOrStreamer(),
    #                 NotBannedAllowAny(),
    #             ]

    #     if self.action in ('like', 'report'):
    #         return [perm.IsAuthenticated(), NotBannedAllowAny()]

    #     return [
    #         NotBannedAllowAny(), perm.IsAuthenticatedOrReadOnly(), IsOwner()
    #     ]

    def get_serializer_class(self):
        """
        Все пользователи могут смотреть свой профиль.
        Только администратор может смотреть других пользователей.
        """
        user = self.request.user

        if user.is_authenticated and user.is_superuser:
            if self.action == 'list':
                return serializers.AdminListUserSerializer
            return serializers.AdminUserSerializer

        return serializers.ProfileSerializer

    @action(detail=False, methods=['get', 'patch', 'delete'])
    def me(self, request):
        """Возвращает профиль пользователя."""
        serializer = self.get_serializer(self.request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=['post'],
        url_path='me/balance',
    )
    def add_balance(self, request):
        """Пополняет баланс пользователя."""
        user = self.request.user

        serializer = serializers.BalanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        add_money = serializer.validated_data['add_money']
        user.balance += add_money
        user.save(update_fields=['balance'])

        serializer = self.get_serializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProductViewSet(LookupMixin, ModelViewSet):
    model = Product
    # filter_backends = [DjangoFilterBackend, OrderingFilter]
    # ordering_fields = ['likes_count', 'comments_count']
    # ordering = ['-created_at']
    # parser_classes = [MultiPartParser, JSONParser]

    # def get_permissions(self):
    #     user = self.request.user

    #     if user.is_authenticated and not user.is_user:
    #         if self.action == 'partial_update':
    #             return [
    #                 perm.IsAuthenticated(),
    #                 IsModerOrStreamer(),
    #                 NotBannedAllowAny(),
    #             ]

    #     if self.action in ('like', 'report'):
    #         return [perm.IsAuthenticated(), NotBannedAllowAny()]

    #     return [
    #         NotBannedAllowAny(), perm.IsAuthenticatedOrReadOnly(), IsOwner()
    #     ]

    def get_queryset(self):
        return Product.objects.filter(is_deleted=False)

    def get_serializer_class(self):
        """Обычному пользователю доступно только чтение."""
        user = self.request.user

        if user.is_authenticated and user.is_superuser:
            if self.action == 'list':
                return serializers.ProductAdminListSerializer
            return serializers.ProductAdminSerializer

        if self.action == 'list':
            return serializers.ProductListSerializer
        return serializers.ProductDetailSerializer

    def destroy(self, request, *args, **kwargs):
        """Реализация soft-delete."""
        public_id = kwargs['public_id']
        product = get_object_or_404(Product, public_id=public_id)

        if product.is_deleted is True:
            raise ValidationError(f'Товар {public_id} уже удален.')

        product.is_deleted = True
        product.deleted_at = timezone.now()
        product.save(update_fields=["is_deleted", "deleted_at"])

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['post'], detail=True)
    def restore(self, request, public_id=None):
        """Восстановить удаленный товар."""
        product = get_object_or_404(Product, public_id=public_id)

        if product.is_deleted is False:
            raise ValidationError(f'Товар {public_id} не удален.')

        product.is_deleted = False
        product.deleted_at = None
        product.save(update_fields=["is_deleted", "deleted_at"])

        serializer = self.get_serializer(product)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        methods=['post'],
        detail=True,
        url_path='add-to-cart',
    )
    def add_to_cart(self, request, public_id=None):
        """
        Добавляет товар в корзину.

        Если товар закончился, или он удален
        то выбрасывается ошибка.

        Если товар уже добавлен, то
        увеличивает его количество на один.
        """
        user = self.request.user
        cart = get_object_or_404(Cart, user=user)
        product = get_object_or_404(Product, public_id=public_id)

        if product.warehouse_quantity == ProductConstants.NOT_IN_WAREHOUSE:
            raise ValidationError(
                f'Товар \'{product.public_id}\' закончился на складе. '
                'Выберете другой товар.'
            )
        elif product.is_deleted is True:
            raise ValidationError(
                f'Товар \'{product.public_id}\' удален из магазина. '
                'Выберете другой товар.'
            )

        item, created = CartItem.objects.get_or_create(
            cart=cart, product=product
        )

        if created is False:
            item.item_quantity += CartConstants.ONE_ITEM
            item.save(update_fields=['item_quantity'])

        serializer = serializers.CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CartView(GenericAPIView):
    serializer_class = serializers.CartSerializer
    # filter_backends = [DjangoFilterBackend, OrderingFilter]
    # ordering_fields = ['likes_count', 'comments_count']
    # ordering = ['-created_at']
    # parser_classes = [MultiPartParser, JSONParser]

    def get(self, request, *args, **kwargs):
        """Возвращает содержимое корзины."""
        cart = CartOrderService.get_cart(self.request.user)

        serializer = self.get_serializer(cart)
        return Response(serializer.data)

    def delete(self, request):
        """Очистка корзины."""
        cart = get_object_or_404(Cart, user=request.user)
        cart.items.all().delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class CartItemView(APIView):

    def get_cart_item(self, product_public_id: str) -> tuple:
        """Проверяет существование позиции и возвращает ее."""
        cart = get_object_or_404(Cart, user=self.request.user)
        product = get_object_or_404(Product, public_id=product_public_id)
        item = get_object_or_404(CartItem, cart=cart, product=product)

        return cart, product, item

    def patch(self, request, product_public_id=None):
        """Меняет количество позиций товара в корзине."""
        cart, _, item = self.get_cart_item(product_public_id)

        serializer = serializers.PatchCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if item.item_quantity == serializer.validated_data['item_quantity']:
            raise ValidationError(
                f'В корзине уже находится {item.item_quantity} '
                f'позиции товара \'{product_public_id}\''
            )

        item.item_quantity = serializer.validated_data['item_quantity']
        item.save(update_fields=['item_quantity'])

        serializer = serializers.CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, product_public_id=None):
        """Удаляет все позиции товара из корзины."""
        cart, _, item = self.get_cart_item(product_public_id)
        item.delete()

        serializer = serializers.CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)


class OrderViewSet(
    LookupMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
):
    # filter_backends = [DjangoFilterBackend, OrderingFilter]
    # ordering_fields = ['likes_count', 'comments_count']
    # ordering = ['-created_at']
    # parser_classes = [MultiPartParser, JSONParser]

    def get_queryset(self):
        user = self.request.user

        queryset = Order.objects.filter(user=user)

        if user.is_authenticated and user.is_superuser:
            if self.action == 'list':
                return queryset.annotate(total_products=Count('items'))

        return queryset.prefetch_related(Prefetch(
            'items',
            queryset=OrderItem.objects.select_related('product')
        ))

    def get_serializer_class(self):
        """Обычному пользователю доступен просмотр только своих заказов."""
        user = self.request.user

        if user.is_authenticated and user.is_superuser:
            if self.action == 'list':
                return serializers.OrderAdminListSerializer

        return serializers.OrderSerializer

    def perform_create(self, serializer):
        """Сохраняем владельца заказа."""
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        """
        Для создания заказа необходимо указать адрес.

        Перед созданием проверяется наличие позиций в корзине
        и на складе, их статус удаления, а также баланс пользователя.

        Считают общую сумму всех позиций и суммы каждой позиции.
        Снимает деньги с баланса пользователя.
        Удаляет товары из корзины, уменьшает остатки на складе.
        """
        serializer = serializers.CreateOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = self.request.user
        address = serializer.validated_data['address']
        order = CartOrderService.create_order_from_cart(user, address)

        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
