from django.urls import path
from . import views

urlpatterns = [
    path('zalopay/create/<int:order_id>/', views.create_payment, name='create_payment'),
    path('zalopay/callback/', views.zalopay_callback, name='zalopay_callback'),
] 