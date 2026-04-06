from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import os
import re
import time
import random
from django.utils.deconstruct import deconstructible
from django.db.models.signals import post_save
from django.dispatch import receiver


# ========== FILE UPLOAD PATH HELPERS ==========

@deconstructible
class PhotoUploadPath:
    def __call__(self, instance, filename):
        name, ext = os.path.splitext(filename)
        clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        clean_name = clean_name[:50]
        return f'photos/{instance.author.username}/{timezone.now().strftime("%Y/%m/%d")}/{clean_name}{ext}'

@deconstructible
class VideoUploadPath:
    def __call__(self, instance, filename):
        name, ext = os.path.splitext(filename)
        clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        clean_name = clean_name[:50]
        return f'videos/{instance.author.username}/{timezone.now().strftime("%Y/%m/%d")}/{clean_name}{ext}'

photo_upload_path = PhotoUploadPath()
video_upload_path = VideoUploadPath()


# ========== USER PROFILE MODEL ==========

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(max_length=500, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    location = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    phone_number = models.CharField(max_length=20, blank=True, help_text="International format: +1234567890")
    is_verified = models.BooleanField(default=False)
    followers = models.ManyToManyField(User, related_name='following', blank=True)
    following = models.ManyToManyField(User, related_name='followers_list', blank=True)
    
    # Call settings
    call_price_per_minute = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_available_for_calls = models.BooleanField(default=False, help_text="Allow other users to call you")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s profile"
    
    @property
    def followers_count(self):
        return self.followers.count()
    
    @property
    def following_count(self):
        return self.following.count()
    
    @property
    def total_photos(self):
        return self.user.photos.count()
    
    @property
    def total_videos(self):
        return self.user.videos.count()


# ========== PHOTO MODEL ==========

class Photo(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to=photo_upload_path, max_length=500)
    caption = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    likes = models.ManyToManyField(User, related_name='liked_photos', blank=True)
    views = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Photo'
        verbose_name_plural = 'Photos'
    
    def __str__(self):
        return f"{self.author.username}'s photo - {self.created_at}"
    
    @property
    def likes_count(self):
        return self.likes.count()
    
    @property
    def image_url(self):
        return self.image.url if self.image else None
    
    @property
    def comments_count(self):
        return self.comments.count()


# ========== VIDEO MODEL ==========

class Video(models.Model):
    VIDEO_TYPES = [
        ('short', 'Short Video (< 60s)'),
        ('long', 'Long Video'),
    ]
    
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='videos')
    video_file = models.FileField(upload_to=video_upload_path, max_length=500)
    thumbnail = models.ImageField(upload_to='video_thumbnails/', blank=True, null=True)
    title = models.CharField(max_length=200)
    description = models.TextField(max_length=2000, blank=True)
    video_type = models.CharField(max_length=10, choices=VIDEO_TYPES, default='short')
    duration = models.PositiveIntegerField(help_text="Duration in seconds", default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    likes = models.ManyToManyField(User, related_name='liked_videos', blank=True)
    views = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Video'
        verbose_name_plural = 'Videos'
    
    def __str__(self):
        return f"{self.author.username}'s video: {self.title}"
    
    @property
    def likes_count(self):
        return self.likes.count()
    
    @property
    def comments_count(self):
        return self.comments.count()
    
    @property
    def formatted_duration(self):
        minutes = self.duration // 60
        seconds = self.duration % 60
        return f"{minutes}:{seconds:02d}"
    
    @property
    def video_url(self):
        return self.video_file.url if self.video_file else None
    




# Add this to your models.py after the Video model

class VideoView(models.Model):
    """Track unique video views from database"""
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='views_objects')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='video_views')
    session_key = models.CharField(max_length=40, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    watch_time = models.PositiveIntegerField(default=0, help_text="Watch time in seconds")
    completed = models.BooleanField(default=False)
    viewed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-viewed_at']
        unique_together = ['video', 'session_key']  # Prevent duplicate views from same session
    
    def __str__(self):
        user_str = self.user.username if self.user else 'Anonymous'
        return f"{user_str} viewed {self.video.title} at {self.viewed_at}"


# ========== COMMENT MODEL ==========
# Add to your models.py - Add 'parent' field to Comment model

class Comment(models.Model):
    CONTENT_TYPES = [
        ('photo', 'Photo'),
        ('video', 'Video'),
    ]
    
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    content_type = models.CharField(max_length=10, choices=CONTENT_TYPES)
    photo = models.ForeignKey(Photo, on_delete=models.CASCADE, related_name='comments', null=True, blank=True)
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='comments', null=True, blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    text = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']  # Change to created_at for chronological order
    
    def __str__(self):
        target = self.photo if self.photo else self.video
        return f"{self.author.username} on {target}"
    
    @property
    def is_reply(self):
        return self.parent is not None
    
    @property
    def reply_count(self):
        return self.replies.count()
# ========== SHARE MODEL ==========

class Share(models.Model):
    SHARE_TYPES = [
        ('photo', 'Photo'),
        ('video', 'Video'),
        ('profile', 'Profile'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shares')
    content_type = models.CharField(max_length=20, choices=SHARE_TYPES)
    photo = models.ForeignKey(Photo, on_delete=models.CASCADE, null=True, blank=True)
    video = models.ForeignKey(Video, on_delete=models.CASCADE, null=True, blank=True)
    profile_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='profile_shares')
    platform = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Shared {self.content_type} by {self.user.username}"


# ========== CALL SESSION MODEL ==========

class CallSession(models.Model):
    CALL_STATUS = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('missed', 'Missed'),
        ('failed', 'Failed'),
    ]
    
    CALL_TYPE = [
        ('browser', 'Browser to Browser (WebRTC)'),
        ('phone', 'Browser to Phone (PSTN)'),
        ('phone_to_phone', 'Phone to Phone'),
    ]
    
    # Participants
    caller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='outgoing_calls')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='incoming_calls')
    
    # Call details
    call_type = models.CharField(max_length=20, choices=CALL_TYPE, default='browser')
    status = models.CharField(max_length=20, choices=CALL_STATUS, default='pending')
    receiver_phone_number = models.CharField(max_length=20, blank=True, null=True)
    
    # Duration and pricing
    duration = models.PositiveIntegerField(default=0, help_text="Duration in seconds")
    price_per_minute = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Timestamps
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # WebRTC and Twilio tracking
    room_name = models.CharField(max_length=255, unique=True, blank=True)
    twilio_call_sid = models.CharField(max_length=255, blank=True, null=True)
    twilio_status = models.CharField(max_length=50, blank=True, null=True)
    
    def save(self, *args, **kwargs):
        if not self.room_name:
            unique_suffix = random.randint(1000, 9999)
            self.room_name = f"call_{self.caller.id}_{self.receiver.id}_{int(time.time())}_{unique_suffix}"
        super().save(*args, **kwargs)
    
    def calculate_cost(self):
        if self.duration > 0:
            minutes = self.duration / 60
            self.total_cost = minutes * self.price_per_minute
            self.save()
        return self.total_cost
    
    @property
    def formatted_duration(self):
        minutes = self.duration // 60
        seconds = self.duration % 60
        return f"{minutes}:{seconds:02d}"
    
    def __str__(self):
        return f"{self.call_type} call from {self.caller.username} to {self.receiver.username} ({self.status})"


# ========== MESSAGING MODELS ==========

class MessageThread(models.Model):
    """Message thread/conversation between users"""
    participants = models.ManyToManyField(User, related_name='message_threads')
    subject = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Thread: {self.subject}"
    
    def get_last_message(self):
        return self.messages.first()
    
    def get_unread_count(self, user):
        return self.messages.filter(is_read=False).exclude(sender=user).count()
    
    def get_other_participant(self, user):
        for participant in self.participants.all():
            if participant != user:
                return participant
        return None
    
    @property
    def last_message(self):
        return self.messages.first()
    
    @property
    def last_message_preview(self):
        last_msg = self.messages.first()
        if last_msg:
            return last_msg.content[:50]
        return "No messages"


class Message(models.Model):
    """Individual message in a thread"""
    FILE_TYPES = [
        ('image', 'Image'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('document', 'Document'),
        ('voice', 'Voice Note'),
    ]
    
    thread = models.ForeignKey(MessageThread, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField(max_length=5000, blank=True)  # Made blank=True for file-only messages
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    
    # File attachment fields
    file = models.FileField(upload_to='chat_files/%Y/%m/%d/', null=True, blank=True)
    file_type = models.CharField(max_length=20, choices=FILE_TYPES, null=True, blank=True)
    file_name = models.CharField(max_length=255, null=True, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True)  # Size in bytes
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Message from {self.sender.username} in {self.thread.subject}"
    
    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.save()
    
    @property
    def short_content(self):
        if self.file:
            return f"[{self.get_file_type_display()}] {self.file_name}"
        return self.content[:100] + '...' if len(self.content) > 100 else self.content
    
    @property
    def file_size_display(self):
        if not self.file_size:
            return "Unknown size"
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.file_size < 1024.0:
                return f"{self.file_size:.1f} {unit}"
            self.file_size /= 1024.0
        return f"{self.file_size:.1f} GB"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()