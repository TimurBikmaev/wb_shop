import logging
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from product.models import Cart


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Create admin user and cart'

    def handle(self, *args, **kwargs):
        User = get_user_model()

        email = os.getenv('ADMIN_EMAIL')
        password = os.getenv('ADMIN_PASSWORD')

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'is_active': True,
                'is_staff': True,
                'is_superuser': True,
            },
        )

        if created:
            user.set_password(password)
            user.save()

            logger.info('Создан администратор')

            Cart.objects.create(user=user)
            logger.info('Создана покупная корзина администратора')

        else:
            logger.info('Администратор уже создан')
