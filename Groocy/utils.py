# from django.core.mail import send_mail
# from django.template.loader import render_to_string
# from django.conf import settings        

# def send_groocy_email(user_email, subject, template_name, context):
#     # This renders an HTML file as a string for the email body
#     html_message = render_to_string(template_name, context)
    
#     send_mail(
#         subject=subject,
#         message="", # Plain text version (optional)
#         from_email=settings.DEFAULT_FROM_EMAIL,
#         recipient_list=[user_email],
#         html_message=html_message,
#         fail_silently=True,
#     )


import logging
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

logger = logging.getLogger(__name__)

def send_groocy_email(recipient_email, subject, template_name, context=None):
    if not recipient_email:
        print("⚠️ Email skipped: No recipient email provided.")
        return False

    if context is None:
        context = {}

    try:
        # Render HTML body
        html_message = render_to_string(template_name, context)
        # Generate plain text version from HTML
        plain_message = strip_tags(html_message)

        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            html_message=html_message,
            fail_silently=False,  # Raises explicit errors during debugging
        )
        print(f"✅ Email successfully sent to {recipient_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_email}: {e}")
        print(f"❌ Email Sending Error ({recipient_email}): {e}")
        return False