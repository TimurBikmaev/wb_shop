import pytest
from django.urls import reverse
from rest_framework import status

from product.models import CartItem
from product.tests.constants import TestCartConstants as TCartCon


def test_user_can_get_cart(api_client, user, cart, product, cart_item):
    """Проверяет получение корзины авторизованным пользователем."""
    api_client.force_authenticate(user=user)

    response = api_client.get(
        reverse('cart'),
    )

    assert response.status_code == status.HTTP_200_OK


def test_user_can_clear_cart(api_client, user, cart, product, cart_item):
    """Проверяет полную очистку корзины."""
    api_client.force_authenticate(user=user)

    response = api_client.delete(
        reverse('cart'),
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not CartItem.objects.filter(cart=cart).exists(), (
        'Корзина не очищена'
    )


def test_user_can_change_cart_item_quantity(
    api_client,
    user,
    cart,
    product,
    cart_item,
):
    """Проверяет изменение количества товара в корзине."""
    api_client.force_authenticate(user=user)

    response = api_client.patch(
        reverse(
            'cart_item',
            kwargs={'product_public_id': product.public_id},
        ),
        {'item_quantity': TCartCon.CART_ITEM_THREE},
    )

    assert response.status_code == status.HTTP_200_OK

    cart_item.refresh_from_db()
    assert cart_item.item_quantity == TCartCon.CART_ITEM_THREE, (
        'Количество товара не изменилось'
    )


def test_user_cannot_set_same_cart_item_quantity(
    api_client,
    user,
    product,
    cart_item,
):
    """Проверяет запрет установки уже установленного количества."""
    api_client.force_authenticate(user=user)

    response = api_client.patch(
        reverse(
            'cart_item',
            kwargs={'product_public_id': product.public_id},
        ),
        {'item_quantity': TCartCon.CART_ITEM_ONE},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_user_cannot_set_quantity_above_warehouse(
    api_client,
    user,
    product,
    cart_item,
):
    """Проверяет запрет количества товара выше складского остатка."""
    api_client.force_authenticate(user=user)

    response = api_client.patch(
        reverse(
            'cart_item',
            kwargs={'product_public_id': product.public_id},
        ),
        {'item_quantity': TCartCon.CART_ITEM_ELEVEN},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST

    cart_item.refresh_from_db()
    assert cart_item.item_quantity == TCartCon.CART_ITEM_ONE, (
        'Количество товара изменилось'
    )


def test_user_cannot_change_quantity_of_missing_cart_item(
    api_client,
    user,
    cart,
    product,
):
    """Проверяет ошибку при изменении отсутствующего товара в корзине."""
    api_client.force_authenticate(user=user)

    response = api_client.patch(
        reverse(
            'cart_item',
            kwargs={'product_public_id': product.public_id},
        ),
        {'item_quantity': TCartCon.CART_ITEM_THREE},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_user_can_delete_cart_item(
    api_client,
    user,
    product,
    cart_item,
):
    """Проверяет удаление товара из корзины."""
    api_client.force_authenticate(user=user)

    response = api_client.delete(
        reverse(
            'cart_item',
            kwargs={'product_public_id': product.public_id},
        ),
    )

    assert response.status_code == status.HTTP_200_OK
    assert not CartItem.objects.filter(pk=cart_item.pk).exists(), (
        'Товар не удален из корзины'
    )


def test_user_cannot_delete_missing_cart_item(
    api_client,
    user,
    cart,
    product,
):
    """Проверяет ошибку при удалении отсутствующего товара."""
    api_client.force_authenticate(user=user)

    response = api_client.delete(
        reverse(
            'cart_item',
            kwargs={'product_public_id': product.public_id},
        ),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.parametrize(
    'quantity',
    [TCartCon.CART_NO_ITEM, TCartCon.CART_INVALID_COUNT_ITEM],
)
def test_user_cannot_set_invalid_cart_item_quantity(
    api_client,
    user,
    product,
    cart_item,
    quantity,
):
    """Проверяет валидацию недопустимого количества товара."""
    api_client.force_authenticate(user=user)

    response = api_client.patch(
        reverse(
            'cart_item',
            kwargs={'product_public_id': product.public_id},
        ),
        {'item_quantity': quantity},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST

    cart_item.refresh_from_db()
    assert cart_item.item_quantity == TCartCon.CART_ITEM_ONE, (
        'Количество товара изменилось'
    )
