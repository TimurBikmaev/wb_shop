class SerializerConstants:
    CART_COMMON_FIELDS = [
        'public_id', 'name', 'total_price',
        'created_at', 'updated_at',
    ]
    ORDER_COMMON_FIELDS = [
        'public_id', 'total_price', 'address',
        'status', 'created_at', 'updated_at'
    ]
