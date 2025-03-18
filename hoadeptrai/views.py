from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib import messages
from django.http import JsonResponse
from .models import Customer, Product, Order, OrderItem, Category  # Add Category to imports
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta

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
    categories = Category.objects.all()
    print(f"Number of products: {products.count()}")  # For debugging
    print(f"Number of categories: {categories.count()}")  # For debugging
    context = {
        'Products': products,
        'categories': categories
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

def logout_view(request):
    logout(request)
    messages.success(request, 'Logged out successfully!')
    return redirect('home')

def add_to_cart(request, product_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Please login to add items to cart'}, status=401)
        
    product = get_object_or_404(Product, id=product_id)
    customer = request.user
    order, created = Order.objects.get_or_create(
        customer=customer,
        status='pending',
        defaults={
            'total_amount': 0,
            'shipping_address': customer.address or ''
        }
    )
    
    order_item, created = OrderItem.objects.get_or_create(
        order=order,
        product=product,
        defaults={
            'quantity': 0,
            'price': product.price
        }
    )
    
    order_item.quantity += 1
    order_item.price = product.price  # Ensure price is updated
    order_item.save()
    
    # Update order total
    order.total_amount = sum(item.get_total for item in order.orderitem_set.all())
    order.save()
    
    return JsonResponse({
        'success': True,
        'cart_total': order.get_cart_items,
        'message': 'Item added to cart successfully'
    })

def update_cart(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Please login first'}, status=401)

    action = request.GET.get('action')
    product_id = request.GET.get('product_id')
    
    if not all([action, product_id]):
        return JsonResponse({'error': 'Invalid request'}, status=400)
        
    customer = request.user
    product = get_object_or_404(Product, id=product_id)
    order = Order.objects.get(customer=customer, status='pending')
    order_item = get_object_or_404(OrderItem, order=order, product=product)
    
    if action == 'add':
        order_item.quantity += 1
    elif action == 'remove':
        order_item.quantity -= 1
    
    if order_item.quantity <= 0:
        order_item.delete()
    else:
        order_item.save()
        
    order.total_amount = order.get_cart_total
    order.save()
    
    return JsonResponse({
        'quantity': order_item.quantity if order_item.quantity > 0 else 0,
        'cart_total': order.get_cart_items,
        'item_total': float(order_item.get_total) if order_item.quantity > 0 else 0,
        'cart_total_amount': float(order.get_cart_total)
    })

def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    related_products = Product.objects.filter(category=product.category).exclude(id=product_id)[:4]
    context = {
        'product': product,
        'related_products': related_products
    }
    return render(request, 'app/product_detail.html', context)

def search_products(request):
    query = request.GET.get('q', '')
    if query:
        products = Product.objects.filter(product_name__icontains(query))
    else:
        products = Product.objects.none()
    
    context = {
        'Products': products,
        'query': query
    }
    return render(request, 'app/search_results.html', context)

@staff_member_required
def admin_dashboard(request):
    # Get statistics
    total_orders = Order.objects.count()
    total_revenue = Order.objects.filter(status='delivered').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_products = Product.objects.count()
    total_customers = Customer.objects.filter(role='customer').count()
    
    # Recent orders
    recent_orders = Order.objects.order_by('-order_date')[:5]
    
    # Category analytics
    categories = Category.objects.annotate(product_count=Count('product'))
    category_labels = [cat.category_name for cat in categories]
    category_data = [cat.product_count for cat in categories]
    
    context = {
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'total_products': total_products,
        'total_customers': total_customers,
        'recent_orders': recent_orders,
        'category_labels': category_labels,
        'category_data': category_data,
    }
    return render(request, 'admin/dashboard.html', context)

@staff_member_required
def admin_products(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            product_name = request.POST.get('product_name')
            price = request.POST.get('price')
            category_id = request.POST.get('category')
            description = request.POST.get('description')
            image_url = request.POST.get('image_url')
            status = request.POST.get('status') == 'true'
            
            Product.objects.create(
                seller=request.user,
                product_name=product_name,
                price=price,
                category_id=category_id,
                description=description,
                image_url=image_url,
                status=status
            )
            messages.success(request, 'Product added successfully!')
            
        elif action == 'edit':
            product_id = request.POST.get('product_id')
            product = Product.objects.get(id=product_id)
            product.product_name = request.POST.get('product_name')
            product.price = request.POST.get('price')
            product.category_id = request.POST.get('category')
            product.description = request.POST.get('description')
            product.image_url = request.POST.get('image_url')
            product.status = request.POST.get('status') == 'true'
            product.save()
            messages.success(request, 'Product updated successfully!')
            
        elif action == 'delete':
            product_id = request.POST.get('product_id')
            Product.objects.get(id=product_id).delete()
            messages.success(request, 'Product deleted successfully!')
            
        return redirect('admin_products')

    products = Product.objects.all().order_by('-id')
    categories = Category.objects.all()
    return render(request, 'admin/products.html', {
        'products': products,
        'categories': categories
    })

@staff_member_required
def admin_orders(request):
    orders = Order.objects.all().order_by('-order_date')
    return render(request, 'admin/orders.html', {'orders': orders})

@staff_member_required
def admin_customers(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        customer_id = request.POST.get('customer_id')
        
        if action == 'toggle_status':
            customer = Customer.objects.get(id=customer_id)
            customer.is_active = not customer.is_active
            customer.save()
            return JsonResponse({'success': True})
            
    customers = Customer.objects.filter(role='customer').order_by('-date_joined')
    return render(request, 'admin/customers.html', {'customers': customers})

@staff_member_required
def admin_customer_details(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)
    orders = Order.objects.filter(customer=customer).order_by('-order_date')
    
    customer_html = render_to_string('admin/partials/customer_info.html', {'customer': customer})
    order_html = render_to_string('admin/partials/order_history.html', {'orders': orders})
    
    return JsonResponse({
        'customerHtml': customer_html,
        'orderHtml': order_html
    })

@staff_member_required
def admin_categories(request):
    categories = Category.objects.all()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            category_name = request.POST.get('category_name')
            parent_id = request.POST.get('parent_category')
            parent = Category.objects.get(id=parent_id) if parent_id else None
            Category.objects.create(category_name=category_name, parent_category=parent)
            messages.success(request, 'Category added successfully!')
        elif action == 'edit':
            category_id = request.POST.get('category_id')
            category = Category.objects.get(id=category_id)
            category.category_name = request.POST.get('category_name')
            parent_id = request.POST.get('parent_category')
            category.parent_category = Category.objects.get(id=parent_id) if parent_id else None
            category.save()
            messages.success(request, 'Category updated successfully!')
        elif action == 'delete':
            category_id = request.POST.get('category_id')
            Category.objects.get(id=category_id).delete()
            messages.success(request, 'Category deleted successfully!')
        return redirect('admin_categories')
    
    context = {
        'categories': categories,
    }
    return render(request, 'admin/categories.html', context)