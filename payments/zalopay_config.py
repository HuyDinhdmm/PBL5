import os
from datetime import datetime

# ZaloPay configuration
ZALOPAY_APP_ID = "2554"  # Replace with your actual App ID
ZALOPAY_KEY1 = "sdngKKJmqEMzvh5QQcdD2A9XBSKUNaYn"  # Replace with your actual Key1
ZALOPAY_KEY2 = "trMrHtvjo6myautxDUiAcYsVtaeQ8nhf"  # Replace with your actual Key2
ZALOPAY_ENDPOINT = "https://sb-openapi.zalopay.vn/v2/create"

# Callback URL for ZaloPay
CALLBACK_URL = "http://localhost:8000/payments/zalopay/callback/"

# Timeout for payment (in minutes)
PAYMENT_TIMEOUT = 15

def get_timestamp():
    return int(datetime.now().timestamp() * 1000) 