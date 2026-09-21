from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status

from product.constants import Status
from product.models import CartItem, Order, OrderItem
from product.tests.constants import (
    TestCartConstants as TCartCon,
    TestProductConstants as TProductCon,
)


def test_user_can_create_order(
    api_client,
    user,
    cart,
    product,
    cart_item,
):
    """Проверяет создание заказа из корзины."""
    user.balance = Decimal('500.00')
    user.save(update_fields=['balance'])

    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse('orders-list'),
        {'address': 'Тестовый адрес'},
    )

    assert response.status_code == status.HTTP_201_CREATED

    order = Order.objects.get(user=user)

    assert order.total_price == Decimal('100.00'), (
        'Неверная сумма заказа'
    )
    assert order.address == 'Тестовый адрес', (
        'Неверный адрес заказа'
    )
    assert order.status == Status.PENDING, (
        'Неверный статус заказа'
    )


def test_create_order_saves_product_snapshot(
    api_client,
    user,
    cart,
    product,
    cart_item,
):
    """Проверяет сохранение данных товара в позиции заказа."""
    user.balance = Decimal('500.00')
    user.save(update_fields=['balance'])

    cart_item.item_quantity = TCartCon.CART_ITEM_TWO
    cart_item.save(update_fields=['item_quantity'])

    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse('orders-list'),
        {'address': 'Тестовый адрес'},
    )

    assert response.status_code == status.HTTP_201_CREATED

    order = Order.objects.get(user=user)
    order_item = OrderItem.objects.get(order=order)

    assert order_item.product == product, (
        'Неверный товар в заказе'
    )
    assert order_item.public_id == product.public_id, (
        'Неверный public_id товара'
    )
    assert order_item.name == product.name, (
        'Неверное название товара'
    )
    assert order_item.item_quantity == TCartCon.CART_ITEM_TWO, (
        'Неверное количество товара'
    )
    assert order_item.item_price == Decimal('100.00'), (
        'Неверная цена товара'
    )
    assert order_item.item_total == Decimal('200.00'), (
        'Неверная сумма позиции'
    )
    assert order.total_price == Decimal('200.00'), (
        'Неверная сумма заказа'
    )


def test_create_order_reduces_balance_and_warehouse(
    api_client,
    user,
    cart,
    product,
    cart_item,
):
    """Проверяет списание денег и уменьшение складского остатка."""
    user.balance = Decimal('500.00')
    user.save(update_fields=['balance'])

    cart_item.item_quantity = TCartCon.CART_ITEM_TWO
    cart_item.save(update_fields=['item_quantity'])

    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse('orders-list'),
        {'address': 'Тестовый адрес'},
    )

    assert response.status_code == status.HTTP_201_CREATED

    user.refresh_from_db()
    product.refresh_from_db()

    assert user.balance == Decimal('300.00'), 'Баланс не уменьшился'

    assert product.warehouse_quantity == (
        TProductCon.WAREHOUSE_QUANTITY_TEN - TCartCon.CART_ITEM_TWO
    ), 'Остаток склада не уменьшился'


def test_create_order_clears_cart(
    api_client,
    user,
    cart,
    product,
    cart_item,
):
    """Проверяет очистку корзины после создания заказа."""
    user.balance = Decimal('500.00')
    user.save(update_fields=['balance'])

    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse('orders-list'),
        {'address': 'Тестовый адрес'},
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert not CartItem.objects.filter(
        cart=cart,
    ).exists(), 'Корзина не очищена'


def test_unauthenticated_user_cannot_create_order(
    api_client,
):
    """Проверяет запрет создания заказа без авторизации."""
    response = api_client.post(
        reverse('orders-list'),
        {'address': 'Тестовый адрес'},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_user_cannot_create_order_with_empty_cart(
    api_client,
    user,
    cart,
):
    """Проверяет запрет создания заказа с пустой корзиной."""
    user.balance = Decimal('500.00')
    user.save(update_fields=['balance'])

    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse('orders-list'),
        {'address': 'Тестовый адрес'},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert not Order.objects.filter(user=user).exists(), (
        'Заказ создан с пустой корзиной'
    )


def test_user_cannot_create_order_with_insufficient_balance(
    api_client,
    user,
    cart,
    product,
    cart_item,
):
    """Проверяет запрет покупки при недостаточном балансе."""
    user.balance = Decimal('50.00')
    user.save(update_fields=['balance'])

    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse('orders-list'),
        {'address': 'Тестовый адрес'},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert not Order.objects.filter(user=user).exists(), (
        'Заказ создан при недостаточном балансе'
    )


def test_user_cannot_create_order_with_deleted_product(
    api_client,
    user,
    cart,
    product,
    cart_item,
):
    """Проверяет запрет заказа удаленного товара."""
    user.balance = Decimal('500.00')
    user.save(update_fields=['balance'])

    product.is_deleted = True
    product.save(update_fields=['is_deleted'])

    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse('orders-list'),
        {'address': 'Тестовый адрес'},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert not Order.objects.filter(user=user).exists(), (
        'Заказ создан с удаленным товаром'
    )


def test_user_cannot_create_order_with_insufficient_stock(
    api_client,
    user,
    cart,
    product,
    cart_item,
):
    """Проверяет запрет заказа при недостаточном остатке."""
    user.balance = Decimal('500.00')
    user.save(update_fields=['balance'])

    cart_item.item_quantity = TCartCon.CART_ITEM_ELEVEN
    cart_item.save(update_fields=['item_quantity'])

    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse('orders-list'),
        {'address': 'Тестовый адрес'},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert not Order.objects.filter(user=user).exists(), (
        'Заказ создан при недостаточном остатке'
    )


def test_user_can_get_own_order(api_client, user, order, order_item):
    """Проверяет получение пользователем своего заказа."""
    api_client.force_authenticate(user=user)

    response = api_client.get(
        reverse(
            'orders-detail',
            kwargs={'public_id': order.public_id},
        ),
    )

    assert response.status_code == status.HTTP_200_OK


def test_user_cannot_get_another_user_order(
    api_client,
    user,
    inactive_user_order,
):
    """Проверяет изоляцию заказов разных пользователей."""
    api_client.force_authenticate(user=user)

    response = api_client.get(
        reverse(
            'orders-detail',
            kwargs={'public_id': inactive_user_order.public_id},
        ),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_admin_can_get_all_orders(
    api_client,
    admin_user,
    order,
    inactive_user_order,
    order_item,
):
    """Проверяет получение администратором всех заказов."""
    api_client.force_authenticate(user=admin_user)

    response = api_client.get(
        reverse('orders-list'),
        {'status': 'all'},
    )

    assert response.status_code == status.HTTP_200_OK

    order_data = next(
        item
        for item in response.data['results']
        if item['public_id'] == order.public_id
    )

    order_ids = {
        item['public_id']
        for item in response.data['results']
    }

    assert order.public_id in order_ids, (
        'Заказ пользователя отсутствует'
    )
    assert inactive_user_order.public_id in order_ids, (
        'Заказ другого пользователя отсутствует'
    )
    assert order_data['total_products'] == order_item.item_quantity, (
        'Неверное общее количество позиций в заказе'
    )


def test_user_cannot_update_order(api_client, user, order):
    """Проверяет запрет изменения заказа обычным пользователем."""
    api_client.force_authenticate(user=user)

    response = api_client.patch(
        reverse(
            'orders-detail',
            kwargs={'public_id': order.public_id},
        ),
        {'status': Status.COMPLETED},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_admin_can_change_order_status(
    api_client,
    admin_user,
    order,
):
    """Проверяет изменение статуса заказа администратором."""
    api_client.force_authenticate(user=admin_user)

    response = api_client.patch(
        reverse(
            'orders-detail',
            kwargs={'public_id': order.public_id},
        ),
        {'status': Status.COMPLETED},
    )

    assert response.status_code == status.HTTP_200_OK

    order.refresh_from_db()

    assert order.status == Status.COMPLETED, (
        'Статус заказа не изменился'
    )


def test_admin_cannot_set_same_order_status(
    api_client,
    admin_user,
    order,
):
    """Проверяет запрет повторной установки текущего статуса."""
    api_client.force_authenticate(user=admin_user)

    response = api_client.patch(
        reverse(
            'orders-detail',
            kwargs={'public_id': order.public_id},
        ),
        {'status': Status.PENDING},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST

    order.refresh_from_db()

    assert order.status == Status.PENDING, (
        'Статус заказа изменился'
    )


@pytest.mark.parametrize(
    'ordering',
    [
        'created_at',
        '-created_at',
        'total_price',
        '-total_price',
    ],
)
def test_user_can_order_own_orders(
    api_client,
    user,
    order,
    second_order,
    ordering,
):
    """Проверяет доступность сортировки заказов."""
    api_client.force_authenticate(user=user)

    response = api_client.get(
        reverse('orders-list'),
        {
            'status': 'all',
            'ordering': ordering,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data['results']) == TCartCon.CART_ITEM_TWO, (
        'Неверное количество заказов'
    )
