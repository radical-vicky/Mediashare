from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.template.loader import render_to_string
from .models import Photo, Video, Comment, UserProfile, CallSession, Share, VideoView
from django.contrib.auth.models import User
import os
import re
import json

def home(request):
    """Home page - landing page"""
    recent_photos = Photo.objects.select_related('author').all()[:8]
    recent_videos = Video.objects.select_related('author').all()[:8]
    
    context = {
        'recent_photos': recent_photos,
        'recent_videos': recent_videos,
    }
    return render(request, 'frontend/home.html', context)

def feed(request):
    """Main feed page showing photos and videos"""
    content_filter = request.GET.get('filter', 'all')
    
    photos = Photo.objects.select_related('author').all()
    videos = Video.objects.select_related('author').all()
    
    if content_filter == 'photos':
        videos = Video.objects.none()
    elif content_filter == 'videos':
        photos = Photo.objects.none()
    
    photos_paginator = Paginator(photos, 9)
    videos_paginator = Paginator(videos, 6)
    
    photos_page = request.GET.get('photos_page', 1)
    videos_page = request.GET.get('videos_page', 1)
    
    context = {
        'photos': photos_paginator.get_page(photos_page),
        'videos': videos_paginator.get_page(videos_page),
        'current_filter': content_filter,
    }
    return render(request, 'frontend/feed.html', context)

def photo_detail(request, photo_id):
    """View photo details with proper error handling"""
    try:
        photo = get_object_or_404(Photo, id=photo_id)
    except Http404:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Photo not found'}, status=404)
        
        context = {
            'error_message': 'The photo you are looking for does not exist or has been removed.',
            'photo_id': photo_id,
            'suggestions': Photo.objects.select_related('author').all()[:8]
        }
        return render(request, 'frontend/photo_not_found.html', context, status=404)
    
    if photo.image and not os.path.exists(photo.image.path):
        messages.warning(request, 'This photo file is missing. It may have been removed from the server.')
    
    if not request.session.get(f'viewed_photo_{photo_id}'):
        photo.views += 1
        photo.save()
        request.session[f'viewed_photo_{photo_id}'] = True
    
    # Get related photos
    related_photos = Photo.objects.filter(author=photo.author).exclude(id=photo_id)[:4]
    if not related_photos:
        related_photos = Photo.objects.exclude(id=photo_id).order_by('-views')[:4]
    
    # Get ALL photos for carousel (this is the key fix)
    all_photos = Photo.objects.filter(image__isnull=False).order_by('-created_at')
    
    context = {
        'photo': photo,
        'related_photos': related_photos,
        'all_photos': all_photos,  # This must be here!
    }
    return render(request, 'frontend/photo_detail.html', context)


# Add this to your views.py

@login_required
def track_video_view(request, video_id):
    """Track video view with watch time and completion status"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        video = get_object_or_404(Video, id=video_id)
    except Http404:
        return JsonResponse({'error': 'Video not found'}, status=404)
    
    # Get session key
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key
    
    # Parse request body
    try:
        data = json.loads(request.body)
        watch_time = data.get('watch_time', 0)
        completed = data.get('completed', False)
    except json.JSONDecodeError:
        watch_time = 0
        completed = False
    
    # Check if already viewed in this session
    existing_view = VideoView.objects.filter(
        video=video,
        session_key=session_key
    ).first()
    
    if existing_view:
        # Update existing view with watch time
        existing_view.watch_time = max(existing_view.watch_time, watch_time)
        existing_view.completed = completed or existing_view.completed
        existing_view.save()
        view_tracked = False
    else:
        # Create new view record
        VideoView.objects.create(
            video=video,
            user=request.user if request.user.is_authenticated else None,
            session_key=session_key,
            ip_address=get_client_ip(request),
            watch_time=watch_time,
            completed=completed
        )
        view_tracked = True
    
    # Update video's total unique view count
    unique_views = VideoView.objects.filter(video=video).values('session_key').distinct().count()
    video.view_count = unique_views
    video.save()
    
    return JsonResponse({
        'success': True,
        'view_tracked': view_tracked,
        'view_count': unique_views,
        'watch_time': watch_time
    })


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def video_detail(request, video_id):
    """View video details with proper error handling"""
    try:
        video = get_object_or_404(Video, id=video_id)
    except Http404:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Video not found'}, status=404)
        
        context = {
            'error_message': 'The video you are looking for does not exist or has been removed.',
            'video_id': video_id,
            'suggestions': Video.objects.select_related('author').all()[:8]
        }
        return render(request, 'frontend/video_not_found.html', context, status=404)
    
    if video.video_file and not os.path.exists(video.video_file.path):
        messages.warning(request, 'This video file is missing. It may have been removed from the server.')
    
    # Get unique view count from database
    unique_views = VideoView.objects.filter(video=video).values('session_key').distinct().count()
    video.view_count = unique_views
    video.save()
    
    # Get related videos
    related_videos = Video.objects.filter(author=video.author).exclude(id=video_id)[:4]
    if not related_videos:
        related_videos = Video.objects.exclude(id=video_id).order_by('-views')[:4]
    
    # Get next video (newer videos first)
    next_video = Video.objects.filter(created_at__gt=video.created_at).order_by('created_at').first()
    
    # If no newer video, get the oldest video as next (loop)
    if not next_video:
        next_video = Video.objects.exclude(id=video_id).order_by('created_at').first()
    
    # Also get previous video for optional previous button
    prev_video = Video.objects.filter(created_at__lt=video.created_at).order_by('-created_at').first()
    
    context = {
        'video': video,
        'related_videos': related_videos,
        'unique_views': unique_views,
        'next_video': next_video,  # This is required for the next button
        'prev_video': prev_video,  # Optional for previous button
    }
    return render(request, 'frontend/video_detail.html', context)

def user_profile(request, username):
    """View user profile"""
    try:
        profile_user = get_object_or_404(User, username=username)
    except Http404:
        context = {
            'error_message': f'User "{username}" does not exist.',
            'username': username
        }
        return render(request, 'frontend/user_not_found.html', context, status=404)
    
    profile, created = UserProfile.objects.get_or_create(user=profile_user)
    
    photos = Photo.objects.filter(author=profile_user)
    videos = Video.objects.filter(author=profile_user)
    
    is_following = False
    if request.user.is_authenticated:
        is_following = profile.followers.filter(id=request.user.id).exists()
    
    context = {
        'profile_user': profile_user,
        'profile': profile,
        'photos': photos[:6],
        'videos': videos[:6],
        'total_photos': photos.count(),
        'total_videos': videos.count(),
        'is_following': is_following,
    }
    return render(request, 'frontend/user_profile.html', context)

@login_required
def edit_profile(request):
    """Edit user profile"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        profile.bio = request.POST.get('bio', '')
        profile.location = request.POST.get('location', '')
        profile.website = request.POST.get('website', '')
        profile.phone_number = request.POST.get('phone_number', '')
        profile.call_price_per_minute = request.POST.get('call_price_per_minute', 0)
        profile.is_available_for_calls = request.POST.get('is_available_for_calls') == 'on'
        
        if request.FILES.get('avatar'):
            profile.avatar = request.FILES['avatar']
        
        profile.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('frontend:user_profile', username=request.user.username)
    
    return render(request, 'frontend/edit_profile.html', {'profile': profile})

@login_required
def follow_user(request, username):
    """Follow/unfollow a user"""
    try:
        user_to_follow = get_object_or_404(User, username=username)
    except Http404:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'User not found'}, status=404)
        messages.error(request, 'User not found.')
        return redirect('frontend:feed')
    
    profile, created = UserProfile.objects.get_or_create(user=user_to_follow)
    
    if request.user in profile.followers.all():
        profile.followers.remove(request.user)
        followed = False
    else:
        profile.followers.add(request.user)
        followed = True
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'followed': followed,
            'count': profile.followers.count()
        })
    
    return redirect('frontend:user_profile', username=username)

@login_required
def download_media(request, media_type, media_id):
    """Download photo or video with error handling"""
    try:
        if media_type == 'photo':
            media = get_object_or_404(Photo, id=media_id)
            if not os.path.exists(media.image.path):
                messages.error(request, 'Photo file not found on server.')
                return redirect('frontend:feed')
            file_path = media.image.path
            filename = f"{media.author.username}_photo_{media_id}.jpg"
        elif media_type == 'video':
            media = get_object_or_404(Video, id=media_id)
            if not os.path.exists(media.video_file.path):
                messages.error(request, 'Video file not found on server.')
                return redirect('frontend:feed')
            file_path = media.video_file.path
            filename = f"{media.author.username}_video_{media_id}.mp4"
        else:
            return JsonResponse({'error': 'Invalid media type'}, status=400)
        
        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
    except Http404:
        messages.error(request, f'{media_type.capitalize()} not found.')
        return redirect('frontend:feed')
    except Exception as e:
        messages.error(request, f'Error downloading file: {str(e)}')
        return redirect('frontend:feed')

@login_required
def share_media(request, media_type, media_id):
    """Track share analytics when user shares media on social platforms"""
    if request.method == 'POST':
        platform = request.POST.get('platform')
        
        if not platform:
            return JsonResponse({'error': 'Platform not specified'}, status=400)
        
        media_exists = False
        if media_type == 'photo':
            media_exists = Photo.objects.filter(id=media_id).exists()
        elif media_type == 'video':
            media_exists = Video.objects.filter(id=media_id).exists()
        
        share = Share.objects.create(
            user=request.user,
            content_type=media_type,
            platform=platform
        )
        
        if media_type == 'photo' and media_exists:
            share.photo_id = media_id
        elif media_type == 'video' and media_exists:
            share.video_id = media_id
        
        share.save()
        
        base_url = request.build_absolute_uri('/').rstrip('/')
        if media_type == 'photo':
            media_url = f"{base_url}/photo/{media_id}/"
        else:
            media_url = f"{base_url}/video/{media_id}/"
        
        share_urls = {
            'facebook': f"https://www.facebook.com/sharer/sharer.php?u={media_url}",
            'twitter': f"https://twitter.com/intent/tweet?url={media_url}&text=Check%20out%20this%20photo%20on%20MediaShare",
            'whatsapp': f"https://wa.me/?text=Check%20out%20this%20photo%20on%20MediaShare%20{media_url}",
            'telegram': f"https://t.me/share/url?url={media_url}&text=Check%20out%20this%20photo",
            'linkedin': f"https://www.linkedin.com/sharing/share-offsite/?url={media_url}",
            'pinterest': f"https://pinterest.com/pin/create/button/?url={media_url}&media={media_url}&description=Check%20out%20this%20photo",
            'reddit': f"https://reddit.com/submit?url={media_url}&title=Check%20out%20this%20photo",
            'instagram': f"instagram://library?assetType=photo",
        }
        
        return JsonResponse({
            'success': True, 
            'share_url': share_urls.get(platform, media_url),
            'media_url': media_url,
            'platform': platform
        })
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)

@login_required
def init_call(request, username):
    """Initialize a video/audio call"""
    try:
        receiver = get_object_or_404(User, username=username)
    except Http404:
        messages.error(request, 'User not found.')
        return redirect('frontend:feed')
    
    receiver_profile, created = UserProfile.objects.get_or_create(user=receiver)
    
    if request.method == 'POST':
        call_type = request.POST.get('call_type', 'video')
        
        if not receiver_profile.is_available_for_calls:
            return JsonResponse({'error': 'User is not available for calls'}, status=400)
        
        call_session = CallSession.objects.create(
            caller=request.user,
            receiver=receiver,
            call_type=call_type,
            price_per_minute=receiver_profile.call_price_per_minute
        )
        
        return JsonResponse({
            'success': True,
            'room_name': call_session.room_name,
            'call_id': call_session.id
        })
    
    context = {
        'receiver': receiver,
        'receiver_profile': receiver_profile,
    }
    return render(request, 'frontend/init_call.html', context)

@login_required
def call_room(request, room_name):
    """Video call room"""
    try:
        call_session = get_object_or_404(CallSession, room_name=room_name)
    except Http404:
        messages.error(request, 'Call session not found.')
        return redirect('frontend:feed')
    
    if request.user not in [call_session.caller, call_session.receiver]:
        messages.error(request, 'You are not authorized to join this call')
        return redirect('frontend:feed')
    
    context = {
        'room_name': room_name,
        'call_session': call_session,
        'caller': call_session.caller,
        'receiver': call_session.receiver,
    }
    return render(request, 'frontend/call_room.html', context)

@login_required
def end_call(request, call_id):
    """End a call session"""
    try:
        call_session = get_object_or_404(CallSession, id=call_id)
    except Http404:
        return JsonResponse({'error': 'Call session not found'}, status=404)
    
    if request.user not in [call_session.caller, call_session.receiver]:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    call_session.status = 'completed'
    call_session.ended_at = timezone.now()
    
    if call_session.started_at:
        duration_seconds = (call_session.ended_at - call_session.started_at).total_seconds()
        call_session.duration = int(duration_seconds)
        call_session.total_cost = (duration_seconds / 60) * call_session.price_per_minute
    
    call_session.save()
    
    return JsonResponse({'success': True})

@login_required
def upload_photo(request):
    """Upload a new photo"""
    if request.method == 'POST':
        if request.FILES.get('image'):
            image_file = request.FILES['image']
            
            if image_file.size > 50 * 1024 * 1024:
                messages.error(request, 'File size too large. Maximum size is 50MB.')
                return render(request, 'frontend/upload_photo.html')
            
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
            ext = os.path.splitext(image_file.name)[1].lower()
            if ext not in valid_extensions:
                messages.error(request, 'Invalid file type. Please upload an image file (JPG, PNG, GIF, WEBP, BMP).')
                return render(request, 'frontend/upload_photo.html')
            
            original_name = image_file.name
            name, ext = os.path.splitext(original_name)
            clean_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', name)
            clean_name = clean_name[:100]
            image_file.name = f"{clean_name}{ext}"
            
            photo = Photo.objects.create(
                author=request.user,
                image=image_file,
                caption=request.POST.get('caption', '')
            )
            messages.success(request, 'Your photo has been uploaded successfully!')
            return redirect('frontend:photo_detail', photo_id=photo.id)
        else:
            messages.error(request, 'Please select an image file.')
    
    return render(request, 'frontend/upload_photo.html')

@login_required
def upload_video(request):
    """Upload a new video - NO SIZE LIMITS, ANY FORMAT"""
    if request.method == 'POST':
        if request.FILES.get('video_file'):
            video_file = request.FILES['video_file']
            
            # Remove size limit check
            # if video_file.size > 500 * 1024 * 1024:
            #     messages.error(request, 'File size too large. Maximum size is 500MB.')
            #     return render(request, 'frontend/upload_video.html')
            
            # Allow ANY video format - remove extension validation
            # valid_extensions = ['.mp4', '.webm', '.mov', '.avi', '.mkv']
            # ext = os.path.splitext(video_file.name)[1].lower()
            # if ext not in valid_extensions:
            #     messages.error(request, 'Invalid file type. Please upload a video file (MP4, WebM, MOV, AVI, MKV).')
            #     return render(request, 'frontend/upload_video.html')
            
            # Keep original filename for better compatibility
            original_name = video_file.name
            name, ext = os.path.splitext(original_name)
            clean_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', name)
            clean_name = clean_name[:100]
            video_file.name = f"{clean_name}{ext}"
            
            # Create video record
            video = Video.objects.create(
                author=request.user,
                video_file=video_file,
                title=request.POST.get('title', ''),
                description=request.POST.get('description', '')
            )
            
            messages.success(request, 'Your video has been uploaded successfully!')
            return redirect('frontend:video_detail', video_id=video.id)
        else:
            messages.error(request, 'Please select a video file.')
    
    return render(request, 'frontend/upload_video.html')

@login_required
def like_photo(request, photo_id):
    """Like/unlike a photo"""
    try:
        photo = get_object_or_404(Photo, id=photo_id)
    except Http404:
        return JsonResponse({'error': 'Photo not found'}, status=404)
    
    if request.user in photo.likes.all():
        photo.likes.remove(request.user)
        liked = False
    else:
        photo.likes.add(request.user)
        liked = True
    return JsonResponse({'liked': liked, 'count': photo.likes.count()})

@login_required
def like_video(request, video_id):
    """Like/unlike a video"""
    try:
        video = get_object_or_404(Video, id=video_id)
    except Http404:
        return JsonResponse({'error': 'Video not found'}, status=404)
    
    if request.user in video.likes.all():
        video.likes.remove(request.user)
        liked = False
    else:
        video.likes.add(request.user)
        liked = True
    return JsonResponse({'liked': liked, 'count': video.likes.count()})

@login_required
def add_comment(request, content_type, content_id):
    """Add a comment or reply to photo or video"""
    if request.method == 'POST':
        text = request.POST.get('text', '')
        parent_id = request.POST.get('parent_id', None)
        
        if text:
            try:
                if content_type == 'photo':
                    content = get_object_or_404(Photo, id=content_id)
                    comment = Comment.objects.create(
                        author=request.user,
                        photo=content,
                        text=text,
                        content_type='photo'
                    )
                elif content_type == 'video':
                    content = get_object_or_404(Video, id=content_id)
                    comment = Comment.objects.create(
                        author=request.user,
                        video=content,
                        text=text,
                        content_type='video'
                    )
                else:
                    return JsonResponse({'error': 'Invalid content type'}, status=400)
                
                # Handle reply
                if parent_id:
                    parent_comment = get_object_or_404(Comment, id=parent_id)
                    comment.parent = parent_comment
                    comment.save()
                    
            except Http404:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'error': 'Content not found'}, status=404)
                messages.error(request, 'Content not found.')
                return redirect('frontend:feed')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # Return simple JSON response without template rendering
                return JsonResponse({
                    'success': True,
                    'comment_id': comment.id,
                    'author': comment.author.username,
                    'text': comment.text,
                    'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M'),
                    'is_reply': bool(parent_id),
                    'parent_id': parent_id
                })
            
            messages.success(request, 'Comment added successfully!')
            if content_type == 'photo':
                return redirect('frontend:photo_detail', photo_id=content_id)
            else:
                return redirect('frontend:video_detail', video_id=content_id)
    
    return redirect('frontend:feed')

@login_required
def delete_comment(request, comment_id):
    """Delete a comment (AJAX support)"""
    try:
        comment = get_object_or_404(Comment, id=comment_id)
    except Http404:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Comment not found'}, status=404)
        messages.error(request, 'Comment not found.')
        return redirect('frontend:feed')
    
    if comment.author != request.user:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'You can only delete your own comments'}, status=403)
        messages.error(request, 'You can only delete your own comments.')
        return redirect('frontend:feed')
    
    comment.delete()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    messages.success(request, 'Comment deleted successfully!')
    return redirect('frontend:feed')

@login_required
def delete_post(request, post_type, post_id):
    """Delete a photo or video post (supports AJAX for instant deletion)"""
    try:
        if post_type == 'photo':
            post = get_object_or_404(Photo, id=post_id)
        elif post_type == 'video':
            post = get_object_or_404(Video, id=post_id)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': 'Invalid post type'}, status=400)
            messages.error(request, 'Invalid post type.')
            return redirect('frontend:feed')
    except Http404:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Post not found'}, status=404)
        messages.error(request, 'Post not found.')
        return redirect('frontend:feed')
    
    if post.author != request.user:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'You can only delete your own posts'}, status=403)
        messages.error(request, 'You can only delete your own posts.')
        return redirect('frontend:feed')
    
    try:
        if post_type == 'photo' and post.image:
            if os.path.exists(post.image.path):
                os.remove(post.image.path)
        elif post_type == 'video' and post.video_file:
            if os.path.exists(post.video_file.path):
                os.remove(post.video_file.path)
    except Exception as e:
        print(f"Error deleting file: {e}")
    
    post_id_value = post.id
    post.delete()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': 'Post deleted successfully',
            'post_id': post_id_value,
            'post_type': post_type,
            'redirect_url': '/feed/'
        })
    
    messages.success(request, 'Post deleted successfully!')
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('frontend:feed')


# ========== API ENDPOINTS FOR AJAX NAVIGATION ==========

def get_all_photo_ids(request):
    """API endpoint to get all photo IDs for navigation"""
    photos = Photo.objects.filter(image__isnull=False).values_list('id', flat=True).order_by('-created_at')
    return JsonResponse({'ids': list(photos)})


def get_photo_data(request, photo_id):
    """API endpoint to get photo data for AJAX navigation"""
    try:
        photo = get_object_or_404(Photo, id=photo_id)
    except Http404:
        return JsonResponse({'error': 'Photo not found'}, status=404)
    
    # Get related photos
    related_photos = Photo.objects.filter(author=photo.author).exclude(id=photo_id)[:4]
    if not related_photos:
        related_photos = Photo.objects.exclude(id=photo_id).order_by('-views')[:4]
    
    # Get avatar safely
    author_avatar = None
    is_available = False
    if hasattr(photo.author, 'profile') and photo.author.profile:
        if photo.author.profile.avatar:
            author_avatar = photo.author.profile.avatar.url
        is_available = photo.author.profile.is_available_for_calls
    
    return JsonResponse({
        'id': photo.id,
        'image_url': photo.image.url,
        'caption': photo.caption if photo.caption else '',
        'description': '',
        'views': photo.views,
        'likes_count': photo.likes.count(),
        'comments_count': photo.comments.count(),
        'published_date': photo.created_at.strftime("%B %d, %Y"),
        'author_username': photo.author.username,
        'author_avatar': author_avatar,
        'is_available': is_available,
        'user_liked': request.user in photo.likes.all() if request.user.is_authenticated else False,
    })



def get_all_photos_api(request):
    """API endpoint to get all photos for carousel"""
    photos = Photo.objects.filter(image__isnull=False).order_by('-created_at')
    photos_data = []
    for photo in photos:
        photos_data.append({
            'id': photo.id,
            'image_url': photo.image.url,
            'caption': photo.caption,
        })
    return JsonResponse({'photos': photos_data})


def get_all_users_api(request):
    """API endpoint to get all users for messaging"""
    users = User.objects.exclude(id=request.user.id).select_related('profile')
    users_data = []
    
    for user in users:
        is_following = False
        if request.user.is_authenticated and hasattr(user, 'profile'):
            is_following = user.profile.followers.filter(id=request.user.id).exists()
        
        users_data.append({
            'id': user.id,
            'username': user.username,
            'avatar': user.profile.avatar.url if hasattr(user, 'profile') and user.profile.avatar else None,
            'bio': user.profile.bio if hasattr(user, 'profile') else '',
            'is_following': is_following,
        })
    
    return JsonResponse({'users': users_data})
