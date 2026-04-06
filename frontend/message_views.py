from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.models import User
from .models import MessageThread, Message, UserProfile
from django.utils import timezone
from django.db.models import Count, Q
import json

@login_required
def inbox(request):
    """Display user's message threads"""
    import logging
    logger = logging.getLogger(__name__)
    
    # Get all threads where user is a participant
    threads = MessageThread.objects.filter(participants=request.user).order_by('-updated_at')
    
    logger.info(f"Found {threads.count()} threads for user {request.user.username}")
    
    threads_data = []
    for thread in threads:
        logger.info(f"Processing thread {thread.id}: {thread.subject}")
        
        # Get the other participant
        other_user = None
        for participant in thread.participants.all():
            logger.info(f"Participant: {participant.username}")
            if participant != request.user:
                other_user = participant
                break
        
        if other_user:
            # Get unread count
            unread_count = Message.objects.filter(
                thread=thread, 
                is_read=False
            ).exclude(sender=request.user).count()
            
            # Get last message
            last_message = thread.messages.first()
            
            threads_data.append({
                'thread': thread,
                'other_user': other_user,
                'unread_count': unread_count,
                'last_message': last_message,
                'updated_at': thread.updated_at,
                'subject': thread.subject,
            })
            logger.info(f"Added thread with user: {other_user.username}")
        else:
            logger.warning(f"No other user found for thread {thread.id}")
    
    logger.info(f"Final threads_data count: {len(threads_data)}")
    
    context = {
        'threads_data': threads_data,
    }
    return render(request, 'frontend/messages/inbox.html', context)

@login_required
def thread_detail(request, thread_id):
    """Display a specific message thread"""
    thread = get_object_or_404(MessageThread, id=thread_id)
    
    # Check if user is a participant
    if request.user not in thread.participants.all():
        messages.error(request, 'You do not have access to this conversation.')
        return redirect('frontend:inbox')
    
    # Mark all messages as read
    Message.objects.filter(thread=thread, is_read=False).exclude(sender=request.user).update(is_read=True)
    
    # Get all messages
    messages_list = thread.messages.select_related('sender').all()
    
    # Get the other participant
    other_participant = None
    for participant in thread.participants.all():
        if participant != request.user:
            other_participant = participant
            break
    
    context = {
        'thread': thread,
        'messages': messages_list,
        'other_user': other_participant,
    }
    return render(request, 'frontend/messages/thread_detail.html', context)

@login_required
def new_message(request, username=None):
    """Start a new message thread"""
    if request.method == 'POST':
        recipient_username = request.POST.get('username')
        subject = request.POST.get('subject')
        content = request.POST.get('content')
        
        if not recipient_username or not subject or not content:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': 'All fields are required'}, status=400)
            messages.error(request, 'All fields are required')
            return redirect('frontend:inbox')
        
        try:
            recipient = User.objects.get(username=recipient_username)
            
            # Don't allow messaging yourself
            if recipient == request.user:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'error': 'You cannot message yourself'}, status=400)
                messages.error(request, 'You cannot message yourself')
                return redirect('frontend:inbox')
            
            # Create or get existing thread
            thread = MessageThread.objects.filter(
                participants=request.user
            ).filter(
                participants=recipient
            ).first()
            
            if not thread:
                thread = MessageThread.objects.create(subject=subject)
                thread.participants.add(request.user, recipient)
            
            # Create message
            message = Message.objects.create(
                thread=thread,
                sender=request.user,
                content=content
            )
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'thread_id': thread.id})
            
            messages.success(request, 'Message sent!')
            return redirect('frontend:thread_detail', thread_id=thread.id)
            
        except User.DoesNotExist:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': 'User not found'}, status=404)
            messages.error(request, 'User not found')
            return redirect('frontend:inbox')
    
    # GET request
    context = {
        'username': username,
    }
    return render(request, 'frontend/messages/new_message.html', context)

@login_required
def send_ajax_message(request):
    """Send a message via AJAX (handles both new threads and replies) with file support - NO SIZE LIMITS"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    # Get data from POST (supports files)
    thread_id = request.POST.get('thread_id')
    username = request.POST.get('username')
    subject = request.POST.get('subject')
    content = request.POST.get('content', '')
    file = request.FILES.get('file')
    file_type = request.POST.get('file_type')
    
    if not content and not file:
        return JsonResponse({'error': 'Message content or file is required'}, status=400)
    
    try:
        # If thread_id is provided, reply to existing thread
        if thread_id and thread_id != 'null' and thread_id != 'undefined':
            thread = get_object_or_404(MessageThread, id=int(thread_id))
            
            # Check if user is a participant
            if request.user not in thread.participants.all():
                return JsonResponse({'error': 'Unauthorized'}, status=403)
        else:
            # Create new thread
            if not username or not subject:
                return JsonResponse({'error': 'Username and subject are required for new threads'}, status=400)
            
            try:
                recipient = User.objects.get(username=username)
            except User.DoesNotExist:
                return JsonResponse({'error': 'User not found'}, status=404)
            
            # Don't allow messaging yourself
            if recipient == request.user:
                return JsonResponse({'error': 'You cannot message yourself'}, status=400)
            
            # Check if thread already exists
            thread = MessageThread.objects.filter(
                participants=request.user
            ).filter(
                participants=recipient
            ).first()
            
            if not thread:
                thread = MessageThread.objects.create(subject=subject)
                thread.participants.add(request.user, recipient)
        
        # Create message
        message = Message.objects.create(
            thread=thread,
            sender=request.user,
            content=content
        )
        
        # Handle file upload - NO SIZE LIMIT
        file_info = None
        if file:
            # Determine file type from extension or content type
            file_ext = file.name.split('.')[-1].lower()
            if file_type:
                detected_type = file_type
            elif file.content_type and file.content_type.startswith('image/'):
                detected_type = 'image'
            elif file.content_type and file.content_type.startswith('video/'):
                detected_type = 'video'
            elif file.content_type and file.content_type.startswith('audio/'):
                detected_type = 'audio' if 'voice' not in file.name.lower() else 'voice'
            else:
                detected_type = 'document'
            
            message.file = file
            message.file_type = detected_type
            message.file_name = file.name
            message.file_size = file.size
            message.save()
            
            file_info = {
                'url': message.file.url,
                'type': detected_type,
                'name': message.file_name,
                'size': message.file_size_display if hasattr(message, 'file_size_display') else f"{file.size} bytes",
                'file_type_display': message.get_file_type_display() if hasattr(message, 'get_file_type_display') else detected_type
            }
        
        # Update thread timestamp
        thread.save()
        
        response_data = {
            'success': True,
            'thread_id': thread.id,
            'message': {
                'id': message.id,
                'content': message.content,
                'sender': request.user.username,
                'time': message.created_at.strftime('%I:%M %p'),
                'timestamp': message.created_at.isoformat(),
                'file': file_info
            }
        }
        
        return JsonResponse(response_data)
        
    except MessageThread.DoesNotExist:
        return JsonResponse({'error': 'Thread not found'}, status=404)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def get_unread_count(request):
    """Get unread message count for the current user"""
    threads = MessageThread.objects.filter(participants=request.user)
    unread_count = 0
    
    for thread in threads:
        unread_count += Message.objects.filter(thread=thread, is_read=False).exclude(sender=request.user).count()
    
    return JsonResponse({'unread_count': unread_count})

@login_required
def delete_thread(request, thread_id):
    """Delete a message thread"""
    thread = get_object_or_404(MessageThread, id=thread_id)
    
    # Check if user is a participant
    if request.user not in thread.participants.all():
        messages.error(request, 'You do not have access to this conversation.')
        return redirect('frontend:inbox')
    
    # Remove user from participants instead of deleting the thread
    thread.participants.remove(request.user)
    
    # If no participants left, delete the thread
    if thread.participants.count() == 0:
        thread.delete()
    
    messages.success(request, 'Conversation deleted successfully.')
    return redirect('frontend:inbox')

@login_required
def delete_message(request, message_id):
    """Delete a single message (only the sender can delete)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    # Get the message
    message = get_object_or_404(Message, id=message_id)
    
    # Check if user is the sender
    if message.sender != request.user:
        return JsonResponse({'error': 'You can only delete your own messages'}, status=403)
    
    # Store thread ID before deleting
    thread_id = message.thread.id
    
    # Delete the message
    message.delete()
    
    # Return JSON response for AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'thread_id': thread_id})
    
    # For non-AJAX requests
    messages.success(request, 'Message deleted successfully')
    return redirect('frontend:thread_detail', thread_id=thread_id)

@login_required
def edit_message(request, message_id):
    """Edit a message (only if not read by receiver)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    # Get the message
    message = get_object_or_404(Message, id=message_id)
    
    # Check if user is the sender
    if message.sender != request.user:
        return JsonResponse({'error': 'You can only edit your own messages'}, status=403)
    
    # Check if message has been read
    if message.is_read:
        return JsonResponse({'error': 'Message has already been read and cannot be edited'}, status=400)
    
    # Get new content
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            new_content = data.get('content', '').strip()
        else:
            new_content = request.POST.get('content', '').strip()
    except:
        new_content = request.POST.get('content', '').strip()
    
    if not new_content:
        return JsonResponse({'error': 'Message content cannot be empty'}, status=400)
    
    # Update the message
    old_content = message.content
    message.content = new_content
    message.edited = True
    message.edited_at = timezone.now()
    message.save()
    
    # Return JSON response for AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True, 
            'message_id': message.id,
            'new_content': new_content,
            'edited_at': message.edited_at.strftime('%I:%M %p'),
            'old_content': old_content
        })
    
    messages.success(request, 'Message edited successfully')
    return redirect('frontend:thread_detail', thread_id=message.thread.id)

@login_required
def get_thread_messages(request, thread_id):
    """Get new messages for a thread via AJAX polling"""
    thread = get_object_or_404(MessageThread, id=thread_id)
    
    # Check if user is a participant
    if request.user not in thread.participants.all():
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    last_id = request.GET.get('last_id', 0)
    
    messages_list = thread.messages.filter(id__gt=last_id).select_related('sender')
    
    messages_data = []
    for message in messages_list:
        file_info = None
        if message.file:
            file_info = {
                'url': message.file.url,
                'type': message.file_type,
                'name': message.file_name,
                'size': message.file_size_display,
                'file_type_display': message.get_file_type_display()
            }
        
        messages_data.append({
            'id': message.id,
            'content': message.content,
            'sender': message.sender.username,
            'time': message.created_at.strftime('%I:%M %p'),
            'timestamp': message.created_at.isoformat(),
            'is_read': message.is_read,
            'edited': message.edited,
            'edited_at': message.edited_at.strftime('%I:%M %p') if message.edited_at else None,
            'file': file_info
        })
    
    return JsonResponse({'messages': messages_data})

@login_required
def mark_thread_read(request, thread_id):
    """Mark all messages in a thread as read"""
    thread = get_object_or_404(MessageThread, id=thread_id)
    if request.user in thread.participants.all():
        Message.objects.filter(thread=thread, is_read=False).exclude(sender=request.user).update(is_read=True)
    return JsonResponse({'success': True})

@login_required
def typing_indicator(request, thread_id):
    """Handle typing indicator (store in cache)"""
    # You can implement this with Redis or cache
    return JsonResponse({'success': True})