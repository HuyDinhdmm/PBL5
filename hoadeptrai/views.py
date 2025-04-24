from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib import messages
from django.http import JsonResponse
from .models import Customer, Product, Order, OrderItem, Category, Message  # Add Message to imports
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from django.template.loader import render_to_string
import random
import string

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
    category_id = request.GET.get('category')
    
    if category_id:
        products = Product.objects.filter(category_id=category_id, status=True)
    else:
        products = Product.objects.filter(status=True)
        
    categories = Category.objects.all()
    
    context = {
        'Products': products,
        'categories': categories,
    }
    return render(request, 'app/home.html', context)

def cart(request):
    if request.user.is_authenticated:
        customer = Customer.objects.get(id=request.user.id)
        order, created = Order.objects.get_or_create(
            customer=customer, 
            status='pending',
            defaults={'total_amount': 0, 'shipping_address': customer.address or ''}
        )
        items = order.orderitem_set.all()
        
        # Lấy category của các sản phẩm trong giỏ hàng
        cart_categories = [item.product.category for item in items]
        
        # Lấy các sản phẩm đề xuất từ cùng category
        recommended_products = Product.objects.filter(
            category__in=cart_categories,
            status=True  # Chỉ lấy sản phẩm còn hàng
        ).exclude(
            id__in=[item.product.id for item in items]  # Loại bỏ sản phẩm đã có trong giỏ
        ).distinct().order_by('?')[:8]  # Lấy ngẫu nhiên 8 sản phẩm
    else:
        items = []
        order = {'get_cart_total': 0, 'get_cart_items': 0}
        recommended_products = []

    context = {
        'items': items,
        'order': order,
        'recommended_products': recommended_products
    }
    return render(request, 'app/cart.html', context)

def checkout(request):
    if not request.user.is_authenticated:
        return redirect('login')

    customer = Customer.objects.get(id=request.user.id)
    order, created = Order.objects.get_or_create(
        customer=customer,
        status='pending',
        defaults={
            'total_amount': 0,
            'shipping_address': customer.address or ''
        }
    )

    if request.method == 'POST':
        shipping_address = request.POST.get('shipping_address')
        payment_method = request.POST.get('payment_method')
        
        if order.orderitem_set.exists():
            order.shipping_address = shipping_address
            order.payment_method = payment_method
            order.status = 'processing'
            order.save()
            
            messages.success(request, 'Order placed successfully!')
            return redirect('home')
        else:
            messages.error(request, 'Your cart is empty!')

    context = {
        'order': order,
        'items': order.orderitem_set.all(),
        'shipping_address': customer.address,
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
        # Fix: Changed from product_name__icontains(query) to product_name__icontains=query
        products = Product.objects.filter(product_name__icontains=query)
    else:
        products = Product.objects.none()
    
    context = {
        'Products': products,
        'query': query
    }
    return render(request, 'app/search_results.html', context)

def user_order_history(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    orders = Order.objects.filter(customer=request.user).order_by('-order_date')
    
    for order in orders:
        order.items = order.orderitem_set.all()
        
    context = {
        'orders': orders
    }
    return render(request, 'app/order_history.html', context)

def order_detail(request, order_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
        
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    items = order.orderitem_set.all()
    
    data = {
        'order_id': order.id,
        'date': order.order_date.strftime('%d/%m/%Y %H:%M'),
        'status': order.status,
        'payment_method': order.payment_method,
        'shipping_address': order.shipping_address,
        'items': [],
        'total': float(order.total_amount)
    }
    
    for item in items:
        data['items'].append({
            'product': item.product.product_name,
            'quantity': item.quantity, 
            'price': float(item.price),
            'total': float(item.get_total)
        })
    
    return JsonResponse(data)

def user_profile(request):
    if not request.user.is_authenticated:
        return redirect('login')
        
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.phone_number = request.POST.get('phone_number', '')
        user.address = request.POST.get('address', '')
        
        # Handle password change
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        if current_password and new_password:
            if user.check_password(current_password):
                user.set_password(new_password)
                messages.success(request, 'Mật khẩu đã được cập nhật')
            else:
                messages.error(request, 'Mật khẩu hiện tại không đúng')
        
        user.save()
        messages.success(request, 'Thông tin tài khoản đã được cập nhật')
        return redirect('user_profile')
        
    return render(request, 'app/profile.html', {'user': request.user})

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
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        new_status = request.POST.get('status')
        if order_id and new_status:
            order = get_object_or_404(Order, id=order_id)
            order.status = new_status
            order.save()
            messages.success(request, 'Order status updated successfully')
            return redirect('admin_orders')

    orders = Order.objects.all().order_by('-order_date')
    return render(request, 'admin/orders.html', {'orders': orders})

@staff_member_required
def admin_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    items = order.orderitem_set.all()

    # Định dạng dữ liệu trả về
    return JsonResponse({
        'order_id': order.id,
        'date': order.order_date.strftime('%d/%m/%Y %H:%M'),
        'status': order.status,
        'payment_method': order.payment_method or 'Không xác định',
        'customer': {
            'name': order.customer.username,
            'email': order.customer.email,
            'phone': order.customer.phone_number or 'Chưa cập nhật',
        },
        'shipping_address': order.shipping_address,
        'items': [{
            'product': item.product.product_name,
            'category': item.product.category.category_name,
            'image': item.product.image_url,
            'quantity': item.quantity,
            'price': float(item.price),
            'total': float(item.get_total)
        } for item in items],
        'total': float(order.total_amount)
    })

@staff_member_required
def delete_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order.delete()
    messages.success(request, 'Order deleted successfully')
    return redirect('admin_orders')

@staff_member_required
def admin_customers(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        customer_id = request.POST.get('customer_id')
        
        if action == 'toggle_status':
            try:
                customer = Customer.objects.get(id=customer_id)
                if customer.role != 'admin':
                    customer.is_active = not customer.is_active
                    customer.save()
                    messages.success(request, f'Customer status updated successfully')
                return JsonResponse({'success': True})
            except Customer.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Customer not found'}, status=404)
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)}, status=500)
        
        elif action == 'edit':
            try:
                customer = Customer.objects.get(id=customer_id)
                if customer.role != 'admin':
                    customer.email = request.POST.get('email')
                    customer.phone_number = request.POST.get('phone_number')
                    customer.address = request.POST.get('address')
                    customer.role = request.POST.get('role')
                    customer.is_active = request.POST.get('is_active') == 'on'
                    customer.save()
                    messages.success(request, 'Customer updated successfully')
                return redirect('admin_customers')
            except Customer.DoesNotExist:
                messages.error(request, 'Customer not found')
                return redirect('admin_customers')
            
    # Only show non-admin users or admins if current user is admin
    if request.user.role == 'admin':
        customers = Customer.objects.all().order_by('-date_joined')
    else:
        customers = Customer.objects.exclude(role='admin').order_by('-date_joined')
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

@staff_member_required
def admin_change_password(request):
    if request.method == 'POST':
        try:
            customer_id = request.POST.get('customer_id')
            new_password = request.POST.get('new_password')
            customer = Customer.objects.get(id=customer_id)
            
            if customer.role != 'admin' or request.user.role == 'admin':
                customer.set_password(new_password)
                customer.save()
                return JsonResponse({'success': True})
            return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
        except Customer.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Customer not found'}, status=404)
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

@staff_member_required
def admin_reset_password(request):
    if request.method == 'POST':
        try:
            customer_id = request.POST.get('customer_id')
            customer = Customer.objects.get(id=customer_id)
            
            if customer.role != 'admin' or request.user.role == 'admin':
                # Generate random password
                new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                customer.set_password(new_password)
                customer.save()
                return JsonResponse({'success': True, 'new_password': new_password})
            return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
        except Customer.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Customer not found'}, status=404)
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

@staff_member_required 
def admin_chat(request):
    # Get all customers for admin, or only assigned customers for sellers
    if request.user.role == 'admin':
        users = Customer.objects.filter(role='customer')
    else:
        # For sellers, only show their customers (you'll need to implement this logic)
        users = Customer.objects.filter(role='customer')
    
    # Add unread messages flag
    for user in users:
        user.has_unread = Message.objects.filter(
            sender=user,
            receiver=request.user,
            is_read=False
        ).exists()
    
    return render(request, 'admin/chat.html', {'users': users})

@staff_member_required
def send_message(request):
    if request.method == 'POST':
        receiver_id = request.POST.get('receiver_id')
        message_text = request.POST.get('message')
        
        try:
            receiver = Customer.objects.get(id=receiver_id)
            Message.objects.create(
                sender=request.user,
                receiver=receiver,
                message_text=message_text
            )
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
            
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@staff_member_required
def get_messages(request, user_id):
    try:
        other_user = Customer.objects.get(id=user_id)
        messages = Message.objects.filter(
            (Q(sender=request.user, receiver=other_user) |
             Q(sender=other_user, receiver=request.user))
        ).order_by('sent_at')
        
        # Mark messages as read
        messages.filter(receiver=request.user, is_read=False).update(is_read=True)
        
        messages_data = [{
            'sender_id': msg.sender.id,
            'message': msg.message_text,
            'sent_at': msg.sent_at.strftime('%I:%M %p, %d/%m/%Y')
        } for msg in messages]
        
        return JsonResponse({'messages': messages_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

def customer_chat(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'app/customer_chat.html')

def customer_chat_send(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    if request.method == 'POST':
        message_text = request.POST.get('message')
        try:
            # Find an admin to send the message to
            admin = Customer.objects.filter(role='admin').first()
            if not admin:
                admin = Customer.objects.filter(is_staff=True).first()
            
            if admin:
                Message.objects.create(
                    sender=request.user,
                    receiver=admin,
                    message_text=message_text
                )
                return JsonResponse({'success': True})
            return JsonResponse({'success': False, 'error': 'No admin available'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
            
    return JsonResponse({'success': False, 'error': 'Invalid request'})

def customer_chat_messages(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
        
    try:
        # Get messages between customer and any admin
        messages = Message.objects.filter(
            (Q(sender=request.user) | Q(receiver=request.user))
        ).order_by('sent_at')
        
        messages_data = [{
            'id': msg.id,  # Add message id
            'sender_id': msg.sender.id,
            'message': msg.message_text,
            'sent_at': msg.sent_at.strftime('%I:%M %p, %d/%m/%Y')
        } for msg in messages]
        
        return JsonResponse({'messages': messages_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)