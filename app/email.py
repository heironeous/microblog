from flask_mail import Message
from app import mail, app
from app.models import User
from flask import render_template

def send_email(subject: str, sender: str, recipients: list, text_body: str, html_body: str) -> None:
    msg = Message(subject=subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    mail.send(message=msg)
    
def send_password_reset_email(user: User) -> None:
    token = user.get_reset_password_token()
    send_email(
        subject='[Microblog] Reset Your Password',
        sender=app.config['ADMINS'][0],
        recipients=[user.email],
        text_body=render_template(
            template_name_or_list='email/reset_password.txt',
            user=user, token=token),
        html_body=render_template(
            template_name_or_list='email/reset_password.html',
            user=user, token=token))