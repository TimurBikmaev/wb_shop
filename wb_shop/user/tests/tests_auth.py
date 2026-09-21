import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

from user.models import VarificationCode
from user.tests.constants import TestAuthConstants as TAuthCon

User = get_user_model()


def test_register_correct(api_client, email_sender, db):
    """Проверяет регистрацию пользователя и отправку кода на email."""
    data = {
        'email': 'test@example.com',
        'first_name': 'Test',
        'password': 'StrongPassword123!',
    }

    response = api_client.post(
        reverse('auth-register'),
        data,
    )

    assert response.status_code == status.HTTP_201_CREATED

    user = User.objects.get(email=data['email'])

    assert user.first_name == data['first_name'], (
        'Имя пользователя сохранено некорректно'
    )
    assert user.is_active is False, (
        'После регистрации пользователь должен быть неактивным'
    )
    assert user.check_password(data['password']), (
        'Пароль сохранен некорректно'
    )

    assert len(email_sender) == TAuthCon.EMAIL_ONE, (
        'После регистрации должно отправляться письмо'
    )

    assert (
        email_sender[TAuthCon.EMAIL_RECIPIENT_IDX]['recipient_list']
        == [data['email']]
    ), 'Письмо должно отправляться на email пользователя'

    assert VarificationCode.objects.filter(user=user).exists(), (
        'После регистрации должен создаваться код подтверждения'
    )


@pytest.mark.parametrize(
    'data',
    [
        {},
        {
            'email': 'invalid',
            'first_name': 'Test',
            'password': 'StrongPassword123!',
        },
        {
            'email': 'test@example.com',
            'first_name': '',
            'password': 'StrongPassword123!',
        },
        {
            'email': 'test@example.com',
            'first_name': 'Test',
            'password': '123',
        },
    ],
)
def test_register_invalid_data(api_client, data, db):
    """Проверяет отказ регистрации с некорректными данными."""
    response = api_client.post(
        reverse('auth-register'),
        data,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST, (
        'Некорректные данные регистрации должны отклоняться'
    )


def test_send_code_correct(api_client, user, email_sender):
    """Проверяет повторную отправку кода пользователю."""
    response = api_client.post(
        reverse('auth-send-code'),
        {'email': user.email},
    )

    assert response.status_code == status.HTTP_201_CREATED, (
        'Отправка кода должна возвращать 201'
    )
    assert len(email_sender) == TAuthCon.EMAIL_ONE, (
        'Должно отправляться одно письмо'
    )
    assert (
        email_sender[TAuthCon.EMAIL_RECIPIENT_IDX]['recipient_list']
        == [user.email]
    ), 'Письмо должно отправляться на email пользователя'


@pytest.mark.parametrize(
    'email, expected_status',
    [
        ('unknown@example.com', status.HTTP_404_NOT_FOUND),
        ('invalid', status.HTTP_400_BAD_REQUEST),
        ('', status.HTTP_400_BAD_REQUEST),
    ],
)
def test_send_code_invalid_email(
    api_client,
    email,
    expected_status,
    db,
):
    """Проверяет отказ отправки кода для некорректного email."""
    response = api_client.post(
        reverse('auth-send-code'),
        {'email': email},
    )

    assert response.status_code == expected_status, (
        'Для некорректного email должен возвращаться ожидаемый статус ошибки'
    )


def test_verify_email_correct(api_client, inactive_user, db):
    """Проверяет активацию пользователя после подтверждения email."""
    VarificationCode.objects.create(
        user=inactive_user,
        code='1234',
    )

    response = api_client.post(
        reverse('auth-verify-email'),
        {
            'email': inactive_user.email,
            'code': '1234',
        },
    )

    assert response.status_code == status.HTTP_200_OK, (
        'Корректное подтверждение email должно возвращать 200'
    )

    inactive_user.refresh_from_db()

    assert inactive_user.is_active is True, (
        'После подтверждения пользователь должен стать активным'
    )
    assert not VarificationCode.objects.filter(user=inactive_user).exists(), (
        'Использованный код должен удаляться'
    )


@pytest.mark.parametrize(
    'email, code',
    [
        ('inactive@example.com', '0000'),
        ('inactive@example.com', '123'),
        ('unknown@example.com', '1234'),
        ('', ''),
    ],
)
def test_verify_email_invalid_data(
    api_client,
    inactive_user,
    email,
    code,
    db,
):
    """Проверяет отказ подтверждения с некорректными данными."""
    VarificationCode.objects.create(
        user=inactive_user,
        code='1234',
    )

    response = api_client.post(
        reverse('auth-verify-email'),
        {
            'email': email,
            'code': code,
        },
    )

    assert response.status_code in (
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_404_NOT_FOUND,
    ), 'Некорректные данные подтверждения должны отклоняться'

    inactive_user.refresh_from_db()

    assert inactive_user.is_active is False, (
        'При ошибке пользователь не должен активироваться'
    )


def test_verify_email_already_verified(api_client, user):
    """Проверяет запрет повторного подтверждения активного пользователя."""
    response = api_client.post(
        reverse('auth-verify-email'),
        {
            'email': user.email,
            'code': '1234',
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST, (
        'Активный пользователь не должен повторно подтверждать email'
    )


def test_change_email_correct(api_client, user):
    """Проверяет смену email и деактивацию пользователя."""
    new_email = 'new@example.com'

    response = api_client.patch(
        reverse('auth-change-email'),
        {
            'email': user.email,
            'password': 'Password123!',
            'new_email': new_email,
        },
    )

    assert response.status_code == status.HTTP_200_OK, (
        'Корректная смена email должна возвращать 200'
    )

    user.refresh_from_db()

    assert user.email == new_email, (
        'Email пользователя не был изменен'
    )
    assert user.is_active is False, (
        'После смены email пользователь должен быть неактивным'
    )


@pytest.mark.parametrize(
    'password, new_email',
    [
        ('WrongPassword123!', 'new@example.com'),
        ('Password123!', 'user@example.com'),
    ],
)
def test_change_email_invalid_data(
    api_client,
    user,
    password,
    new_email,
):
    """Проверяет отказ смены email при некорректных данных."""
    response = api_client.patch(
        reverse('auth-change-email'),
        {
            'email': user.email,
            'password': password,
            'new_email': new_email,
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST, (
        'Некорректные данные смены email должны отклоняться'
    )

    user.refresh_from_db()

    assert user.email == 'user@example.com', (
        'При ошибке email не должен изменяться'
    )
    assert user.is_active is True, (
        'При ошибке пользователь не должен деактивироваться'
    )


def test_change_email_already_exists(
    api_client,
    user,
    inactive_user,
):
    """Проверяет запрет смены email на существующий."""
    response = api_client.patch(
        reverse('auth-change-email'),
        {
            'email': user.email,
            'password': 'Password123!',
            'new_email': inactive_user.email,
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST, (
        'Нельзя изменить email на уже существующий'
    )

    user.refresh_from_db()

    assert user.email == 'user@example.com', (
        'Email не должен изменяться при ошибке'
    )


def test_change_password_correct(api_client, user, db):
    """Проверяет смену пароля и удаление кода подтверждения."""
    new_password = 'NewPassword123!'

    VarificationCode.objects.create(
        user=user,
        code='1234',
    )

    response = api_client.patch(
        reverse('auth-change-password'),
        {
            'email': user.email,
            'code': '1234',
            'new_password': new_password,
        },
    )

    assert response.status_code == status.HTTP_200_OK, (
        'Корректная смена пароля должна возвращать 200'
    )

    user.refresh_from_db()

    assert user.check_password(new_password), (
        'Новый пароль не был сохранен'
    )
    assert not VarificationCode.objects.filter(user=user).exists(), (
        'Использованный код должен удаляться'
    )


@pytest.mark.parametrize(
    'code, new_password',
    [
        ('000000', 'NewPassword123!'),
        ('123', 'NewPassword123!'),
        ('123456', 'Password123!'),
    ],
)
def test_change_password_invalid_data(
    api_client,
    user,
    code,
    new_password,
    db,
):
    """Проверяет отказ смены пароля при некорректных данных."""
    VarificationCode.objects.create(
        user=user,
        code='1234',
    )

    response = api_client.patch(
        reverse('auth-change-password'),
        {
            'email': user.email,
            'code': code,
            'new_password': new_password,
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST, (
        'Некорректные данные смены пароля должны отклоняться'
    )
