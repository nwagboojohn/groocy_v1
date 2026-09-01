from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

def send_groocy_email(user_email, subject, template_name, context):
    # This renders an HTML file as a string for the email body
    html_message = render_to_string(template_name, context)
    
    send_mail(
        subject=subject,
        message="", # Plain text version (optional)
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user_email],
        html_message=html_message,
        fail_silently=True,
    )
    
