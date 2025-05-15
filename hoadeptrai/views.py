from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from .models import Customer, Product, Order, OrderItem, Category, Message, Promotion  # Add Promotion to imports
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from django.template.loader import render_to_string
import random
import string
import qrcode
import io
import base64
import logging
import json
import time
import uuid
import hmac
import hashlib
import requests
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

logger = logging.getLogger(__name__)

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        # Username validation
        if len(username) < 3:
            messages.error(request, 'Username phải có ít nhất 3 ký tự')
            return redirect('register')
            
        if len(username) > 20:
            messages.error(request, 'Username không được vượt quá 20 ký tự')
            return redirect('register')
            
        if not username.replace('_', '').isalnum():
            messages.error(request, 'Username chỉ được chứa chữ cái, số và dấu gạch dưới')
            return redirect('register')
            
        # Check if username exists
        if Customer.objects.filter(username=username).exists():
            messages.error(request, 'Username này đã được sử dụng, vui lòng chọn username khác')
            return redirect('register')
            
        # Create user
        try:
            user = Customer.objects.create_user(
                username=username,
                email=email,
                password=password,
                role='customer'
            )
            auth_login(request, user)
            messages.success(request, 'Đăng ký thành công!')
            return redirect('home')
        except Exception as e:
            messages.error(request, f'Đăng ký thất bại: {str(e)}')
            return redirect('register')
        
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
    order = Order.objects.filter(customer=customer, status='pending').first()

    if request.method == 'POST':
        shipping_address = request.POST.get('shipping_address')
        payment_method = request.POST.get('payment_method')
        phone_number = request.POST.get('phone_number')
        
        # Add phone number validation
        if not phone_number.isdigit() or len(phone_number) != 10:
            messages.error(request, 'Số điện thoại không hợp lệ')
            return redirect('checkout')
        
        if not order or not order.orderitem_set.exists():
            message = 'Giỏ hàng của bạn đang trống!'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': message})
            messages.error(request, message)
            return redirect('cart')

        try:
            order.shipping_address = shipping_address
            order.payment_method = payment_method
            # Update customer phone number
            customer.phone_number = phone_number
            customer.save()
            order.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                if payment_method == 'cod':
                    order.status = 'processing'
                    order.save()
                    return JsonResponse({
                        'success': True,
                        'redirect_url': reverse('home')
                    })
                elif payment_method == 'zalopay':
                    return JsonResponse({
                        'success': True,
                        'order_id': order.id
                    })
        except Exception as e:
            logger.error(f"Checkout error: {str(e)}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Có lỗi xảy ra trong quá trình xử lý!'})
            messages.error(request, 'Có lỗi xảy ra trong quá trình xử lý!')
    
    context = {
        'order': order,
        'items': order.orderitem_set.all() if order else [],
        'shipping_address': customer.address,
        'user': customer,
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

def compute_hmac256(key, data):
    hmac_obj = hmac.new(key.encode('utf-8'), data.encode('utf-8'), hashlib.sha256)
    return hmac_obj.hexdigest()

@csrf_exempt
def create_payment(request, order_id):
    try:
        order = get_object_or_404(Order, id=order_id)
        
        # Keep validation but don't change status yet
        if order.status != 'pending':
            return JsonResponse({
                'return_code': -1,
                'return_message': 'Đơn hàng không hợp lệ hoặc đã được xử lý'
            })

        if order.payment_method != 'zalopay':
            return JsonResponse({
                'return_code': -1,
                'return_message': 'Phương thức thanh toán không hợp lệ'
            }) 

        # ZaloPay order creation parameters
        app_id = settings.ZALOPAY_SETTINGS.get('APP_ID')
        key1 = settings.ZALOPAY_SETTINGS.get('KEY1') 
        
        if not all([app_id, key1]):
            return JsonResponse({
                'return_code': -1,
                'return_message': 'Thiếu cấu hình ZaloPay'
            })

        app_user = request.user.username
        app_time = str(int(time.time() * 1000))
        app_trans_id = time.strftime("%y%m%d_") + str(uuid.uuid4())[:8]
        amount = str(int(order.total_amount))

        embed_data = {
            "merchantinfo": "embeddata123",
            "promotioninfo": "",
            "redirecturl": request.build_absolute_uri('/payment/zalopay-return/')
        }
        
        items = [{
            "itemid": str(item.product.id),
            "itemname": item.product.product_name,
            "itemprice": int(item.price),
            "itemquantity": item.quantity
        } for item in order.orderitem_set.all()]

        embed_data_str = json.dumps(embed_data)
        items_str = json.dumps(items)

        mac_input = f"{app_id}|{app_trans_id}|{app_user}|{amount}|{app_time}|{embed_data_str}|{items_str}"
        mac = compute_hmac256(key1, mac_input)

        order_data = {
            "appid": app_id,
            "apptransid": app_trans_id,
            "appuser": app_user,
            "apptime": app_time,
            "amount": amount,
            "embeddata": embed_data_str,
            "item": items_str,
            "description": f"Thanh toán đơn hàng #{order.id}",
            "mac": mac,
            "bankcode": "zalopayapp"
        }

        api_url = settings.ZALOPAY_SETTINGS['API_URL']

        # Log request data for debugging
        logger.info(f"ZaloPay Request Data: {order_data}")
        
        # Make API call to ZaloPay with timeout
        try:
            response = requests.post(api_url, data=order_data, timeout=30)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"ZaloPay API Error: {str(e)}")
            return JsonResponse({
                'return_code': -1,
                'return_message': 'Lỗi kết nối đến cổng thanh toán'
            })

        result = response.json()
        logger.info(f"ZaloPay Response: {result}")

        if result.get('returncode') == 1:
            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(result.get('orderurl'))
            qr.make(fit=True)
            qr_image = qr.make_image(fill_color="black", back_color="white")

            # Convert QR to base64
            buffered = io.BytesIO()
            qr_image.save(buffered, format="PNG")
            qr_base64 = base64.b64encode(buffered.getvalue()).decode()

            # Save transaction ID
            order.zalopay_trans_id = app_trans_id
            order.save()
            
            return render(request, 'app/zalopay_payment.html', {
                'order': order,
                'amount': order.total_amount,
                'order_url': result.get('orderurl'),
                'zptranstoken': result.get('zptranstoken'),
                'order_qr_code': qr_base64,  # Add QR code to context
                'debug': settings.DEBUG
            })
        else:
            messages.error(request, result.get('returnmessage', 'Thanh toán thất bại'))
            return redirect('checkout')

    except Exception as e:
        logger.error(f"Payment creation error: {str(e)}", exc_info=True)
        messages.error(request, 'Có lỗi xảy ra khi xử lý thanh toán')
        return redirect('checkout')

@csrf_exempt
def zalopay_callback(request):
    if request.method == 'POST':
        try:
            # Get callback data from ZaloPay
            callback_data = json.loads(request.body)
            data_str = callback_data.get('data')
            req_mac = callback_data.get('mac')

            # Verify callback authenticity
            key2 = settings.ZALOPAY_SETTINGS['KEY2']
            mac = compute_hmac256(key2, data_str)

            if req_mac != mac:
                logger.error("Invalid callback MAC")
                return JsonResponse({
                    "returncode": -1,
                    "returnmessage": "mac not equal"
                })

            # Parse transaction data
            data = json.loads(data_str)
            app_trans_id = data.get('apptransid')
            status = int(data.get('status', 0))  # Add status check

            # Update order status only if payment is successful
            try:
                order = Order.objects.get(zalopay_trans_id=app_trans_id)
                if status == 1:  # Payment successful
                    order.status = 'processing'  # Now we change status
                    order.payment_status = 'completed'
                    messages.success(request, 'Thanh toán thành công!')
                else:  # Payment failed
                    order.payment_status = 'failed'
                    messages.error(request, 'Thanh toán thất bại!')
                order.save()
                
                logger.info(f"Payment Status Updated: Order #{order.id} - Status: {status}")
                
            except Order.DoesNotExist:
                logger.error(f"Order not found for ZaloPay transaction: {app_trans_id}")

            return JsonResponse({
                "returncode": 1,
                "returnmessage": "success"
            })

        except Exception as e:
            logger.error(f"Callback error: {str(e)}")
            return JsonResponse({
                "returncode": 0,
                "returnmessage": str(e)
            })

    return HttpResponse("Invalid request method", status=405)

def zalopay_return(request):
    # Handle return from ZaloPay payment
    trans_id = request.GET.get('apptransid')
    if trans_id:
        try:
            order = Order.objects.get(zalopay_trans_id=trans_id)
            if order.status == 'paid':
                messages.success(request, 'Thanh toán thành công!')
            else:
                messages.warning(request, 'Đang xử lý thanh toán...')
            return redirect('order_detail', order_id=order.id)
        except Order.DoesNotExist:
            messages.error(request, 'Không tìm thấy đơn hàng!')
    return redirect('home')

def apply_promotion(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Vui lòng đăng nhập!'})
        
    if request.method == 'POST':
        code = request.POST.get('promotion_code')
        try:
            promotion = Promotion.objects.get(
                promotion_code=code,
                start_date__lte=timezone.now(),
                end_date__gte=timezone.now(),
                is_active=True
            )
            
            # Get current cart
            order = Order.objects.get(customer=request.user, status='pending')
            cart_total = order.get_cart_total

            # Check minimum order value
            if promotion.min_order_value and cart_total < promotion.min_order_value:
                return JsonResponse({
                    'success': False, 
                    'error': f'Đơn hàng tối thiểu {int(promotion.min_order_value)}đ'
                })

            # Calculate discount
            if promotion.discount_type == 'percent':
                discount = cart_total * (promotion.discount_value / 100)
                if promotion.max_discount_amount:
                    discount = min(discount, promotion.max_discount_amount)
            else:
                discount = promotion.discount_value

            # Update order
            order.promotion = promotion
            order.save()

            new_total = cart_total - discount
            
            return JsonResponse({
                'success': True,
                'discount_amount': int(discount),
                'new_total': int(new_total),
                'discount_value': (
                    f"{int(promotion.discount_value)}%" 
                    if promotion.discount_type == 'percent' 
                    else f"{int(promotion.discount_value)}đ"
                )
            })

        except Promotion.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Mã giảm giá không hợp lệ!'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': 'Có lỗi xảy ra!'
            })
            
    return JsonResponse({'success': False, 'error': 'Invalid request'})