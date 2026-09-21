from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from product.models import CartItem, Product
from product.tests.constants import TestProductConstants as TProductCon


User = get_user_model()


@pytest.mark.parametrize(
    'method',
    ['post', 'patch', 'delete'],
)
def test_product_write_methods_available_only_for_admin(
    api_client,
    user,
    product,
    method,
):
    """Обычный пользователь не может создавать, изменять и удалять товары."""
    api_client.force_authenticate(user=user)

    data = {
        'name': 'Новый товар',
        'description': 'Новое описание',
        'price': '200.00',
        'warehouse_quantity': TProductCon.WAREHOUSE_QUANTITY_TEN,
    }

    if method == 'post':
        url = reverse('products-list')
        response = api_client.post(url, data, format='json')

    elif method == 'patch':
        url = reverse(
            'products-detail',
            kwargs={'public_id': product.public_id},
        )
        response = api_client.patch(url, data, format='json')

    else:
        url = reverse(
            'products-detail',
            kwargs={'public_id': product.public_id},
        )
        response = api_client.delete(url)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_product_list_available_without_authentication(api_client, product):
    """Неавторизованный пользователь может просматривать каталог."""
    url = reverse('products-list')

    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert (
        response.data['results'][TProductCon.FIRST_PRODUCT_IDX]['public_id']
        == str(product.public_id)
    )


def test_product_detail_available_without_authentication(api_client, product):
    """Неавторизованный пользователь может просматривать товар."""
    url = reverse(
        'products-detail',
        kwargs={'public_id': product.public_id},
    )

    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data['public_id'] == str(product.public_id)
    assert response.data['description'] == product.description


def test_product_list_hides_deleted_products(api_client, product):
    """Обычный каталог не содержит удалённые товары."""
    product.is_deleted = True
    product.deleted_at = timezone.now()
    product.save(update_fields=['is_deleted', 'deleted_at'])

    url = reverse('products-list')
    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert not response.data['results'], 'Удаленный товар попал в каталог'


@pytest.mark.parametrize(
    'query, expected_count',
    [
        ('true', TProductCon.PRODUCT_ONE),
        ('all', TProductCon.PRODUCT_TWO),
    ],
)
def test_admin_product_deleted_filter(
    api_client,
    admin_user,
    product,
    query,
    expected_count,
):
    """
    Администратор может фильтровать удалённые товары и смотреть все товары.
    """
    deleted_product = Product.objects.create(
        name='Удаленный товар',
        description='Описание',
        price=Decimal('150.00'),
        warehouse_quantity=TProductCon.WAREHOUSE_QUANTITY_TEN,
        is_deleted=True,
        deleted_at=timezone.now(),
    )

    api_client.force_authenticate(user=admin_user)

    url = reverse('products-list')

    response = api_client.get(
        url,
        {'is_deleted': query},
    )

    results = response.data['results']

    assert response.status_code == status.HTTP_200_OK
    assert len(results) == expected_count, (
        f'Фильтр {query} вернул лишние объекты.'
    )

    if query == 'true':
        assert (
            results[TProductCon.FIRST_PRODUCT_IDX]['public_id']
            == deleted_product.public_id
        ), 'Фильтр вернул не тот товар'


def test_admin_can_create_product(api_client, admin_user):
    """Администратор может создать товар."""
    api_client.force_authenticate(user=admin_user)

    data = {
        'name': 'Новый товар',
        'description': 'Описание нового товара',
        'price': '250.00',
        'warehouse_quantity': TProductCon.WAREHOUSE_QUANTITY_TEN,
    }

    url = reverse('products-list')
    response = api_client.post(url, data, format='json')

    assert response.status_code == status.HTTP_201_CREATED

    product = Product.objects.get(name=data['name'])

    assert product.description == data['description'], (
        'Описание не сохранилось'
    )
    assert product.price == Decimal(data['price']), 'Цена не сохранилась'
    assert product.warehouse_quantity == data['warehouse_quantity'], (
        'Количество не сохранилось'
    )


def test_admin_can_update_product(api_client, admin_user, product):
    """Администратор может изменить данные товара."""
    api_client.force_authenticate(user=admin_user)

    data = {
        'name': 'Измененный товар',
        'description': 'Новое описание',
        'price': '300.00',
        'warehouse_quantity': TProductCon.WAREHOUSE_QUANTITY_TWENTY,
    }

    url = reverse(
        'products-detail',
        kwargs={'public_id': product.public_id},
    )

    response = api_client.patch(url, data, format='json')

    assert response.status_code == status.HTTP_200_OK

    product.refresh_from_db()

    assert product.name == data['name'], 'Название не изменилось'
    assert product.description == data['description'], 'Описание не изменилось'
    assert product.price == Decimal(data['price']), 'Цена не изменилась'
    assert product.warehouse_quantity == data['warehouse_quantity'], (
        'Количество не изменилось'
    )


def test_admin_can_soft_delete_product(api_client, admin_user, product):
    """Удаление товара переводит его в soft-delete."""
    api_client.force_authenticate(user=admin_user)

    before_delete = timezone.now()

    url = reverse(
        'products-detail',
        kwargs={'public_id': product.public_id},
    )

    response = api_client.delete(url)

    assert response.status_code == status.HTTP_204_NO_CONTENT

    product.refresh_from_db()

    assert product.is_deleted is True, 'Товар не помечен удаленным'
    assert product.deleted_at is not None, 'Дата удаления не записалась'
    assert product.deleted_at >= before_delete, 'Некорректная дата удаления'


def test_admin_cannot_delete_already_deleted_product(
    api_client,
    admin_user,
    product,
):
    """Повторное удаление уже удалённого товара запрещено."""
    product.is_deleted = True
    product.deleted_at = timezone.now()
    product.save(update_fields=['is_deleted', 'deleted_at'])

    api_client.force_authenticate(user=admin_user)

    url = reverse(
        'products-detail',
        kwargs={'public_id': product.public_id},
    )

    response = api_client.delete(url)

    assert response.status_code == status.HTTP_400_BAD_REQUEST, (
        'Нельзя удалить уже удаленный товар.'
    )


def test_admin_can_restore_deleted_product(
    api_client,
    admin_user,
    product,
):
    """Администратор может восстановить удалённый товар."""
    product.is_deleted = True
    product.deleted_at = timezone.now()
    product.save(update_fields=['is_deleted', 'deleted_at'])

    api_client.force_authenticate(user=admin_user)

    url = reverse(
        'products-restore',
        kwargs={'public_id': product.public_id},
    )

    response = api_client.post(url)

    assert response.status_code == status.HTTP_200_OK

    product.refresh_from_db()

    assert product.is_deleted is False, 'Товар не восстановлен'
    assert product.deleted_at is None, 'Дата удаления не очищена'


def test_admin_cannot_restore_not_deleted_product(
    api_client, admin_user, product,
):
    """Нельзя восстановить товар, который не был удалён."""
    api_client.force_authenticate(user=admin_user)

    url = reverse(
        'products-restore',
        kwargs={'public_id': product.public_id},
    )

    response = api_client.post(url)

    assert response.status_code == status.HTTP_400_BAD_REQUEST, (
        'Нельзя восстановить неудаленный товар.'
    )


@pytest.mark.parametrize(
    'ordering',
    [
        'price',
        '-price',
        'warehouse_quantity',
        '-warehouse_quantity',
    ],
)
def test_product_ordering(
    api_client,
    product,
    ordering,
):
    """Каталог поддерживает сортировку по цене и остатку."""
    Product.objects.create(
        name='Второй товар',
        description='Описание',
        price=Decimal('200.00'),
        warehouse_quantity=TProductCon.WAREHOUSE_QUANTITY_TWENTY,
    )

    url = reverse('products-list')
    response = api_client.get(url, {'ordering': ordering})

    assert response.status_code == status.HTTP_200_OK

    products = response.data['results']

    assert len(products) == TProductCon.PRODUCT_TWO, (
        'Неверное количество товаров'
    )

    if 'price' in ordering:
        values = [Decimal(item['price']) for item in products]
    else:
        values = [item['warehouse_quantity'] for item in products]

    assert values == sorted(
        values,
        reverse=ordering.startswith('-'),
    ), 'Неверный порядок товаров'


def test_user_can_add_product_to_cart(
    api_client,
    user,
    product,
    cart,
):
    """Авторизованный пользователь может добавить товар в корзину."""
    api_client.force_authenticate(user=user)

    url = reverse(
        'products-add-to-cart',
        kwargs={'public_id': product.public_id},
    )

    response = api_client.post(url)

    assert response.status_code == status.HTTP_201_CREATED

    item = CartItem.objects.get(
        cart=cart,
        product=product,
    )

    assert item.item_quantity == TProductCon.PRODUCT_ONE, (
        'Товар добавлен в неверном количестве'
    )


def test_user_adds_existing_product_to_cart_again(
    api_client,
    user,
    product,
    cart,
):
    """Повторное добавление товара увеличивает его количество."""
    CartItem.objects.create(
        cart=cart,
        product=product,
        item_quantity=1,
    )

    api_client.force_authenticate(user=user)

    url = reverse(
        'products-add-to-cart',
        kwargs={'public_id': product.public_id},
    )

    response = api_client.post(url)

    assert response.status_code == status.HTTP_201_CREATED

    item = CartItem.objects.get(
        cart=cart,
        product=product,
    )

    assert item.item_quantity == TProductCon.PRODUCT_TWO, (
        'Количество товара не увеличилось'
    )


@pytest.mark.parametrize(
    'is_deleted, warehouse_quantity',
    [
        (True, 10),
        (False, 0),
    ],
)
def test_user_cannot_add_unavailable_product_to_cart(
    api_client,
    user,
    product,
    cart,
    is_deleted,
    warehouse_quantity,
):
    """Нельзя добавить удалённый или отсутствующий на складе товар."""
    product.is_deleted = is_deleted
    product.warehouse_quantity = warehouse_quantity
    product.save(update_fields=['is_deleted', 'warehouse_quantity'])

    api_client.force_authenticate(user=user)

    url = reverse(
        'products-add-to-cart',
        kwargs={'public_id': product.public_id},
    )

    response = api_client.post(url)

    assert response.status_code == status.HTTP_400_BAD_REQUEST, (
        'Нельзя добавить в корзину удаленный '
        'или закончившийся на складе товар.'
    )


def test_unauthenticated_user_cannot_add_product_to_cart(
    api_client,
    product,
):
    """Неавторизованный пользователь не может добавить товар в корзину."""
    url = reverse(
        'products-add-to-cart',
        kwargs={'public_id': product.public_id},
    )

    response = api_client.post(url)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_admin_gets_admin_product_fields(
    api_client,
    admin_user,
    product,
):
    """Администратор получает административные поля товара."""
    api_client.force_authenticate(user=admin_user)

    product.is_deleted = True
    product.deleted_at = timezone.now()
    product.save(update_fields=['is_deleted', 'deleted_at'])

    url = reverse(
        'products-detail',
        kwargs={'public_id': product.public_id},
    )

    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK, (
        'Администратор должен видеть удаленный объект в product/public_id'
    )
    assert 'created_at' in response.data, 'Нет даты создания'
    assert 'updated_at' in response.data, 'Нет даты обновления'
    assert 'deleted_at' in response.data, 'Нет даты удаления'
    assert 'description' in response.data, 'Нет описания'


def test_regular_user_gets_public_product_fields(
    api_client,
    user,
    product,
):
    """Обычный пользователь получает только пользовательские поля."""
    api_client.force_authenticate(user=user)

    url = reverse(
        'products-detail',
        kwargs={'public_id': product.public_id},
    )

    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert 'description' in response.data, 'Нет описания'
    assert 'created_at' not in response.data, 'Доступна дата создания'
    assert 'updated_at' not in response.data, 'Доступна дата обновления'
    assert 'deleted_at' not in response.data, 'Доступна дата удаления'
