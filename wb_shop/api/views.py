import logging

from django.contrib.auth import get_user_model, logout
from django.core.mail import send_mail
from django.db.models import Count, Exists, OuterRef, Prefetch, Q, Value
from django.db.models import DecimalField, ExpressionWrapper, F, Sum, Window
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend

from drf_spectacular import utils as swg
from rest_framework import mixins, permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet, ViewSet

from api import serializers
from api.constants import MsgConstants as MSG
from api.mixins import LookupMixin
from api.validators import AuthValidator
from core.constants import PublicIdConstants
from product.constants import CartConstants
from product.models import Cart, CartItem, Product, Order
from user.models import VarificationCode
from user.services import send_email_code
from user.utils import generate_code

logger = logging.getLogger(__name__)
User = get_user_model()


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
        """
        Разделение для обычного пользователя и админаистратора.

        Обычному пользователю доступно только чтение.
        Администратору доступны все действия.
        """
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


class CartViewSet(ModelViewSet):
    model = Cart
    serializer_class = serializers.CartSerializer
    # filter_backends = [DjangoFilterBackend, OrderingFilter]
    # ordering_fields = ['likes_count', 'comments_count']
    # ordering = ['-created_at']
    # parser_classes = [MultiPartParser, JSONParser]

    def get_cart(self):
        """Возвращает корзину пользователя."""
        user = self.request.user
        return get_object_or_404(Cart, user=user)

    def get_queryset(self):
        """Возвращает содержимое корзины пользователя."""
        cart = self.get_cart()
        queryset = cart.items.select_related('product').annotate(
            item_total=ExpressionWrapper(
                F('product__price') * F('item_quantity'),
                output_field=DecimalField(
                    max_digits=10,
                    decimal_places=2,
                ),
            ),
            cart_total=Window(
                expression=Sum(
                    F('product__price') * F('item_quantity'),
                ),
            ),
        )

        # total = cart.items.aggregate(
        #     total=Sum(
        #         ExpressionWrapper(
        #             F('product__price') * F('item_quantity'),
        #             output_field=DecimalField(
        #                 max_digits=10,
        #                 decimal_places=2,
        #             ),
        #         )
        #     )
        # )['total']

        # return cart.items.select_related('product').annotate(
        #     total=ExpressionWrapper(
        #         F('product__price') * F('item_quantity'),
        #         output_field=DecimalField(
        #             max_digits=10,
        #             decimal_places=2,
        #         ),
        #     ),
        # )

    def destroy(self, request, *args, **kwargs):
        """Очистка корзины."""
        self.get_cart().items.all().delete()

        return Response(
            {'detail': 'Корзина очищена.'},
            status=status.HTTP_204_NO_CONTENT,
        )

    @action(
        methods=['post', 'patch'],
        detail=False,
        url_path=rf'item/(?P<item_public_id>{PublicIdConstants.URL_REGEX})',
    )
    def item(self, request, item_public_id=None):
        """
        Добавляет одну позицию в корзину.

        Если позиция уже добавелна, то
        увеличивает количество позиции на один.
        """
        cart = self.get_cart()
        product = get_object_or_404(Product, public_id=item_public_id)

        if request.method == 'POST':
            item, created = CartItem.objects.get_or_create(
                cart=cart, product=product
            )

            if created is False:
                item.item_quantity += CartConstants.ONE_ITEM
                item.save(update_fields=['item_quantity'])

            serializer = self.get_serializer(cart)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == 'PATCH':
            serializer = serializers.PatchCartItemSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            item = get_object_or_404(CartItem, cart=cart, product=product)
            item.item_quantity += serializer.validated_data['item_quantity']
            item.save(update_fields=['item_quantity'])

            serializer = self.get_serializer(cart)
            return Response(serializer.data, status=status.HTTP_200_OK)


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


class AuthViewSet(ViewSet):
    """
    Аутентификация пользователя перед получением токена.

    Сначала пользователь регистрируется, вводя email и пароль.
    После он подтверждает свой email.
    """
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
