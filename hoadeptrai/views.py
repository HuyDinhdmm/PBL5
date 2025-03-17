from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login
from django.contrib import messages
from .models import Customer, Product, Order

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if Customer.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return redirect('register')
            
        user = Customer.objects.create_user(
            username=username,
            email=email,
            password=password,
            role='customer'
        )
        auth_login(request, user)
        messages.success(request, 'Registration successful!')
        return redirect('home')
        
    return render(request, 'app/register.html')


def login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)  # Sử dụng authenticate()
        
        if user is not None:
            auth_login(request, user)
            messages.success(request, 'Login successful!')
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password')
            
    return render(request, 'app/login.html')

def home(request):
    products = Product.objects.all()
    print(f"Number of products: {products.count()}")  # For debugging
    context = {
        'Products': products
    }
    return render(request, 'app/home.html', context)

def cart(request):
    if request.user.is_authenticated:
        customer = Customer.objects.get(id=request.user.id)
        order, created = Order.objects.get_or_create(
            customer=customer, 
            status='pending',
            defaults={
                'total_amount': 0,
                'shipping_address': customer.address or ''
            }
        )
        items = order.orderitem_set.all()
    else:
        items = []
        order = {'get_cart_total': 0, 'get_cart_items': 0}
    
    context = {
        'items': items,
        'order': order
    }
    return render(request, 'app/cart.html', context)

def checkout(request):
    if request.user.is_authenticated:
        customer = Customer.objects.get(id=request.user.id)
        order, created = Order.objects.get_or_create(
            customer=customer,
            status='pending',
            defaults={
                'total_amount': 0,
                'shipping_address': customer.address or ''
            }
        )
        items = order.orderitem_set.all()
    else:
        items = []
        order = {'get_cart_total': 0, 'get_cart_items': 0}
    
    context = {
        'items': items,
        'order': order
    }
    return render(request, 'app/checkout.html', context)