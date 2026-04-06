from django.shortcuts import get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.conf import settings
from twilio.twiml.voice_response import VoiceResponse, Dial
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from .models import CallSession, UserProfile
from django.contrib.auth.models import User
from django.db import models
import json
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Initialize Twilio client with error handling
twilio_client = None
try:
    if hasattr(settings, 'TWILIO_ACCOUNT_SID') and settings.TWILIO_ACCOUNT_SID:
        if hasattr(settings, 'TWILIO_AUTH_TOKEN') and settings.TWILIO_AUTH_TOKEN:
            twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            logger.info("Twilio client initialized successfully")
        else:
            logger.warning("Twilio auth token not configured")
    else:
        logger.warning("Twilio account SID not configured")
except Exception as e:
    logger.error(f"Failed to initialize Twilio client: {e}")

@login_required
def initiate_call(request, username):
    """Initiate a call (browser-to-browser or browser-to-phone)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=400)
    
    try:
        receiver = get_object_or_404(User, username=username)
        receiver_profile = receiver.profile
        call_type = request.POST.get('call_type', 'browser')
        
        # Validate call type
        if call_type not in ['browser', 'phone']:
            return JsonResponse({'error': 'Invalid call type'}, status=400)
        
        # Check if receiver is available for calls
        if call_type == 'browser' and not receiver_profile.is_available_for_calls:
            return JsonResponse({'error': 'User is not available for browser calls'}, status=400)
        
        # For phone calls, check if receiver has a phone number
        if call_type == 'phone':
            if not receiver_profile.phone_number:
                return JsonResponse({'error': 'User has not set a phone number'}, status=400)
            if not receiver_profile.is_available_for_calls:
                return JsonResponse({'error': 'User is not available for phone calls'}, status=400)
        
        # Create call session
        call_session = CallSession.objects.create(
            caller=request.user,
            receiver=receiver,
            call_type=call_type,
            price_per_minute=receiver_profile.call_price_per_minute or 0,
            receiver_phone_number=receiver_profile.phone_number if call_type == 'phone' else None,
            status='pending'
        )
        
        if call_type == 'browser':
            # Browser-to-browser WebRTC call
            return JsonResponse({
                'success': True,
                'room_name': call_session.room_name,
                'call_id': call_session.id,
                'call_type': 'browser'
            })
        
        elif call_type == 'phone':
            # Check if Twilio client is available
            if twilio_client is None:
                call_session.status = 'failed'
                call_session.save()
                return JsonResponse({
                    'error': 'Twilio service is not configured. Please check your credentials.'
                }, status=500)
            
            # Browser-to-phone call via Twilio
            try:
                # Build the full URL for the webhook
                webhook_url = request.build_absolute_uri(f'/twilio/voice/{call_session.id}/')
                status_callback_url = request.build_absolute_uri('/twilio/status/')
                
                # Make the call via Twilio
                call = twilio_client.calls.create(
                    url=webhook_url,
                    to=receiver_profile.phone_number,
                    from_=settings.TWILIO_PHONE_NUMBER,
                    status_callback=status_callback_url,
                    status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
                    status_callback_method='POST'
                )
                
                call_session.twilio_call_sid = call.sid
                call_session.status = 'active'
                call_session.started_at = timezone.now()
                call_session.save()
                
                logger.info(f"Phone call initiated: {call.sid} to {receiver_profile.phone_number}")
                
                return JsonResponse({
                    'success': True,
                    'call_id': call_session.id,
                    'call_type': 'phone',
                    'call_sid': call.sid
                })
                
            except TwilioRestException as e:
                logger.error(f"Twilio error: {e}")
                call_session.status = 'failed'
                call_session.save()
                
                # Provide user-friendly error messages
                if e.code == 21211:
                    error_msg = "Invalid phone number format. Please use international format (e.g., +1234567890)"
                elif e.code == 21408:
                    error_msg = "Cannot call this number. Trial accounts can only call verified numbers."
                elif e.code == 21614:
                    error_msg = "Not enough credit to make the call. Please add funds to your Twilio account."
                elif e.code == 13223:
                    error_msg = "This phone number is not voice-capable. Please use a different number."
                else:
                    error_msg = f"Twilio error: {str(e)}"
                
                return JsonResponse({'error': error_msg}, status=500)
                
            except Exception as e:
                logger.error(f"Unexpected error during call initiation: {e}")
                call_session.status = 'failed'
                call_session.save()
                return JsonResponse({'error': f'Failed to initiate call: {str(e)}'}, status=500)
        
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        logger.error(f"Unexpected error in initiate_call: {e}")
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)


@csrf_exempt
def twilio_voice_webhook(request, call_id):
    """Twilio webhook for handling outgoing calls"""
    try:
        call_session = get_object_or_404(CallSession, id=call_id)
        response = VoiceResponse()
        
        # Say a message before connecting
        response.say(
            f"You are receiving a call from {call_session.caller.username} on MediaShare. Please wait while we connect you.",
            voice='alice'
        )
        
        # Connect the call
        dial = Dial(caller_id=settings.TWILIO_PHONE_NUMBER)
        dial.number(call_session.receiver_phone_number)
        response.append(dial)
        
        # If the call fails or is not answered
        response.say("The call could not be connected. Please try again later.", voice='alice')
        
        logger.info(f"Twilio webhook processed for call {call_id}")
        return HttpResponse(str(response), content_type='text/xml')
        
    except CallSession.DoesNotExist:
        logger.error(f"Call session not found: {call_id}")
        response = VoiceResponse()
        response.say("Invalid call session. Please try again.")
        return HttpResponse(str(response), content_type='text/xml')
    except Exception as e:
        logger.error(f"Error in twilio_voice_webhook: {e}")
        response = VoiceResponse()
        response.say("An error occurred. Please try again later.")
        return HttpResponse(str(response), content_type='text/xml')


@csrf_exempt
def twilio_status_callback(request):
    """Handle call status updates from Twilio"""
    if request.method != 'POST':
        return HttpResponse('OK')
    
    call_sid = request.POST.get('CallSid')
    call_status = request.POST.get('CallStatus')
    call_duration = request.POST.get('CallDuration', 0)
    
    logger.info(f"Twilio status callback: CallSid={call_sid}, Status={call_status}, Duration={call_duration}")
    
    # Find and update the call session
    try:
        call_session = CallSession.objects.get(twilio_call_sid=call_sid)
        
        if call_status == 'initiated':
            call_session.status = 'pending'
        elif call_status == 'ringing':
            call_session.status = 'pending'
        elif call_status == 'in-progress':
            call_session.status = 'active'
            if not call_session.started_at:
                call_session.started_at = timezone.now()
        elif call_status == 'completed':
            call_session.status = 'completed'
            call_session.ended_at = timezone.now()
            if call_duration:
                call_session.duration = int(call_duration)
            elif call_session.started_at:
                duration_seconds = (call_session.ended_at - call_session.started_at).total_seconds()
                call_session.duration = int(duration_seconds)
            # Calculate cost
            if call_session.duration > 0:
                minutes = call_session.duration / 60
                call_session.total_cost = minutes * call_session.price_per_minute
        elif call_status in ['busy', 'no-answer', 'canceled']:
            call_session.status = 'missed'
            call_session.ended_at = timezone.now()
        elif call_status == 'failed':
            call_session.status = 'failed'
            call_session.ended_at = timezone.now()
        
        call_session.twilio_status = call_status
        call_session.save()
        
        logger.info(f"Call session {call_session.id} updated to status {call_session.status}")
        
    except CallSession.DoesNotExist:
        logger.warning(f"Call session not found for Twilio SID: {call_sid}")
    except Exception as e:
        logger.error(f"Error updating call session: {e}")
    
    return HttpResponse('OK')


@login_required
def generate_twilio_token(request):
    """Generate Twilio access token for browser client"""
    try:
        # Check if twilio-jwt is installed
        try:
            from twilio.jwt.access_token import AccessToken
            from twilio.jwt.access_token.grants import VoiceGrant
        except ImportError:
            logger.error("twilio-jwt module not installed")
            return JsonResponse({'error': 'Twilio JWT module not available. Run: pip install twilio'}, status=500)
        
        # Check if required settings are configured
        required_settings = {
            'TWILIO_ACCOUNT_SID': getattr(settings, 'TWILIO_ACCOUNT_SID', None),
            'TWILIO_API_KEY_SID': getattr(settings, 'TWILIO_API_KEY_SID', None),
            'TWILIO_API_KEY_SECRET': getattr(settings, 'TWILIO_API_KEY_SECRET', None),
            'TWILIO_TWIML_APP_SID': getattr(settings, 'TWILIO_TWIML_APP_SID', None)
        }
        
        missing_settings = [s for s, v in required_settings.items() if not v]
        
        if missing_settings:
            logger.error(f"Missing Twilio settings: {missing_settings}")
            return JsonResponse({
                'error': f'Twilio not properly configured. Missing: {", ".join(missing_settings)}'
            }, status=500)
        
        # Create access token
        token = AccessToken(
            required_settings['TWILIO_ACCOUNT_SID'],
            required_settings['TWILIO_API_KEY_SID'],
            required_settings['TWILIO_API_KEY_SECRET'],
            identity=str(request.user.id)
        )
        
        # Create Voice grant
        voice_grant = VoiceGrant(
            outgoing_application_sid=required_settings['TWILIO_TWIML_APP_SID'],
            incoming_allow=True
        )
        token.add_grant(voice_grant)
        
        logger.info(f"Twilio token generated for user {request.user.id}")
        return JsonResponse({'token': token.to_jwt()})
        
    except Exception as e:
        logger.error(f"Error generating Twilio token: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def call_history(request):
    """Get call history for the logged-in user"""
    try:
        # Get calls where user is either caller or receiver
        calls = CallSession.objects.filter(
            models.Q(caller=request.user) | models.Q(receiver=request.user)
        ).order_by('-created_at')[:50]
        
        call_list = []
        for call in calls:
            call_list.append({
                'id': call.id,
                'with_user': call.receiver.username if call.caller == request.user else call.caller.username,
                'direction': 'outgoing' if call.caller == request.user else 'incoming',
                'call_type': call.get_call_type_display(),
                'status': call.get_status_display(),
                'duration': call.formatted_duration,
                'total_cost': f"${call.total_cost:.2f}" if call.total_cost else "$0.00",
                'created_at': call.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            })
        
        return JsonResponse({'success': True, 'calls': call_list, 'count': len(call_list)})
        
    except Exception as e:
        logger.error(f"Error fetching call history: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def end_call(request, call_id):
    """End an active call session"""
    try:
        call_session = get_object_or_404(CallSession, id=call_id)
        
        # Check if user is a participant
        if request.user not in [call_session.caller, call_session.receiver]:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
        
        # For phone calls, try to end via Twilio
        if call_session.call_type == 'phone' and call_session.twilio_call_sid and twilio_client:
            try:
                call = twilio_client.calls(call_session.twilio_call_sid).update(status='completed')
                logger.info(f"Call {call_session.twilio_call_sid} ended via Twilio")
            except Exception as e:
                logger.error(f"Error ending call via Twilio: {e}")
        
        # Update call session
        call_session.status = 'completed'
        call_session.ended_at = timezone.now()
        
        if call_session.started_at:
            duration_seconds = (call_session.ended_at - call_session.started_at).total_seconds()
            call_session.duration = int(duration_seconds)
            # Calculate cost
            if call_session.duration > 0:
                minutes = call_session.duration / 60
                call_session.total_cost = minutes * call_session.price_per_minute
        
        call_session.save()
        
        logger.info(f"Call {call_id} ended by {request.user.username}")
        return JsonResponse({'success': True})
        
    except CallSession.DoesNotExist:
        return JsonResponse({'error': 'Call session not found'}, status=404)
    except Exception as e:
        logger.error(f"Error ending call: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def call_settings(request):
    """Get or update user's call settings"""
    if request.method == 'GET':
        try:
            profile = request.user.profile
            return JsonResponse({
                'success': True,
                'settings': {
                    'is_available_for_calls': profile.is_available_for_calls,
                    'call_price_per_minute': float(profile.call_price_per_minute),
                    'phone_number': profile.phone_number or '',
                    'has_phone_number': bool(profile.phone_number),
                }
            })
        except Exception as e:
            logger.error(f"Error fetching call settings: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            profile = request.user.profile
            
            if 'is_available_for_calls' in data:
                profile.is_available_for_calls = data['is_available_for_calls']
            if 'call_price_per_minute' in data:
                profile.call_price_per_minute = float(data['call_price_per_minute'])
            if 'phone_number' in data:
                profile.phone_number = data['phone_number']
            
            profile.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Call settings updated successfully'
            })
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            logger.error(f"Error updating call settings: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)