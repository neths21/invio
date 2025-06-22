from flask import render_template
from flask_mail import Message
from app import mail
from app.models.models import User

class EmailService:
    @staticmethod
    def send_analytics_report(ml_results, run_date):
        """
        Renders a simple email template, then sends it to all users.
        """
        # 1) Render email HTML
        html = render_template(
            'inventory/analytics_email.html',
            ml_results=ml_results,
            run_date=run_date
        )

        # 2) Collect recipients
        recipients = [u.email for u in User.query.with_entities(User.email).all()]

        # 3) Send the message
        msg = Message(
            subject="Inventory Analytics Report",
            recipients=recipients,
            html=html
        )
        mail.send(msg)
