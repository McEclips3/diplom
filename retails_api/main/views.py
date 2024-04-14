from datetime import datetime, timedelta

import jwt
from django.urls import reverse

from rest_framework import generics, permissions
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.status import HTTP_404_NOT_FOUND, HTTP_200_OK, \
    HTTP_400_BAD_REQUEST, HTTP_201_CREATED
from django.core.mail import send_mail

from .permissions import IsOwnerOrReadOnly, IsProviderOrReadOnly, \
    IsAdminOrReadOnly
from .serializers import ProductSerializer, UserSerializer, \
    UserDetailSerializer, OrderSerializer, CategorySerializer
from .models import Product, CustomUser, Order, Category


class ProductView(generics.ListCreateAPIView):
    """
    View all products or post a new one \n
    If account is provider, view all products \n
    If account is customer or anonymous, view only available for sale products \n
    If creating a new product, you can pass either one or many products in one request
    """
    serializer_class = ProductSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,
                          IsOwnerOrReadOnly, IsProviderOrReadOnly)

    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        kwargs.setdefault('context', self.get_serializer_context())
        if isinstance(kwargs['context']['request'].data, list):
            kwargs['many'] = True
        return serializer_class(*args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(provider=self.request.user)

    def get_queryset(self):
        if self.request.user.is_anonymous or not self.request.user.is_provider:
            return Product.available.prefetch_related('category__name')
        return Product.objects.prefetch_related('category__name')


class CategoryView(generics.ListCreateAPIView):
    """
    View all categories with appropriate characteristics.
    Only Staff can create new categories and their characteristics.
    """
    serializer_class = CategorySerializer
    permission_classes = (IsAdminOrReadOnly,)
    queryset = Category.objects.all().prefetch_related('characteristics')


class UserList(generics.ListCreateAPIView):
    """
    GET api/users/
    POST api/users/
    """
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer


class UserDetail(generics.RetrieveAPIView):
    """
    GET api/users/1
    """
    queryset = CustomUser.objects.all()
    serializer_class = UserDetailSerializer


class OrderList(generics.ListCreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        if self.request.user.is_provider:
            return Order.objects.filter(products__provider=self.request.user)
        return Order.objects.filter(user=self.request.user)


class OrderFulfilmentNotification(APIView):
    permission_classes = (IsOwnerOrReadOnly, IsProviderOrReadOnly)

    def post(self, request, *args, **kwargs):
        customer = Order.objects.get(id=kwargs['pk']).user
        send_mail(
            'Provider began to fulfill your order!',

            f'Your order has begun to be fulfilled.\n'
            f'provider will contact you shortly.',

            'P5sI8@example.com',

            [customer.email]
        )
        return Response({"message": "email sent"}, status=HTTP_200_OK)


class LoginView(ObtainAuthToken):
    """
    Use this to obtain a token, pass this token to other requests with header:
    Authorization: Bearer 123456789abcdef
    """
    pass

# TODO: change secret to env var
class ResetPasswordView(APIView):
    """
    POST api/v1/reset-password
    PATCH api/v1/reset-password

    post for requesting password reset
    patch for changing password
    """
    authentication_classes = []

    def post(self, request):
        user_mail = request.data.get('email')
        if not user_mail:
            msg = "Email not provided"
            return Response({"error": msg}, status=HTTP_400_BAD_REQUEST)
        try:
            user_object = CustomUser.objects.get(email=user_mail)
        except CustomUser.DoesNotExist:
            msg = "User with this email does not exist"
            return Response({"error": msg}, status=HTTP_404_NOT_FOUND)

        expiration_time = datetime.now() + timedelta(hours=1)

        token = jwt.encode(
            {
                'email': user_object.email,
                'password_hash': user_object.password,
                'exp': expiration_time
            },
            'secret',
            algorithm='HS256'
        )

        send_mail(
            "Your password reset token",

            f"Here is your password reset token: \n{token}\n"
            f"Endpoint is {reverse('reset-password')}\n"
            f"Use this token with patch request as authorization header "
            f"with keyword Bearer to reset your password\n"
            f"params needed: new_password\n"
            f"This token is valid for 1 hour and is one time use only",

            "from@example.com",
            [user_mail],
            fail_silently=False,
        )
        return Response({'message': 'Email sent'}, status=HTTP_200_OK)

    def patch(self, request):
        authorization_header = request.META.get('HTTP_AUTHORIZATION')
        if not authorization_header:
            return Response({'message': 'no authorization provided'},
                            status=HTTP_400_BAD_REQUEST)

        try:
            prefix, token = authorization_header.split(' ')
        except ValueError:
            return Response({'message': 'Invalid authorization header'},
                            status=HTTP_400_BAD_REQUEST)

        if prefix != 'Bearer':
            return Response({'message': 'no Bearer keyword'},
                            status=HTTP_400_BAD_REQUEST)

        new_password = request.data.get('new_password')
        if not new_password:
            return Response({'message': 'new_password not provided'},
                            status=HTTP_400_BAD_REQUEST)

        try:
            jwt_token = jwt.decode(token, 'secret', algorithms=['HS256'])
            user = jwt_token.get('email')
            password_hash = jwt_token.get('password_hash')

            user_object = CustomUser.objects.get(email=user)
            old_password = user_object.password
            if old_password != password_hash:
                raise ValueError('This token was used before')

            user_object.set_password(new_password)
            user_object.save()

        except jwt.PyJWTError as e:
            return Response({'message': f'{e}'}, status=HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response({'message': f'{e}'}, status=HTTP_400_BAD_REQUEST)

        return Response({'message': 'Password changed'}, status=HTTP_201_CREATED)
