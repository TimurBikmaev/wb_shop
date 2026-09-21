import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

from user.tests.constants import TestUserConstants as TUserCon


User = get_user_model()


def test_user_me_correct(api_client, user):
    """Проверяет получение собственного профиля."""
    api_client.force_authenticate(user=user)

    response = api_client.get(reverse('users-me'))

    assert response.status_code == status.HTTP_200_OK, (
        'Получение собственного профиля должно завершаться статусом 200.'
    )
    assert response.data['public_id'] == str(user.public_id), (
        'В ответе должен возвращаться корректный public_id пользователя.'
    )
    assert response.data['email'] == user.email, (
        'В ответе должен возвращаться корректный email пользователя.'
    )
    assert response.data['first_name'] == user.first_name, (
        'В ответе должно возвращаться корректное имя пользователя.'
    )
    assert 'balance' in response.data, (
        'В ответе собственного профиля должно присутствовать поле balance.'
    )


@pytest.mark.parametrize(
    'method',
    ['get', 'patch', 'delete'],
)
def test_user_me_requires_authentication(api_client, method):
    """Проверяет запрет работы с собственным профилем без авторизации."""
    response = getattr(api_client, method)(
        reverse('users-me'),
        {'first_name': 'NewName'} if method == 'patch' else {},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED, (
        'Неавторизованный пользователь не должен '
        'иметь доступ к собственному профилю.'
    )


def test_user_me_patch_correct(api_client, user):
    """Проверяет изменение имени в собственном профиле."""
    api_client.force_authenticate(user=user)

    response = api_client.patch(
        reverse('users-me'),
        {'first_name': 'NewName'},
    )

    assert response.status_code == status.HTTP_200_OK, (
        'Изменение имени в собственном профиле '
        'должно завершаться статусом 200.'
    )

    user.refresh_from_db()

    assert user.first_name == 'NewName', (
        'После изменения профиля имя пользователя '
        'должно быть сохранено в базе.'
    )


@pytest.mark.parametrize(
    'data',
    [
        {},
        {'first_name': ''},
        {'first_name': 'A'},
    ],
)
def test_user_me_patch_invalid_data(api_client, user, data):
    """Проверяет отказ изменения профиля с некорректными данными."""
    api_client.force_authenticate(user=user)

    old_name = user.first_name

    response = api_client.patch(
        reverse('users-me'),
        data,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST, (
        'Некорректные данные профиля должны отклоняться со статусом 400.'
    )

    user.refresh_from_db()

    assert user.first_name == old_name, (
        'При некорректных данных имя пользователя не должно изменяться.'
    )


def test_user_me_patch_same_name(api_client, user):
    """Проверяет запрет сохранения уже установленного имени."""
    api_client.force_authenticate(user=user)

    response = api_client.patch(
        reverse('users-me'),
        {'first_name': user.first_name},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST, (
        'Изменение имени на уже установленное должно '
        'отклоняться со статусом 400.'
    )


def test_user_me_delete_correct(api_client, user):
    """Проверяет удаление собственного профиля."""
    api_client.force_authenticate(user=user)
    user_id = user.id

    response = api_client.delete(reverse('users-me'))

    assert response.status_code == status.HTTP_204_NO_CONTENT, (
        'Удаление собственного профиля должно завершаться статусом 204.'
    )
    assert not User.objects.filter(id=user_id).exists(), (
        'После удаления профиль пользователя не должен существовать в базе.'
    )


def test_users_list_admin_correct(
        api_client, admin_user, user, inactive_user, db
):
    """Проверяет просмотр списка пользователей администратором."""
    api_client.force_authenticate(user=admin_user)

    response = api_client.get(reverse('users-list'))

    assert response.status_code == status.HTTP_200_OK, (
        'Получение списка пользователей администратором '
        'должно завершаться статусом 200.'
    )
    assert len(response.data['results']) == TUserCon.USER_THREE, (
        'Администратор должен видеть всех пользователей.'
    )

    for item in response.data['results']:
        assert 'public_id' in item, (
            'Каждый пользователь в списке должен содержать поле public_id.'
        )
        assert 'email' in item, (
            'Каждый пользователь в списке должен содержать поле email.'
        )
        assert 'first_name' in item, (
            'Каждый пользователь в списке должен содержать поле first_name.'
        )
        assert 'is_active' in item, (
            'Каждый пользователь в списке должен содержать поле is_active.'
        )
        assert 'total_orders' in item, (
            'Каждый пользователь в списке должен содержать поле total_orders.'
        )
        assert 'total_purchases' in item, (
            'Каждый пользователь в списке должен '
            'содержать поле total_purchases.'
        )


@pytest.mark.parametrize(
    'user_fixture',
    ['user', 'inactive_user'],
)
def test_users_admin_access(
    api_client,
    request,
    user_fixture,
):
    """Проверяет запрет просмотра пользователей обычным пользователем."""
    current_user = request.getfixturevalue(user_fixture)
    api_client.force_authenticate(user=current_user)

    response = api_client.get(reverse('users-list'))

    assert response.status_code == status.HTTP_403_FORBIDDEN, (
        'Обычный пользователь не должен иметь доступ к списку пользователей.'
    )


def test_user_retrieve_admin_correct(api_client, admin_user, user, db):
    """Проверяет просмотр подробного профиля пользователя администратором."""
    api_client.force_authenticate(user=admin_user)

    response = api_client.get(
        reverse(
            'users-detail',
            kwargs={'public_id': user.public_id},
        ),
    )

    assert response.status_code == status.HTTP_200_OK, (
        'Получение профиля пользователя администратором '
        'должно завершаться статусом 200.'
    )
    assert response.data['public_id'] == str(user.public_id), (
        'В профиле должен возвращаться корректный public_id пользователя.'
    )
    assert response.data['email'] == user.email, (
        'В профиле должен возвращаться корректный email пользователя.'
    )
    assert response.data['first_name'] == user.first_name, (
        'В профиле должно возвращаться корректное имя пользователя.'
    )
    assert 'balance' in response.data, (
        'В подробном профиле должно присутствовать поле balance.'
    )
    assert 'total_orders' in response.data, (
        'В подробном профиле должно присутствовать поле total_orders.'
    )
    assert 'total_purchases' in response.data, (
        'В подробном профиле должно присутствовать поле total_purchases.'
    )
    assert 'orders' in response.data, (
        'В подробном профиле должно присутствовать поле orders.'
    )


def test_user_patch_by_admin_correct(api_client, admin_user, user, db):
    """Проверяет изменение пользователя администратором."""
    api_client.force_authenticate(user=admin_user)

    response = api_client.patch(
        reverse(
            'users-detail',
            kwargs={'public_id': user.public_id},
        ),
        {'is_active': False},
    )

    assert response.status_code == status.HTTP_200_OK, (
        'Изменение пользователя администратором должно '
        'завершаться статусом 200.'
    )

    user.refresh_from_db()

    assert user.is_active is False, (
        'После изменения администратором пользователь должен стать неактивным.'
    )


def test_user_patch_by_admin_read_only_fields(api_client, admin_user, user, db):
    """Проверяет, что администратор не может изменить защищенные поля."""
    api_client.force_authenticate(user=admin_user)

    old_email = user.email
    old_name = user.first_name
    old_balance = user.balance

    response = api_client.patch(
        reverse(
            'users-detail',
            kwargs={'public_id': user.public_id},
        ),
        {
            'email': 'new@example.com',
            'first_name': 'NewName',
            'balance': TUserCon.BALANCE_THOUSAND,
        },
    )

    assert response.status_code == status.HTTP_200_OK, (
        'Изменение пользователя администратором должно '
        'завершаться статусом 200.'
    )

    user.refresh_from_db()

    assert user.email == old_email, (
        'Администратор не должен иметь возможность '
        'изменить email пользователя.'
    )
    assert user.first_name == old_name, (
        'Администратор не должен иметь возможность изменить имя пользователя.'
    )
    assert user.balance == old_balance, (
        'Администратор не должен иметь возможность '
        'зменить баланс пользователя.'
    )


def test_user_admin_cannot_patch_himself(api_client, admin_user, db):
    """Проверяет запрет изменения объекта администратора через users/{id}."""
    api_client.force_authenticate(user=admin_user)

    response = api_client.patch(
        reverse(
            'users-detail',
            kwargs={'public_id': admin_user.public_id},
        ),
        {'is_active': False},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST, (
        'Администратор не должен иметь возможность'
        'изменить собственный профиль через endpoint users/{id}.'
    )

    admin_user.refresh_from_db()

    assert admin_user.is_active is True, (
        'При попытке изменения собственного профиля '
        'администратор должен остаться активным.'
    )


def test_user_add_balance_correct(api_client, user):
    """Проверяет успешное пополнение баланса."""
    api_client.force_authenticate(user=user)

    old_balance = user.balance

    response = api_client.post(
        reverse('users-add-balance'),
        {
            'add_money': '1000.00',
            'card_number': '12345',
            'cvc': '123',
        },
    )

    assert response.status_code == status.HTTP_200_OK, (
        'Успешное пополнение баланса должно завершаться статусом 200.'
    )

    user.refresh_from_db()

    assert user.balance == old_balance + TUserCon.BALANCE_THOUSAND, (
        'После успешного пополнения баланс должен '
        'увеличиться на указанную сумму.'
    )


@pytest.mark.parametrize(
    'data',
    [
        {
            'add_money': '0',
            'card_number': '12345',
            'cvc': '123',
        },
        {
            'add_money': '100.00',
            'card_number': '1234',
            'cvc': '123',
        },
        {
            'add_money': '100.00',
            'card_number': '12345',
            'cvc': '12',
        },
        {
            'add_money': '100.00',
            'card_number': 'abcde',
            'cvc': '123',
        },
    ],
)
def test_user_add_balance_invalid_data(api_client, user, data):
    """Проверяет отказ пополнения баланса с некорректными данными."""
    api_client.force_authenticate(user=user)

    old_balance = user.balance

    response = api_client.post(
        reverse('users-add-balance'),
        data,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST, (
        'Некорректные данные пополнения баланса '
        'должны отклоняться со статусом 400.'
    )

    user.refresh_from_db()

    assert user.balance == old_balance, (
        'При некорректных данных баланс пользователя не должен изменяться.'
    )
