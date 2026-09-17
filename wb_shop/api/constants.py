class MsgConstants:
    EMAIL_ALREADY_CONFIRMED = 'Почта \'{user.email}\' уже подтверждена'
    EMAIL_SEND_CODE = (
        'Код подтверждения отправлен на \'{email}\'. '
        'Чтобы продолжить регистрацию, отправьте код '
        'POST-запросом на auth/verify-email.'
    )


class SerializerConstants:
    ORDER_COMMON_FIELDS = [
        'public_id', 'total_price', 'address',
        'status', 'created_at', 'updated_at'
    ]
