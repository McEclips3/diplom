from django.db import transaction
from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Product, CustomUser, Order, OrderProduct, Category, \
    Characteristic

USER_MODEL = get_user_model()


class ListProductsSerializer(serializers.ListSerializer):
    def validate(self, data):
        names = [item['name'] for item in data]
        unique_names = set()
        duplicates = set()

        for name in names:
            if name in unique_names:
                duplicates.add(name)
            else:
                unique_names.add(name)

        if duplicates:
            error_message = f"These products are duplicated in your list: " \
                            f"{', '.join(duplicates)}"
            raise serializers.ValidationError(
                {"duplicated products": error_message})

        return data


class ProductSerializer(serializers.ModelSerializer):
    provider = serializers.ReadOnlyField(source='provider.username')
    category = serializers.ReadOnlyField(source='category.name')

    def validate_name(self, value):
        try:
            Product.objects.get(
                name=value, provider=self.context['request'].user
            )
        except Product.DoesNotExist:
            pass
        else:
            raise serializers.ValidationError(
                f'You already have a product with this name - {value}'
            )
        return value

    class Meta:
        model = Product
        fields = ('name', 'price', 'open_for_sale', 'provider', 'category')
        list_serializer_class = ListProductsSerializer


class CharacteristicSerializer(serializers.ModelSerializer):
    name = serializers.CharField(min_length=3, max_length=255)

    class Meta:
        model = Characteristic
        fields = ('name',)


class CategorySerializer(serializers.ModelSerializer):
    characteristics = CharacteristicSerializer(many=True)

    @transaction.atomic
    def create(self, validated_data):
        characteristics_data = validated_data.pop('characteristics')
        category = Category.objects.create(**validated_data)
        for characteristic_data in characteristics_data:
            characteristic_object \
                = Characteristic.objects.get_or_create(**characteristic_data)[0]
            category.characteristics.add(characteristic_object)
        return category

    class Meta:
        model = Category
        fields = ('id', 'name', 'characteristics')


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True)

    def create(self, validated_data):
        user = USER_MODEL.objects.create_user(**validated_data)
        return user

    def validate_email(self, value):
        if USER_MODEL.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                'User with this email already exists'
            )
        return value

    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'password',
                  'email', 'is_provider')


class UserDetailSerializer(UserSerializer):
    products = ProductSerializer(many=True, read_only=True)

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ('products',)


class ProductOrderSerializer(serializers.ModelSerializer):
    quantity = serializers.IntegerField()

    class Meta:
        model = Product
        fields = ('id', 'name', 'price', 'quantity')


class OrderSerializer(serializers.ModelSerializer):
    products = ProductOrderSerializer(many=True,
                                      source='orderproduct_set')
    user = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = Order
        fields = ('id', 'user', 'comment', 'created_at', 'products')

    @transaction.atomic
    def create(self, validated_data):
        products_data = validated_data.pop('orderproduct_set')

        order = Order.objects.create(**validated_data)
        for product_data in products_data:
            product_id = product_data['product']['id']
            quantity = product_data['quantity']
            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                raise serializers.ValidationError(
                    f'Product with id {product_id} does not exist'
                )
            if not product.open_for_sale:
                raise serializers.ValidationError(
                    f'Product with id {product_id} is not open for sale'
                )
            OrderProduct.objects.create(
                order=order,
                product=product,
                quantity=quantity
            )
        return order
