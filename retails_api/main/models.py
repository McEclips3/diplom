from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager


class ProviderManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_provider=True)


class CustomerManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_provider=False)


class AvailableProductsManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(open_for_sale=True)


class CustomUser(AbstractUser):
    is_provider = models.BooleanField(default=False)
    email = models.EmailField(unique=True)

    objects = UserManager()
    providers = ProviderManager()
    customers = CustomerManager()

    def __str__(self):
        return self.username


class Product(models.Model):
    name = models.CharField(max_length=255)
    price = models.FloatField()
    open_for_sale = models.BooleanField(default=True)
    category = models.ForeignKey('Category', on_delete=models.CASCADE)
    characteristics = models.ManyToManyField('Characteristic',
                                             related_name='products',
                                             through='ProductCharacteristic')
    provider = models.ForeignKey(CustomUser, related_name='products',
                                 on_delete=models.CASCADE)

    objects = models.Manager()
    available = AvailableProductsManager()

    class Meta:
        ordering = ['name']
        unique_together = ['name', 'provider']

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    characteristics = models.ManyToManyField('Characteristic',
                                             related_name='categories')

    def __str__(self):
        return self.name


class Characteristic(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class ProductCharacteristic(models.Model):
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    characteristic = models.ForeignKey('Characteristic',
                                       on_delete=models.CASCADE)
    value = models.CharField(max_length=255)

    def __str__(self):
        return self.value


class Order(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE,
                             related_name='orders')
    products = models.ManyToManyField(Product, through='OrderProduct',
                                      related_name='in_orders')
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class OrderProduct(models.Model):
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    order = models.ForeignKey('Order', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ['order', 'product']
