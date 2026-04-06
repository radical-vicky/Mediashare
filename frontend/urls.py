from django.urls import path
from . import views
from . import twilio_views
from . import message_views

app_name = 'frontend'

urlpatterns = [
    # Home and Feed
    path('', views.home, name='home'),
    path('feed/', views.feed, name='feed'),
    
    # Profile URLs
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/<str:username>/', views.user_profile, name='user_profile'),
    
    # Media detail views
    path('photo/<int:photo_id>/', views.photo_detail, name='photo_detail'),
    path('video/<int:video_id>/', views.video_detail, name='video_detail'),
    
    # Upload endpoints
    path('upload/photo/', views.upload_photo, name='upload_photo'),
    path('upload/video/', views.upload_video, name='upload_video'),
    
    # Like endpoints
    path('like/photo/<int:photo_id>/', views.like_photo, name='like_photo'),
    path('like/video/<int:video_id>/', views.like_video, name='like_video'),
    
    # Comment endpoint
    path('comment/<str:content_type>/<int:content_id>/', views.add_comment, name='add_comment'),
    
    # Delete endpoint
    path('delete/<str:post_type>/<int:post_id>/', views.delete_post, name='delete_post'),
    
    # Follow endpoint
    path('follow/<str:username>/', views.follow_user, name='follow_user'),
    
    # Download and share
    path('download/<str:media_type>/<int:media_id>/', views.download_media, name='download_media'),
    path('share/<str:media_type>/<int:media_id>/', views.share_media, name='share_media'),
    
    # Call endpoints
    path('call/<str:username>/', twilio_views.initiate_call, name='initiate_call'),
    path('call/room/<str:room_name>/', views.call_room, name='call_room'),
    path('call/end/<int:call_id>/', twilio_views.end_call, name='end_call'),
    path('call/settings/', twilio_views.call_settings, name='call_settings'),
    path('calls/history/', twilio_views.call_history, name='calls_history'),
    
    # Twilio webhook endpoints
    path('twilio/voice/<int:call_id>/', twilio_views.twilio_voice_webhook, name='twilio_voice_webhook'),
    path('twilio/status/', twilio_views.twilio_status_callback, name='twilio_status_callback'),
    path('twilio/token/', twilio_views.generate_twilio_token, name='twilio_token'),
    
    # Messaging endpoints
    path('messages/inbox/', message_views.inbox, name='inbox'),
    path('messages/thread/<int:thread_id>/', message_views.thread_detail, name='thread_detail'),
    path('messages/new/<str:username>/', message_views.new_message, name='new_message'),
    path('messages/send-ajax/', message_views.send_ajax_message, name='send_ajax_message'),
    path('messages/unread-count/', message_views.get_unread_count, name='get_unread_count'),
    path('messages/delete/<int:thread_id>/', message_views.delete_thread, name='delete_thread'),
    
    # Comment delete endpoint
    path('comment/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),
    
    # API endpoints for AJAX navigation (no page refresh)
    path('api/photos/ids/', views.get_all_photo_ids, name='api_photo_ids'),
    path('api/photo/<int:photo_id>/data/', views.get_photo_data, name='api_photo_data'),
    path('api/photos/all/', views.get_all_photos_api, name='api_all_photos'),
    # Add to urls.py
    path('video/<int:video_id>/track-view/', views.track_video_view, name='track_video_view'),
    # Add this to your messaging endpoints
    path('messages/thread/<int:thread_id>/messages/', message_views.get_thread_messages, name='get_thread_messages'),
    path('messages/thread/<int:thread_id>/read/', message_views.mark_thread_read, name='mark_thread_read'),
    path('messages/thread/<int:thread_id>/typing/', message_views.typing_indicator, name='typing_indicator'),
    path('api/users/all/', views.get_all_users_api, name='api_all_users'),
]