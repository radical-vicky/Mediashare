import requests
import base64
import json
from datetime import datetime
from django.conf import settings
from .models import MpesaTransaction

def get_access_token():
    """Get M-PESA access token"""
    api_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    
    if settings.MPESA_ENVIRONMENT == 'production':
        api_url = "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    
    response = requests.get(
        api_url,
        auth=requests.auth.HTTPBasicAuth(settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET)
    )
    
    if response.status_code == 200:
        return response.json().get('access_token')
    return None

def format_phone_number(phone_number):
    """Format phone number to 254XXXXXXXXX format"""
    # Remove any non-digit characters
    phone = ''.join(filter(str.isdigit, phone_number))
    
    # If starts with 0, replace with 254
    if phone.startswith('0'):
        phone = '254' + phone[1:]
    # If starts with 254, keep as is
    elif phone.startswith('254'):
        phone = phone
    # If starts with +254, remove +
    elif phone.startswith('+254'):
        phone = phone[1:]
    
    return phone

def initiate_stk_push(phone_number, amount, account_reference, transaction_desc, user, transaction_type, content_id=None, content_type=None):
    """Initiate M-PESA STK Push"""
    access_token = get_access_token()
    if not access_token:
        return {'success': False, 'error': 'Failed to get access token'}
    
    # Format phone number
    formatted_phone = format_phone_number(phone_number)
    
    # Generate timestamp
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    
    # Generate password
    password_str = f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}"
    password = base64.b64encode(password_str.encode()).decode('utf-8')
    
    # API URL
    api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    if settings.MPESA_ENVIRONMENT == 'production':
        api_url = "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    
    # Request payload
    payload = {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline" if settings.MPESA_SHORTCODE_TYPE == 'paybill' else "CustomerBuyGoodsOnline",
        "Amount": int(amount),
        "PartyA": formatted_phone,
        "PartyB": settings.MPESA_SHORTCODE,
        "PhoneNumber": formatted_phone,
        "CallBackURL": settings.MPESA_CALLBACK_URL,
        "AccountReference": account_reference[:12],  # Max 12 characters
        "TransactionDesc": transaction_desc[:13]  # Max 13 characters
    }
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.post(api_url, json=payload, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        
        # Save transaction
        transaction = MpesaTransaction.objects.create(
            user=user,
            transaction_type=transaction_type,
            amount=amount,
            phone_number=formatted_phone,
            reference_id=result.get('CheckoutRequestID'),
            merchant_request_id=result.get('MerchantRequestID'),
            content_id=content_id,
            content_type=content_type,
            status='pending'
        )
        
        return {
            'success': True,
            'checkout_request_id': result.get('CheckoutRequestID'),
            'transaction_id': transaction.id,
            'response_code': result.get('ResponseCode'),
            'response_desc': result.get('ResponseDescription')
        }
    else:
        return {'success': False, 'error': 'STK Push failed', 'response': response.text}