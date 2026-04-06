from .models import MessageThread, Message

def unread_messages_count(request):
    """Add unread message count to all templates"""
    unread_count = 0
    if request.user.is_authenticated:
        threads = MessageThread.objects.filter(participants=request.user)
        for thread in threads:
            unread_count += Message.objects.filter(
                thread=thread, 
                is_read=False
            ).exclude(sender=request.user).count()
    return {'unread_thread_count': unread_count}