import json
import hmac
import hashlib
import requests
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from hoadeptrai.models import Order
from .zalopay_config import *

def create_payment(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
        
        # Prepare payment data
        app_trans_id = f"{order_id}_{get_timestamp()}"  # Unique transaction ID
        amount = int(order.total_amount * 100)  # Convert to VND (cents)
        
        # Create payment data
        payment_data = {
            "app_id": ZALOPAY_APP_ID,
            "app_trans_id": app_trans_id,
            "app_user": str(order.customer.id),
            "app_time": get_timestamp(),
            "amount": amount,
            "item": json.dumps([{"item_name": f"Order #{order_id}"}]),
            "description": f"Payment for order #{order_id}",
            "bank_code": "zalopayapp",
            "callback_url": CALLBACK_URL
        }
        
        # Create mac
        data = f"{payment_data['app_id']}|{payment_data['app_trans_id']}|{payment_data['app_user']}|{payment_data['amount']}|{payment_data['app_time']}|{payment_data['description']}"
        payment_data['mac'] = hmac.new(ZALOPAY_KEY1.encode(), data.encode(), hashlib.sha256).hexdigest()
        
        # Send request to ZaloPay
        response = requests.post(ZALOPAY_ENDPOINT, json=payment_data)
        result = response.json()
        
        if result['return_code'] == 1:
            # Update order with payment information
            order.payment_id = app_trans_id
            order.payment_method = 'zalopay'
            order.save()
            
            return JsonResponse({
                'return_code': 1,
                'return_message': 'Success',
                'order_url': result['order_url']
            })
        else:
            return JsonResponse({
                'return_code': 0,
                'return_message': result['return_message']
            })
            
    except Order.DoesNotExist:
        return JsonResponse({
            'return_code': 0,
            'return_message': 'Order not found'
        })
    except Exception as e:
        return JsonResponse({
            'return_code': 0,
            'return_message': str(e)
        })

@csrf_exempt
@require_POST
def zalopay_callback(request):
    try:
        data = json.loads(request.body)
        app_trans_id = data.get('app_trans_id')
        order_id = app_trans_id.split('_')[0]
        
        # Verify callback data
        mac = hmac.new(ZALOPAY_KEY2.encode(), request.body, hashlib.sha256).hexdigest()
        if mac != data.get('mac'):
            return JsonResponse({'return_code': 0, 'return_message': 'Invalid mac'})
        
        # Update order status
        order = Order.objects.get(id=order_id)
        if data.get('return_code') == 1:
            order.payment_status = 'paid'
        else:
            order.payment_status = 'failed'
        order.save()
        
        return JsonResponse({'return_code': 1, 'return_message': 'Success'})
        
    except Exception as e:
        return JsonResponse({'return_code': 0, 'return_message': str(e)}) 