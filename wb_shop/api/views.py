import logging

from django.contrib.auth import get_user_model
from django.db.models import Count, DecimalField, Prefetch, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular import utils as swg
from rest_framework import mixins, permissions as perm, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet, ViewSet
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from api import serializers
from api.constants import MsgConstants as MSG
from api.mixins import HttpLookupMixin
from core.constants import MoneyConstants
from product.constants import CartConstants, ProductConstants, Status
from product.models import Cart, CartItem, Order, OrderItem, Product
from product.services import CartOrderService
from user.permissions import IsAdmin
from user.services import send_email_code
from user.validators import AuthValidator, ProfileValidator

logger = logging.getLogger(__name__)
User = get_user_model()


@swg.extend_schema(
    tags=['Аутентификация'],
    summary='Получить токены доступа и обновления',
    description=(
        'Принимает почту и пароль пользователя. Возвращает пару '
        'JSON Web Token (токен доступа и токен обновления). '
        'Подтверждает аутентификацию с использованием этих данных.'
    )
)
class CustomTokenObtainPairView(TokenObtainPairView):
    pass


@swg.extend_schema(
    tags=['Аутентификация'],
    summary='Получить токен обновления',
    description=(
        'Принимает JSON Web Token (JWT) обновления и возвращает '
        'JWT доступа, если токен обновления действителен.'
    )
)
class CustomTokenRefreshView(TokenRefreshView):
    pass


@swg.extend_schema(tags=['Аутентификация'])
class AuthViewSet(ViewSet):
    """
    Аутентификация пользователя перед получением токена.

    Сначала пользователь регистрируется, вводя email и пароль.
    После он подтверждает свой email.
    """
    permission_classes = [perm.AllowAny]

    @swg.extend_schema(
        summary='Регистрация пользователя',
        description=(
            'Создает неактивного пользователя по указанным email, имени и '
            'паролю. После регистрации на указанную почту отправляется код '
            'подтверждения. Для завершения регистрации необходимо подтвердить '
            'email через эндпоинт auth/verify-email.'
        ),
        request=serializers.AuthSerializer,
        responses={
            status.HTTP_201_CREATED: swg.OpenApiResponse(
                description=(
                    'Пользователь создан. Код подтверждения отправлен '
                    'на указанную почту.'
                )
            ),
            status.HTTP_400_BAD_REQUEST: swg.OpenApiResponse(
                description='Ошибка валидации данных.'
            ),
        },
    )
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

        logger.info(
            'Зарегистрирован пользователь с id %s',
            user.id
        )

        return Response(
            {'detail': MSG.EMAIL_SEND_CODE.format(email=email)},
            status=status.HTTP_201_CREATED,
        )

    @swg.extend_schema(
        summary='Отправить код подтверждения',
        description=(
            'Отправляет новый код подтверждения на почту зарегистрированного '
            'пользователя.'
        ),
        request=serializers.SendCodeSerializer,
        responses={
            status.HTTP_201_CREATED: swg.OpenApiResponse(
                description='Код подтверждения отправлен на указанную почту.'
            ),
            status.HTTP_400_BAD_REQUEST: swg.OpenApiResponse(
                description='Ошибка валидации данных.'
            ),
            status.HTTP_404_NOT_FOUND: swg.OpenApiResponse(
                description='Пользователь с указанной почтой не найден.'
            ),
        },
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

        logger.info(
            'Пользователю с id %s отправлен код подтверждения на %s',
            user.id,
            email,
        )

        return Response(
            {'detail': MSG.EMAIL_SEND_CODE.format(email=email)},
            status=status.HTTP_201_CREATED,
        )

    @swg.extend_schema(
        summary='Подтвердить email',
        description=(
            'Подтверждает email пользователя по коду. При успешной проверке '
            'кода неактивный пользователь активируется. Также создается '
            'корзина покупок, если она отсутствует.'
        ),
        request=serializers.VerifyEmailSerializer,
        responses={
            status.HTTP_200_OK: swg.OpenApiResponse(
                description=(
                    'Email подтвержден. Пользователь активирован и может '
                    'получить токен доступа.'
                )
            ),
            status.HTTP_400_BAD_REQUEST: swg.OpenApiResponse(
                description='Неверный код подтверждения или ошибка валидации.'
            ),
            status.HTTP_404_NOT_FOUND: swg.OpenApiResponse(
                description='Пользователь с указанной почтой не найден.'
            ),
        },
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

        logger.info(
            'Email подтвержден пользователем c id %s',
            user.id
        )

        return Response(
            {'detail': (
                'Email подтверждён. '
                'Перейдите в auth/token, чтобы получить токен доступа.'
            )},
            status=status.HTTP_200_OK,
        )

    @swg.extend_schema(
        summary='Изменить email',
        description=(
            'Изменяет email пользователя после проверки текущей почты и '
            'пароля. Новая почта не должна быть занята другим пользователем. '
            'После изменения пользователь деактивируется и должен повторно '
            'подтвердить новый email.'
        ),
        request=serializers.ChangeEmailSerializer,
        responses={
            status.HTTP_200_OK: swg.OpenApiResponse(
                description=(
                    'Email изменен. Пользователь деактивирован и должен '
                    'подтвердить новый email.'
                )
            ),
            status.HTTP_400_BAD_REQUEST: swg.OpenApiResponse(
                description=(
                    'Неверный пароль, новая почта уже существует или '
                    'переданы некорректные данные.'
                )
            ),
            status.HTTP_404_NOT_FOUND: swg.OpenApiResponse(
                description='Пользователь со старой почтой не найден.'
            ),
        },
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

        logger.info(
            'Пользователь с id %s изменил email: %s -> %s',
            user.id,
            old_email,
            new_email
        )

        return Response(
            {'detail': (
                'Email изменен. Перейдите в auth/send-code, '
                'чтобы получить код потверждения.'
            )},
            status=status.HTTP_200_OK,
        )

    @swg.extend_schema(
        summary='Изменить пароль',
        description=(
            'Изменяет пароль пользователя после проверки кода подтверждения '
            'email. Новый пароль не должен совпадать с текущим.'
        ),
        request=serializers.ChangePasswordSerializer,
        responses={
            status.HTTP_200_OK: swg.OpenApiResponse(
                description='Пароль успешно изменен.'
            ),
            status.HTTP_400_BAD_REQUEST: swg.OpenApiResponse(
                description=(
                    'Новый пароль совпадает с текущим, код подтверждения '
                    'некорректен или переданы некорректные данные.'
                )
            ),
            status.HTTP_404_NOT_FOUND: swg.OpenApiResponse(
                description='Пользователь с указанной почтой не найден.'
            ),
        },
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

        logger.info(
            'Пользователь c id %s изменил пароль',
            user.id
        )

        return Response(
            {'detail': 'Пароль изменен.'},
            status=status.HTTP_200_OK,
        )


@swg.extend_schema(tags=['Пользователи'])
@swg.extend_schema_view(
    list=swg.extend_schema(
        summary='Получить список пользователей',
        description=(
            'Возвращает список пользователей. Доступно только администратору. '
            'Для каждого пользователя отображается общее количество заказов '
            'и общая сумма покупок. По умолчанию пользователи отсортированы '
            'по общей сумме покупок от большей к меньшей. Доступна сортировка '
            'по общему количеству заказов и общей сумме покупок.'
        ),
        parameters=[
            swg.OpenApiParameter(
                name='ordering',
                description='Сортировка пользователей',
                required=False,
                type=str,
                enum=[
                    'total_orders',
                    '-total_orders',
                    'total_purchases',
                    '-total_purchases',
                ],
            ),
        ],
        responses={
            status.HTTP_200_OK: serializers.AdminListUserSerializer(many=True),
            status.HTTP_403_FORBIDDEN: swg.OpenApiResponse(
                description='Доступно только администратору.'
            ),
        },
    ),
    retrieve=swg.extend_schema(
        summary='Получить пользователя',
        description=(
            'Возвращает подробную информацию о пользователе, включая '
            'общее количество заказов, общую сумму покупок и список '
            'заказов с товарами. Доступно только администратору.'
        ),
        responses={
            status.HTTP_200_OK: serializers.AdminUserSerializer,
            status.HTTP_403_FORBIDDEN: swg.OpenApiResponse(
                description='Доступно только администратору.'
            ),
            status.HTTP_404_NOT_FOUND: swg.OpenApiResponse(
                description='Пользователь не найден.'
            ),
        },
    ),
    partial_update=swg.extend_schema(
        summary='Изменить пользователя',
        description=(
            'Изменяет данные пользователя. Администратор может изменять '
            'других пользователей, но не может изменять состояние своего '
            'профиля через данный эндпоинт. Для изменения собственного '
            'профиля необходимо использовать users/me.'
        ),
        request=serializers.AdminUserSerializer,
        responses={
            status.HTTP_200_OK: serializers.AdminUserSerializer,
            status.HTTP_400_BAD_REQUEST: swg.OpenApiResponse(
                description='Ошибка валидации данных.'
            ),
            status.HTTP_403_FORBIDDEN: swg.OpenApiResponse(
                description='Доступно только администратору.'
            ),
            status.HTTP_404_NOT_FOUND: swg.OpenApiResponse(
                description='Пользователь не найден.'
            ),
        },
    ),
)
class UserViewSet(
    HttpLookupMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
):
    """
    Управление профилями пользователей.

    Пользователь может просматривать, изменять и удалять свой профиль.
    Администратор — просматривать и изменять других пользователей.
    """
    model = User

    filter_backends = [OrderingFilter]
    ordering_fields = ['total_orders', 'total_purchases']
    ordering = ['-total_purchases']

    def get_permissions(self):
        """Доступ к другим пользователя только у администратора."""
        if self.action in ('me', 'add_balance'):
            return [perm.IsAuthenticated()]

        return [IsAdmin()]

    def get_queryset(self):
        """
        Отображение профиля пользователя для админа.

        Всегда содержит общее количество заказов и общую сумму покупок.
        В подробном отображении содержит все заказы с товарами.
        """
        queryset = User.objects.all().annotate(
            total_orders=Count('orders'),
            total_purchases=Coalesce(
                Sum('orders__total_price'),
                Value(MoneyConstants.NO_MONEY),
                output_field=DecimalField(
                    max_digits=MoneyConstants.MAX_DIGITS,
                    decimal_places=MoneyConstants.DECIMAL_PLACES,
                ),
            ),
        )

        if self.action == 'retrieve':
            orders_queryset = Order.objects.all().prefetch_related(
                Prefetch(
                    'items',
                    queryset=OrderItem.objects.select_related('product'),
                )
            )

            queryset = queryset.prefetch_related(
                Prefetch('orders', queryset=orders_queryset)
            )

        return queryset

    def get_serializer_class(self):
        """
        Все пользователи могут смотреть свой профиль.
        Только администратор может смотреть других пользователей.
        """
        if self.action == 'me':
            return serializers.ProfileSerializer

        if self.action == 'list':
            return serializers.AdminListUserSerializer
        return serializers.AdminUserSerializer

    def partial_update(self, request, *args, **kwargs):
        """Администратор не может изменять свой объект пользователя."""
        user = get_object_or_404(User, public_id=kwargs['public_id'])

        if request.user == user:
            raise ValidationError(
                'Администратор может менять свой профиль, но не состояние. '
                'Отправьте PATCH-запрос на users/me.'
            )

        response = super().partial_update(request, *args, **kwargs)

        logger.info(
            'Администратор с id %s изменил пользователя с id %s',
            request.user.id,
            user.id
        )

        return response

    @swg.extend_schema(
        methods=['GET'],
        summary='Получить свой профиль',
        description=(
            'Возвращает профиль текущего авторизованного пользователя, '
            'включая информацию о количестве заказов и общей сумме покупок.'
        ),
        responses={
            status.HTTP_200_OK: serializers.ProfileSerializer,
            status.HTTP_401_UNAUTHORIZED: swg.OpenApiResponse(
                description='Пользователь не авторизован.'
            ),
        },
    )
    @swg.extend_schema(
        methods=['PATCH'],
        summary='Изменить свой профиль',
        description=(
            'Изменяет имя текущего пользователя. Для изменения email '
            'и пароля используются отдельные эндпоинты.'
        ),
        request=serializers.ProfileSerializer,
        responses={
            status.HTTP_200_OK: serializers.ProfileSerializer,
            status.HTTP_400_BAD_REQUEST: swg.OpenApiResponse(
                description=(
                    'Ошибка валидации данных '
                    'или указанное имя уже установлено.'
                )
            ),
            status.HTTP_401_UNAUTHORIZED: swg.OpenApiResponse(
                description='Пользователь не авторизован.'
            ),
        },
    )
    @swg.extend_schema(
        methods=['DELETE'],
        summary='Удалить свой профиль',
        description=(
            'Удаляет профиль текущего пользователя. Удаление невозможно, '
            'если у пользователя есть заказы в статусе ожидания.'
        ),
        request=None,
        responses={
            status.HTTP_204_NO_CONTENT: None,
            status.HTTP_400_BAD_REQUEST: swg.OpenApiResponse(
                description=(
                    'Удаление невозможно из-за наличия ожидающих заказов.'
                )
            ),
            status.HTTP_401_UNAUTHORIZED: swg.OpenApiResponse(
                description='Пользователь не авторизован.'
            ),
        },
    )
    @action(detail=False, methods=['get', 'patch', 'delete'])
    def me(self, request):
        """
        Возвращает профиль пользователя.

        Обновить можно только имя (для смены почты
        и пароля есть другие эндпоинты).

        Удалить профиль при наличии заказов
        в статусе ожидания нельзя.
        """
        user = request.user

        if request.method == 'DELETE':
            ProfileValidator.can_user_delete_himself(user)

            user.delete()

            logger.info(
                'Пользователь с id %s удалил свой профиль',
                user.id
            )
            return Response(status=status.HTTP_204_NO_CONTENT)

        elif request.method == 'PATCH':
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            first_name = serializer.validated_data['first_name']
            if user.first_name == first_name:
                raise ValidationError(
                    f'В профиле уже выставлено имя \'{first_name}\'.'
                )

            user.first_name = serializer.validated_data['first_name']
            user.save(update_fields=['first_name'])

            logger.info(
                'Пользователь с id %s изменил имя',
                user.id
            )

        serializer = self.get_serializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swg.extend_schema(
        summary='Пополнить баланс',
        description=(
            'Пополняет баланс текущего пользователя на указанную сумму '
            'и возвращает обновленный профиль.'
        ),
        request=serializers.BalanceSerializer,
        responses={
            status.HTTP_200_OK: serializers.ProfileSerializer,
            status.HTTP_400_BAD_REQUEST: swg.OpenApiResponse(
                description='Ошибка валидации суммы пополнения.'
            ),
            status.HTTP_401_UNAUTHORIZED: swg.OpenApiResponse(
                description='Пользователь не авторизован.'
            ),
        },
    )
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

        logger.info(
            'Пользователь с id %s пополнил баланс на %s рублей',
            user.id,
            add_money,
        )

        serializer = self.get_serializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)


@swg.extend_schema(tags=['Товары'])
@swg.extend_schema_view(
    list=swg.extend_schema(
        summary='Получить список товаров',
        description=(
            'Возвращает список товаров. По умолчанию возвращаются только '
            'неудаленные товары, отсортированные по цене от меньшей '
            'к большей. Доступна сортировка по цене и количеству товара '
            'на складе. Администратор дополнительно может фильтровать товары '
            'по статусу удаления: получить только удаленные товары '
            'или все товары.'
        ),
        parameters=[
            swg.OpenApiParameter(
                name='ordering',
                description='Сортировка товаров',
                required=False,
                type=str,
                enum=[
                    'price',
                    '-price',
                    'warehouse_quantity',
                    '-warehouse_quantity',
                ],
            ),
            swg.OpenApiParameter(
                name='is_deleted',
                description=(
                    'Фильтрация по статусу удаления. Значение \'true\' '
                    'возвращает только удаленные товары, '
                    '\'all\' — все товары. '
                    'Без параметра возвращаются только неудаленные товары. '
                    'Доступно только администратору.'
                ),
                required=False,
                type=str,
                enum=['true', 'all'],
            ),
        ],
        responses={
            status.HTTP_200_OK: serializers.ProductListSerializer(many=True),
            status.HTTP_403_FORBIDDEN: swg.OpenApiResponse(
                description='Доступно только администратору.'
            ),
        },
    ),
    retrieve=swg.extend_schema(
        summary='Получить товар',
        description='Возвращает подробную информацию о товаре.',
        responses={
            status.HTTP_200_OK: serializers.ProductDetailSerializer,
            status.HTTP_404_NOT_FOUND: swg.OpenApiResponse(
                description='Товар не найден.'
            ),
        },
    ),
    create=swg.extend_schema(
        summary='Создать товар',
        description='Создает новый товар. Доступно только администратору.',
        request=serializers.ProductAdminSerializer,
        responses={
            status.HTTP_201_CREATED: serializers.ProductAdminSerializer,
            status.HTTP_400_BAD_REQUEST: swg.OpenApiResponse(
                description='Ошибка валидации данных.'
            ),
            status.HTTP_403_FORBIDDEN: swg.OpenApiResponse(
                description='Доступно только администратору.'
            ),
        },
    ),
    partial_update=swg.extend_schema(
        summary='Изменить товар',
        description='Изменяет данные товара. Доступно только администратору.',
        request=serializers.ProductAdminSerializer,
        responses={
            status.HTTP_200_OK: serializers.ProductAdminSerializer,
            status.HTTP_400_BAD_REQUEST: swg.OpenApiResponse(
                description='Ошибка валидации данных.'
            ),
            status.HTTP_403_FORBIDDEN: swg.OpenApiResponse(
                description='Доступно только администратору.'
            ),
            status.HTTP_404_NOT_FOUND: swg.OpenApiResponse(
                description='Товар не найден.'
            ),
        },
    ),
    destroy=swg.extend_schema(
        summary='Удалить товар',
        description=(
            'Выполняет soft-delete товара. Товар не удаляется из базы '
            'данных, а помечается как удаленный. '
            'Доступно только администратору.'
        ),
        responses={
            status.HTTP_204_NO_CONTENT: None,
            status.HTTP_400_BAD_REQUEST: swg.OpenApiResponse(
                description='Товар уже удален.'
            ),
            status.HTTP_403_FORBIDDEN: swg.OpenApiResponse(
                description='Доступно только администратору.'
            ),
            status.HTTP_404_NOT_FOUND: swg.OpenApiResponse(
                description='Товар не найден.'
            ),
        },
    ),
)
class ProductViewSet(HttpLookupMixin, ModelViewSet):
    """
    Управление товарами магазина.

    Пользователь может просматривать товары и добавлять их в корзину.
    Администратор — создавать, изменять, удалять и восстанавливать товары.
    """
    model = Product
    filter_backends = [OrderingFilter]
    ordering_fields = ['price', 'warehouse_quantity']
    ordering = ['price']

    def get_permissions(self):
        """Обычному пользователю доступны только безопасные методы."""
        if self.request.method == 'GET' or self.action == 'add_to_cart':
            return [perm.IsAuthenticatedOrReadOnly()]

        return [IsAdmin()]

    def get_queryset(self):
        """Только администратору доступен фильтр статуса удаления."""
        user = self.request.user

        if user.is_authenticated and user.is_superuser:
            param = self.request.query_params.get('is_deleted')

            if param is not None and param == 'true':
                return Product.objects.filter(is_deleted=True)

            elif param is not None and param == 'all':
                return Product.objects.all()

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

        logger.info(
            'Администратор с id %s удалил товар с id %s',
            request.user.id,
            product.id
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @swg.extend_schema(
        summary='Восстановить товар',
        description=(
            'Восстанавливает ранее удаленный товар. После восстановления '
            'товар снова становится доступен в магазине. Доступно только '
            'администратору.'
        ),
        responses={
            status.HTTP_200_OK: serializers.ProductAdminSerializer,
            status.HTTP_400_BAD_REQUEST: swg.OpenApiResponse(
                description='Товар не удален.'
            ),
            status.HTTP_403_FORBIDDEN: swg.OpenApiResponse(
                description='Доступно только администратору.'
            ),
            status.HTTP_404_NOT_FOUND: swg.OpenApiResponse(
                description='Товар не найден.'
            ),
        },
    )
    @action(methods=['post'], detail=True)
    def restore(self, request, public_id=None):
        """Восстановить удаленный товар."""
        product = get_object_or_404(Product, public_id=public_id)

        if product.is_deleted is False:
            raise ValidationError(f'Товар {public_id} не удален.')

        product.is_deleted = False
        product.deleted_at = None
        product.save(update_fields=["is_deleted", "deleted_at"])

        logger.info(
            'Администратор с id %s восстановил товар с id %s',
            request.user.id,
            product.id
        )

        serializer = self.get_serializer(product)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swg.extend_schema(
        summary='Добавить товар в корзину',
        description=(
            'Добавляет товар в корзину текущего пользователя. Если товар '
            'уже находится в корзине, его количество увеличивается на один. '
            'Нельзя добавить удаленный товар или товар, '
            'отсутствующий на складе.'
        ),
        request=None,
        responses={
            status.HTTP_201_CREATED: serializers.CartSerializer,
            status.HTTP_400_BAD_REQUEST: swg.OpenApiResponse(
                description=(
                    'Товар закончился на складе или был удален из магазина.'
                )
            ),
            status.HTTP_401_UNAUTHORIZED: swg.OpenApiResponse(
                description='Пользователь не авторизован.'
            ),
            status.HTTP_404_NOT_FOUND: swg.OpenApiResponse(
                description='Корзина или товар не найдены.'
            ),
        },
    )
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
    """Отображает и очищает содержимое корзины пользователя."""

    @swg.extend_schema(
        tags=['Корзина'],
        summary='Получить содержимое корзины',
        description=(
            'Возвращает содержимое корзины текущего '
            'авторизованного пользователя.'
        ),
        responses={
            status.HTTP_200_OK: serializers.CartSerializer,
            status.HTTP_404_NOT_FOUND: swg.OpenApiResponse(
                description='Корзина не найдена.',
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        """Возвращает содержимое корзины."""
        cart = CartOrderService.get_cart(self.request.user)

        serializer = serializers.CartSerializer(cart)
        return Response(serializer.data)

    @swg.extend_schema(
        tags=['Корзина'],
        summary='Очистить корзину',
        description=(
            'Удаляет все товары из корзины текущего '
            'авторизованного пользователя.'
        ),
        responses={
            status.HTTP_204_NO_CONTENT: None,
            status.HTTP_404_NOT_FOUND: swg.OpenApiResponse(
                description='Корзина не найдена.',
            ),
        },
    )
    def delete(self, request):
        """Очистка корзины."""
        cart = get_object_or_404(Cart, user=request.user)
        cart.items.all().delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class CartItemView(APIView):
    """Управляет позициями в корзине пользователя."""

    @swg.extend_schema(
        tags=['Корзина'],
        summary='Изменить количество товара в корзине',
        description=(
            'Изменяет количество указанного товара в корзине текущего '
            'пользователя. Количество не может превышать доступное '
            'количество товара на складе.'
        ),
        request=serializers.PatchCartItemSerializer,
        responses={
            status.HTTP_200_OK: serializers.CartSerializer,
            status.HTTP_400_BAD_REQUEST: swg.OpenApiResponse(
                description=(
                    'Ошибка валидации. Возможные причины: указанное '
                    'количество уже установлено в корзине; указанное '
                    'количество превышает остаток товара на складе.'
                ),
            ),
            status.HTTP_404_NOT_FOUND: swg.OpenApiResponse(
                description='Товар или позиция товара в корзине не найдены.',
            ),
        },
    )
    def patch(self, request, product_public_id=None):
        """Меняет количество позиций товара в корзине."""
        cart, product, item = CartOrderService.get_cart_item(
            request.user, product_public_id
        )

        serializer = serializers.PatchCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_item_quantity = serializer.validated_data['item_quantity']
        if item.item_quantity == new_item_quantity:
            raise ValidationError(
                f'В корзине уже находится {item.item_quantity} '
                f'позиции товара \'{product_public_id}\''
            )

        elif product.warehouse_quantity < new_item_quantity:
            raise ValidationError(
                f'Количество товара \'{product_public_id}\' '
                f'на складе: {product.warehouse_quantity}.'
            )

        item.item_quantity = new_item_quantity
        item.save(update_fields=['item_quantity'])

        serializer = serializers.CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swg.extend_schema(
        tags=['Корзина'],
        summary='Удалить товар из корзины',
        description=(
            'Удаляет все позиции указанного товара из корзины текущего '
            'пользователя и возвращает обновленное содержимое корзины.'
        ),
        responses={
            status.HTTP_200_OK: serializers.CartSerializer,
            status.HTTP_404_NOT_FOUND: swg.OpenApiResponse(
                description='Товар или позиция товара в корзине не найдены.',
            ),
        },
    )
    def delete(self, request, product_public_id=None):
        """Удаляет все позиции товара из корзины."""
        cart, _, item = CartOrderService.get_cart_item(
            request.user, product_public_id
        )
        item.delete()

        serializer = serializers.CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)


@swg.extend_schema_view(
    list=swg.extend_schema(
        tags=['Заказы'],
        summary='Получить список заказов',
        description=(
            'Возвращает список заказов. Обычному пользователю доступны '
            'только его заказы, администратору — все заказы. По умолчанию '
            'возвращаются заказы со статусом pending, отсортированные '
            'от новых к старым. Доступна фильтрация по статусу и сортировка '
            'по дате создания и общей стоимости заказа.'
        ),
        parameters=[
            swg.OpenApiParameter(
                name='status',
                description=(
                    'Фильтрация заказов по статусу. По умолчанию '
                    '\'pending\'. Значение \'all\' отключает фильтрацию '
                    'по статусу.'
                ),
                required=False,
                type=str,
                enum=[*Status.values, 'all'],
            ),
            swg.OpenApiParameter(
                name='ordering',
                description='Сортировка заказов',
                required=False,
                type=str,
                enum=[
                    'created_at',
                    '-created_at',
                    'total_price',
                    '-total_price',
                ],
            ),
        ],
        responses={
            status.HTTP_200_OK: serializers.OrderAdminListSerializer,
        },
    ),
    retrieve=swg.extend_schema(
        tags=['Заказы'],
        summary='Получить заказ',
        description=(
            'Возвращает подробную информацию о заказе. Обычный пользователь '
            'может получить только свой заказ. Администратор может получить '
            'любой заказ.'
        ),
        responses={
            status.HTTP_200_OK: serializers.OrderSerializer,
            status.HTTP_404_NOT_FOUND: swg.OpenApiResponse(
                description='Заказ не найден.',
            ),
        },
    ),
    create=swg.extend_schema(
        tags=['Заказы'],
        summary='Создать заказ',
        description=(
            'Создает заказ на основе содержимого корзины текущего '
            'пользователя. Перед созданием проверяется, что корзина '
            'не пуста, товары не удалены и доступны в необходимом '
            'количестве на складе, а также что на балансе пользователя '
            'достаточно средств. После создания заказа товары удаляются '
            'из корзины, остатки на складе уменьшаются, а стоимость заказа '
            'списывается с баланса пользователя.'
        ),
        request=serializers.CreateOrderSerializer,
        responses={
            status.HTTP_201_CREATED: serializers.OrderSerializer,
            status.HTTP_400_BAD_REQUEST: swg.OpenApiResponse(
                description=(
                    'Ошибка создания заказа. Возможные причины: '
                    'некорректный или пустой адрес; корзина пуста; '
                    'товар удален из магазина; на складе недостаточно '
                    'товара; на балансе недостаточно средств.'
                ),
            ),
        },
    ),
    partial_update=swg.extend_schema(
        tags=['Заказы'],
        summary='Изменить статус заказа',
        description=(
            'Изменяет данные заказа. Доступно только администратору. '
            'Для изменения статуса необходимо передать новое значение, '
            'отличное от текущего.'
        ),
        request=serializers.OrderSerializer,
        responses={
            status.HTTP_200_OK: serializers.OrderSerializer,
            status.HTTP_400_BAD_REQUEST: swg.OpenApiResponse(
                description=(
                    'Передан недопустимый статус или указанный статус '
                    'уже установлен у заказа.'
                ),
            ),
            status.HTTP_403_FORBIDDEN: swg.OpenApiResponse(
                description='Изменение заказа доступно только администратору.',
            ),
            status.HTTP_404_NOT_FOUND: swg.OpenApiResponse(
                description='Заказ не найден.',
            ),
        },
    ),
)
class OrderViewSet(
    HttpLookupMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
):
    filter_backends = [OrderingFilter]
    ordering_fields = ['created_at', 'total_price']
    ordering = ['-created_at']

    def get_permissions(self):
        """Изменение заказов доступно только администратору."""
        if self.action == 'partial_update':
            return [IsAdmin()]

        return [perm.IsAuthenticated()]

    def get_queryset(self):
        """
        Обычному пользователю доступны только его заказы.

        Администратору доступны все заказы.
        При просмотре списка заказов отображается их количество.

        По умолчанию отображаются активые заказы.
        Доступна фильтрация по статусу.
        """
        user = self.request.user
        param = self.request.query_params.get('status', Status.PENDING)

        if user.is_authenticated and user.is_superuser:
            queryset = Order.objects.annotate(total_products=Count('items'))
        else:
            queryset = Order.objects.filter(user=user)

        if param in Status.values:
            queryset = queryset.filter(status=param)
        elif param != 'all':
            queryset = queryset.filter(status=Status.PENDING)

        return queryset.prefetch_related(
            Prefetch(
                'items',
                queryset=OrderItem.objects.select_related('product')
            )
        )

    def get_serializer_class(self):
        """Обычному пользователю доступен просмотр только своих заказов."""
        user = self.request.user

        if (
            (user.is_authenticated and user.is_superuser)
            and self.action == 'list'
        ):
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

        logger.info(
            'Пользователь с id %s создал заказ с public_id %s',
            user.id,
            order.public_id,
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)
