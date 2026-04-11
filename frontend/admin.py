from django.contrib import admin
from django.utils.html import format_html
from django.contrib.auth.models import User
from .models import (
    UserProfile, Photo, Video, Comment, Share, 
    CallSession, MessageThread, Message, VideoView, BackgroundMedia,
    MpesaTransaction, PaidMessage, SiteSetting, Feature, UserSession, Match
)

# ========== SITE SETTING ADMIN ==========

@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    list_display = ['key', 'value_preview', 'description_preview', 'updated_at']
    list_filter = ['updated_at']
    search_fields = ['key', 'value', 'description']
    readonly_fields = ['updated_at']
    
    fieldsets = (
        ('Setting Information', {
            'fields': ('key', 'value', 'description')
        }),
        ('Timestamps', {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )
    
    def value_preview(self, obj):
        return obj.value[:50] + '...' if len(obj.value) > 50 else obj.value
    value_preview.short_description = 'Value'
    
    def description_preview(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_preview.short_description = 'Description'
    
    actions = ['delete_selected']


# ========== FEATURE ADMIN ==========

@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ['id', 'icon_preview', 'title', 'description_preview', 'order', 'is_active']
    list_filter = ['is_active', 'created_at']
    list_editable = ['order', 'is_active']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Feature Information', {
            'fields': ('title', 'description', 'icon_image', 'order', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def icon_preview(self, obj):
        if obj.icon_image:
            return format_html('<img src="{}?w_50,h_50,c_fill,q_auto,f_auto" width="40" height="40" style="object-fit: cover; border-radius: 50%;" />', obj.icon_image.url)
        return format_html('<span style="color: gray;">No icon</span>')
    icon_preview.short_description = 'Icon'
    
    def description_preview(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_preview.short_description = 'Description'
    
    actions = ['activate_features', 'deactivate_features']
    
    def activate_features(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f'{queryset.count()} features activated.')
    activate_features.short_description = 'Activate selected features'
    
    def deactivate_features(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f'{queryset.count()} features deactivated.')
    deactivate_features.short_description = 'Deactivate selected features'


# ========== USER SESSION ADMIN ==========

@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'session_key_preview', 'last_activity', 'ip_address']
    list_filter = ['last_activity']
    search_fields = ['user__username', 'session_key', 'ip_address']
    readonly_fields = ['last_activity']
    
    fieldsets = (
        ('Session Information', {
            'fields': ('user', 'session_key', 'ip_address')
        }),
        ('Activity', {
            'fields': ('last_activity',),
            'classes': ('collapse',)
        }),
    )
    
    def session_key_preview(self, obj):
        return obj.session_key[:20] + '...' if len(obj.session_key) > 20 else obj.session_key
    session_key_preview.short_description = 'Session Key'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
    
    actions = ['delete_old_sessions']
    
    def delete_old_sessions(self, request, queryset):
        from django.utils import timezone
        from datetime import timedelta
        old_cutoff = timezone.now() - timedelta(days=7)
        old_sessions = queryset.filter(last_activity__lt=old_cutoff)
        count = old_sessions.count()
        old_sessions.delete()
        self.message_user(request, f'{count} old sessions deleted.')
    delete_old_sessions.short_description = 'Delete sessions older than 7 days'


# ========== MATCH ADMIN ==========

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ['id', 'user1', 'user2', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user1__username', 'user2__username']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Match Information', {
            'fields': ('user1', 'user2')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user1', 'user2')
    
    actions = ['delete_selected']


# ========== USER PROFILE ADMIN ==========

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'avatar_preview', 'phone_number', 'is_available_for_calls', 'call_price_per_minute', 'paid_message_price', 'followers_count', 'is_verified']
    list_filter = ['is_available_for_calls', 'is_verified', 'created_at']
    search_fields = ['user__username', 'user__email', 'phone_number', 'location']
    readonly_fields = ['followers_count', 'following_count', 'created_at', 'updated_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'bio', 'avatar', 'location', 'website')
        }),
        ('Contact Information', {
            'fields': ('phone_number', 'is_verified')
        }),
        ('Pricing Settings', {
            'fields': ('call_price_per_minute', 'paid_message_price'),
            'classes': ('collapse',)
        }),
        ('Call Settings', {
            'fields': ('is_available_for_calls',),
            'classes': ('collapse',)
        }),
        ('Social', {
            'fields': ('followers', 'following'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def avatar_preview(self, obj):
        if obj.avatar:
            return format_html('<img src="{}?w_50,h_50,c_fill,q_auto,f_auto" width="40" height="40" style="object-fit: cover; border-radius: 50%;" />', obj.avatar.url)
        return format_html('<span style="color: gray;">No avatar</span>')
    avatar_preview.short_description = 'Avatar'
    
    def followers_count(self, obj):
        return obj.followers.count()
    followers_count.short_description = 'Followers'
    
    def following_count(self, obj):
        return obj.following.count()
    following_count.short_description = 'Following'




# ========== BACKGROUND MEDIA ADMIN ==========

# frontend/admin.py

@admin.register(BackgroundMedia)
class BackgroundMediaAdmin(admin.ModelAdmin):
    list_display = ['id', 'media_type', 'is_active', 'created_at']
    list_filter = ['media_type', 'is_active', 'created_at']
    list_editable = ['is_active']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Media Information', {
            'fields': ('media_type', 'file', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Save the model - CloudinaryField handles the file upload automatically"""
        if obj.is_active:
            BackgroundMedia.objects.exclude(id=obj.id).update(is_active=False)
        super().save_model(request, obj, form, change)
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Make file field required only for new objects
        if obj is None:
            form.base_fields['file'].required = True
        else:
            form.base_fields['file'].required = False
        return form

@admin.register(MpesaTransaction)
class MpesaTransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'transaction_type', 'amount', 'phone_number', 'status', 'mpesa_receipt_number', 'created_at']
    list_filter = ['status', 'transaction_type', 'created_at']
    search_fields = ['user__username', 'phone_number', 'mpesa_receipt_number', 'reference_id']
    readonly_fields = ['reference_id', 'merchant_request_id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Transaction Details', {
            'fields': ('user', 'transaction_type', 'amount', 'phone_number', 'status')
        }),
        ('M-PESA Response', {
            'fields': ('reference_id', 'merchant_request_id', 'mpesa_receipt_number', 'result_code', 'result_desc')
        }),
        ('Content Reference', {
            'fields': ('content_id', 'content_type'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
    
    actions = ['mark_as_completed', 'mark_as_failed', 'mark_as_pending']
    
    def mark_as_completed(self, request, queryset):
        queryset.update(status='completed')
        self.message_user(request, f'{queryset.count()} transactions marked as completed.')
    mark_as_completed.short_description = 'Mark as completed'
    
    def mark_as_failed(self, request, queryset):
        queryset.update(status='failed')
        self.message_user(request, f'{queryset.count()} transactions marked as failed.')
    mark_as_failed.short_description = 'Mark as failed'
    
    def mark_as_pending(self, request, queryset):
        queryset.update(status='pending')
        self.message_user(request, f'{queryset.count()} transactions marked as pending.')
    mark_as_pending.short_description = 'Mark as pending'


# ========== PAID MESSAGE ADMIN ==========

@admin.register(PaidMessage)
class PaidMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'sender', 'receiver', 'amount', 'is_paid', 'is_read', 'message_preview', 'created_at']
    list_filter = ['is_paid', 'is_read', 'created_at']
    search_fields = ['sender__username', 'receiver__username', 'message']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Participants', {
            'fields': ('sender', 'receiver')
        }),
        ('Message Details', {
            'fields': ('message', 'amount', 'is_paid', 'is_read')
        }),
        ('Transaction', {
            'fields': ('transaction',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('sender', 'receiver', 'transaction')
    
    actions = ['mark_as_paid', 'mark_as_unpaid', 'mark_as_read', 'mark_as_unread']
    
    def mark_as_paid(self, request, queryset):
        queryset.update(is_paid=True)
        self.message_user(request, f'{queryset.count()} messages marked as paid.')
    mark_as_paid.short_description = 'Mark as paid'
    
    def mark_as_unpaid(self, request, queryset):
        queryset.update(is_paid=False)
        self.message_user(request, f'{queryset.count()} messages marked as unpaid.')
    mark_as_unpaid.short_description = 'Mark as unpaid'
    
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
        self.message_user(request, f'{queryset.count()} messages marked as read.')
    mark_as_read.short_description = 'Mark as read'
    
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
        self.message_user(request, f'{queryset.count()} messages marked as unread.')
    mark_as_unread.short_description = 'Mark as unread'


# ========== PHOTO ADMIN ==========

@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ['id', 'author', 'thumbnail_preview', 'caption_preview', 'created_at', 'likes_count', 'views']
    list_filter = ['created_at', 'author']
    search_fields = ['author__username', 'caption']
    readonly_fields = ['views', 'likes_count', 'created_at', 'updated_at']
    
    def thumbnail_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}?w_50,h_50,c_fill,q_auto,f_auto" width="50" height="50" style="object-fit: cover; border-radius: 5px;" />', obj.image.url)
        return "No Image"
    thumbnail_preview.short_description = 'Preview'
    
    def caption_preview(self, obj):
        return obj.caption[:50] + '...' if len(obj.caption) > 50 else obj.caption
    caption_preview.short_description = 'Caption'
    
    def likes_count(self, obj):
        return obj.likes.count()
    likes_count.short_description = 'Likes'


# ========== VIDEO ADMIN ==========

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ['id', 'author', 'title', 'video_type', 'thumbnail_preview', 'created_at', 'likes_count', 'views']
    list_filter = ['created_at', 'author', 'video_type']
    search_fields = ['author__username', 'title', 'description']
    readonly_fields = ['views', 'likes_count', 'created_at', 'updated_at', 'duration']
    
    def thumbnail_preview(self, obj):
        if obj.thumbnail:
            return format_html('<img src="{}?w_50,h_50,c_fill,q_auto,f_auto" width="50" height="50" style="object-fit: cover; border-radius: 5px;" />', obj.thumbnail.url)
        return format_html('<span style="color: gray;">No thumbnail</span>')
    thumbnail_preview.short_description = 'Preview'
    
    def likes_count(self, obj):
        return obj.likes.count()
    likes_count.short_description = 'Likes'


# ========== COMMENT ADMIN ==========

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['id', 'author', 'content_type', 'content_preview', 'created_at']
    list_filter = ['created_at', 'content_type', 'author']
    search_fields = ['author__username', 'text']
    readonly_fields = ['created_at']
    
    def content_preview(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    content_preview.short_description = 'Comment'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('author', 'photo', 'video')


# ========== SHARE ADMIN ==========

@admin.register(Share)
class ShareAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'content_type', 'content_link', 'platform', 'created_at']
    list_filter = ['platform', 'content_type', 'created_at']
    search_fields = ['user__username']
    readonly_fields = ['created_at']
    
    def content_link(self, obj):
        if obj.content_type == 'photo' and obj.photo:
            return format_html('<a href="/admin/frontend/photo/{}/change/">Photo #{}</a>', obj.photo.id, obj.photo.id)
        elif obj.content_type == 'video' and obj.video:
            return format_html('<a href="/admin/frontend/video/{}/change/">Video #{}</a>', obj.video.id, obj.video.id)
        elif obj.content_type == 'profile' and obj.profile_user:
            return format_html('<a href="/admin/auth/user/{}/change/">User: {}</a>', obj.profile_user.id, obj.profile_user.username)
        return "N/A"
    content_link.short_description = 'Content'


# ========== CALL SESSION ADMIN ==========

@admin.register(CallSession)
class CallSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'caller', 'receiver', 'call_type', 'status', 'formatted_duration', 'total_cost', 'created_at']
    list_filter = ['call_type', 'status', 'created_at']
    search_fields = ['caller__username', 'receiver__username', 'twilio_call_sid']
    readonly_fields = ['room_name', 'twilio_call_sid', 'formatted_duration', 'created_at']
    
    fieldsets = (
        ('Participants', {
            'fields': ('caller', 'receiver')
        }),
        ('Call Details', {
            'fields': ('call_type', 'status', 'receiver_phone_number')
        }),
        ('Duration & Pricing', {
            'fields': ('duration', 'formatted_duration', 'price_per_minute', 'total_cost')
        }),
        ('Timestamps', {
            'fields': ('started_at', 'ended_at', 'created_at')
        }),
        ('Tracking', {
            'fields': ('room_name', 'twilio_call_sid', 'twilio_status'),
            'classes': ('collapse',)
        }),
    )
    
    def formatted_duration(self, obj):
        return obj.formatted_duration
    formatted_duration.short_description = 'Duration'
    
    actions = ['mark_as_completed', 'mark_as_cancelled']
    
    def mark_as_completed(self, request, queryset):
        queryset.update(status='completed')
        self.message_user(request, f'{queryset.count()} calls marked as completed.')
    mark_as_completed.short_description = 'Mark selected calls as completed'
    
    def mark_as_cancelled(self, request, queryset):
        queryset.update(status='cancelled')
        self.message_user(request, f'{queryset.count()} calls marked as cancelled.')
    mark_as_cancelled.short_description = 'Mark selected calls as cancelled'


# ========== MESSAGE THREAD ADMIN ==========

@admin.register(MessageThread)
class MessageThreadAdmin(admin.ModelAdmin):
    list_display = ['id', 'subject', 'participant_list', 'message_count', 'last_message_preview', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['subject', 'participants__username']
    readonly_fields = ['created_at', 'updated_at']
    
    def participant_list(self, obj):
        return ", ".join([user.username for user in obj.participants.all()])
    participant_list.short_description = 'Participants'
    
    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = 'Messages'
    
    def last_message_preview(self, obj):
        last_msg = obj.messages.first()
        if last_msg:
            return f"{last_msg.sender.username}: {last_msg.short_content}"
        return "No messages"
    last_message_preview.short_description = 'Last Message'
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('participants', 'messages')


# ========== MESSAGE ADMIN ==========

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'sender', 'thread_subject', 'short_content', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at', 'sender']
    search_fields = ['sender__username', 'content', 'thread__subject']
    readonly_fields = ['created_at']
    
    def thread_subject(self, obj):
        return obj.thread.subject
    thread_subject.short_description = 'Thread'
    
    def short_content(self, obj):
        return obj.short_content
    short_content.short_description = 'Message'
    
    actions = ['mark_as_read', 'mark_as_unread']
    
    def mark_as_read(self, request, queryset):
        for message in queryset:
            message.mark_as_read()
        self.message_user(request, f'{queryset.count()} messages marked as read.')
    mark_as_read.short_description = 'Mark selected messages as read'
    
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
        self.message_user(request, f'{queryset.count()} messages marked as unread.')
    mark_as_unread.short_description = 'Mark selected messages as unread'


# ========== VIDEO VIEW ADMIN ==========

@admin.register(VideoView)
class VideoViewAdmin(admin.ModelAdmin):
    list_display = ['id', 'video', 'user', 'session_key', 'watch_time', 'completed', 'viewed_at']
    list_filter = ['completed', 'viewed_at']
    search_fields = ['video__title', 'user__username', 'session_key']
    readonly_fields = ['viewed_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('video', 'user')


# ========== CUSTOM ADMIN SITE CONFIGURATION ==========

admin.site.site_header = 'VibeGaze Administration'
admin.site.site_title = 'VibeGaze Admin Portal'
admin.site.index_title = 'Welcome to VibeGaze Admin Portal'

# Register User model with custom display
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined']
    list_filter = ['is_staff', 'is_active', 'date_joined']
    search_fields = ['username', 'email']

# Unregister default User admin and register custom one
admin.site.unregister(User)
admin.site.register(User, UserAdmin)