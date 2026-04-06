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
    threads = MessageThread.objects.filter(participants=request.user).prefetch_related('participants', 'messages')
    
    # Prepare thread data with unread counts
    threads_data = []
    for thread in threads:
        # Get other participant
        other_participant = None
        for participant in thread.participants.all():
            if participant != request.user:
                other_participant = participant
                break
        
        # Get unread count for this thread
        unread_count = Message.objects.filter(
            thread=thread, 
            is_read=False
        ).exclude(sender=request.user).count()
        
        # Get last message
        last_message = thread.messages.first()
        
        threads_data.append({
            'thread': thread,
            'other_user': other_participant,
            'unread_count': unread_count,
            'last_message': last_message,
            'updated_at': thread.updated_at,
            'subject': thread.subject,
        })
    
    # Sort by updated_at (most recent first)
    threads_data.sort(key=lambda x: x['updated_at'], reverse=True)
    
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
    """Send a message via AJAX (handles both new threads and replies)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    # Try to get data from both POST and JSON
    if request.content_type == 'application/json':
        data = json.loads(request.body)
        thread_id = data.get('thread_id')
        username = data.get('username')
        subject = data.get('subject')
        content = data.get('content')
    else:
        thread_id = request.POST.get('thread_id')
        username = request.POST.get('username')
        subject = request.POST.get('subject')
        content = request.POST.get('content')
    
    if not content:
        return JsonResponse({'error': 'Message content is required'}, status=400)
    
    try:
        # If thread_id is provided, reply to existing thread
        if thread_id:
            thread = get_object_or_404(MessageThread, id=thread_id)
            
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
        
        # Update thread timestamp
        thread.save()
        
        return JsonResponse({
            'success': True,
            'thread_id': thread.id,
            'message': {
                'id': message.id,
                'content': message.content,
                'sender': request.user.username,
                'time': message.created_at.strftime('%I:%M %p'),
                'timestamp': message.created_at.isoformat()
            }
        })
        
    except MessageThread.DoesNotExist:
        return JsonResponse({'error': 'Thread not found'}, status=404)
    except Exception as e:
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
        messages_data.append({
            'id': message.id,
            'content': message.content,
            'sender': message.sender.username,
            'time': message.created_at.strftime('%I:%M %p'),
            'timestamp': message.created_at.isoformat()
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