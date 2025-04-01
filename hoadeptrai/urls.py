from django.contrib import admin
from django.urls import path
from . import views
urlpatterns = [
    path('', views.home, name='home'),
    path('cart/', views.cart, name='cart'),
    path('checkout/', views.checkout, name='checkout'), 
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('update-cart/', views.update_cart, name='update_cart'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('search/', views.search_products, name='search_products'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-products/', views.admin_products, name='admin_products'),
    path('admin-orders/', views.admin_orders, name='admin_orders'),
    path('admin-orders/delete/<int:order_id>/', views.delete_order, name='delete_order'),
    path('admin-customers/', views.admin_customers, name='admin_customers'),
    path('admin-categories/', views.admin_categories, name='admin_categories'),
    path('admin-customers/toggle-status/', views.admin_customers, name='admin_toggle_customer'),
    path('admin-customers/<int:customer_id>/details/', views.admin_customer_details, name='admin_customer_details'),
]
