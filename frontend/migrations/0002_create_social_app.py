from django.db import migrations
from django.contrib.sites.models import Site

def create_social_app(apps, schema_editor):
    SocialApp = apps.get_model('socialaccount', 'SocialApp')
    Site = apps.get_model('sites', 'Site')
    
    # Get or create the site
    site, created = Site.objects.get_or_create(
        domain='vibegaze.onrender.com',
        defaults={'name': 'VibeGaze'}
    )
    
    # Create the Google social app
    SocialApp.objects.get_or_create(
        provider='google',
        defaults={
            'name': 'VIBEGAZE',
            'client_id': '939897139146-vrium4shg57p8fnljo8sc3esk871mio3.apps.googleusercontent.com',
            'secret': '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',
        }
    )
    
    # Associate the app with the site
    app = SocialApp.objects.get(provider='google')
    app.sites.add(site)
    app.save()

def reverse_migration(apps, schema_editor):
    SocialApp = apps.get_model('socialaccount', 'SocialApp')
    SocialApp.objects.filter(provider='google').delete()

class Migration(migrations.Migration):
    dependencies = [
        ('frontend', '0001_initial'),  # Change to your last migration
        ('sites', '0002_alter_domain_unique'),
        ('socialaccount', '0006_alter_socialaccount_extra_data'),
    ]

    operations = [
        migrations.RunPython(create_social_app, reverse_migration),
    ]