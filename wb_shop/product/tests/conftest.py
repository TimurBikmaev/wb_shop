import pytest

from product.constants import Status
from product.models import Cart, CartItem, Order, OrderItem, Product
from product.tests.constants import (
    TestCartConstants as TCartCon,
    TestProductConstants as TProductCon,
)


@pytest.fixture
def product(db):
    return Product.objects.create(
        name='Тестовый товар',
        description='Описание тестового товара',
        price='100.00',
        warehouse_quantity=TProductCon.WAREHOUSE_QUANTITY_TEN,
    )


@pytest.fixture
def cart(db, user):
    return Cart.objects.create(user=user)


@pytest.fixture
def cart_item(db, cart, product):
    return CartItem.objects.create(
        cart=cart,
        product=product,
        item_quantity=TCartCon.CART_ITEM_ONE,
    )


@pytest.fixture
def order(db, user):
    return Order.objects.create(
        user=user,
        total_price='200.00',
        address='Тестовый адрес',
        status=Status.PENDING,
    )


@pytest.fixture
def second_order(db, user):
    return Order.objects.create(
        user=user,
        total_price='100.00',
        address='Второй адрес',
        status=Status.PENDING,
    )


@pytest.fixture
def inactive_user_order(db, inactive_user):
    return Order.objects.create(
        user=inactive_user,
        total_price='100.00',
        address='Чужой адрес',
        status=Status.PENDING,
    )


@pytest.fixture
def order_item(db, order, product):
    return OrderItem.objects.create(
        order=order,
        product=product,
        public_id=product.public_id,
        name=product.name,
        item_quantity=TCartCon.CART_ITEM_TWO,
        item_price=product.price,
        item_total='200.00',
    )
