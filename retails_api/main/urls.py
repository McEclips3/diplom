from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('reset-password/', views.ResetPasswordView.as_view(), name='reset-password'),

    path('products/', views.ProductView.as_view(), name='products-list'),
    path('categories/', views.CategoryView.as_view(), name='categories-list'),
    path('users/', views.UserList.as_view(), name='users-list'),
    path('users/<int:pk>/', views.UserDetail.as_view(), name='users-detail'),
    path('orders/', views.OrderList.as_view(), name='orders-list'),
]
