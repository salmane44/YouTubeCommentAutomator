import os
import logging
import random
import string
from datetime import datetime, timedelta
from flask import render_template, current_app
from flask_mail import Message
from app import mail, db
from models import VerificationCode, YouTubeChannel
from config import VERIFICATION_CODE_LENGTH, VERIFICATION_CODE_EXPIRY

logger = logging.getLogger(__name__)

def generate_verification_code(length=VERIFICATION_CODE_LENGTH):
    """Generate a random verification code."""
    return ''.join(random.choices(string.digits, k=length))

def save_verification_code(channel_id, code):
    """Save a verification code for a YouTube channel."""
    try:
        # Calculate expiry time
        expiry = datetime.utcnow() + timedelta(seconds=VERIFICATION_CODE_EXPIRY)

        # Check if a verification code already exists for this channel
        existing_code = VerificationCode.query.filter_by(channel_id=channel_id).first()

        if existing_code:
            # Update existing code
            existing_code.code = code
            existing_code.expiry = expiry
        else:
            # Create new verification code
            verification = VerificationCode(
                channel_id=channel_id,
                code=code,
                expiry=expiry
            )
            db.session.add(verification)

        # Update the channel record
        channel = YouTubeChannel.query.get(channel_id)
        if channel:
            channel.verification_code = code
            channel.verification_code_expiry = expiry

        db.session.commit()
        return True

    except Exception as e:
        logger.error(f"Error saving verification code: {e}")
        db.session.rollback()
        return False

def send_verification_email(email, channel_name, verification_code):
    """Send a verification email to a YouTube channel owner."""
    if not email or not isinstance(email, str):
        logger.error(f"Cannot send verification email: Invalid email address: {email}")
        return False

    if not current_app.config.get('MAIL_USERNAME') or not current_app.config.get('MAIL_PASSWORD'):
        logger.error("Email configuration missing. Check MAIL_USERNAME and MAIL_APP_PASSWORD in environment variables.")
        return False

    try:
        msg = Message(
            subject='Verify Your YouTube Channel',
            sender=current_app.config['MAIL_USERNAME'],
            recipients=[email]  # Make sure email is a string and wrapped in a list
        )

        msg.body = f"""Hello,

Thank you for using our YouTube Comment Responder service.

To verify your ownership of the YouTube channel "{channel_name}", please use the following verification code:

{verification_code}

This code will expire in 30 minutes.

If you did not request this verification, please ignore this email.

Best regards,
The YouTube Comment Responder Team
"""

        msg.html = f"""
        <html>
        <body>
            <h2>YouTube Channel Verification</h2>
            <p>Hello,</p>
            <p>Thank you for using our YouTube Comment Responder service.</p>
            <p>To verify your ownership of the YouTube channel "<strong>{channel_name}</strong>", please use the following verification code:</p>
            <div style="background-color: #f5f5f5; padding: 15px; margin: 15px 0; text-align: center; font-size: 24px; font-weight: bold; letter-spacing: 5px;">
                {verification_code}
            </div>
            <p>This code will expire in 30 minutes.</p>
            <p>If you did not request this verification, please ignore this email.</p>
            <p>Best regards,<br>The YouTube Comment Responder Team</p>
        </body>
        </html>
        """

        mail.send(msg)
        logger.info(f"Verification email sent successfully to {email}")
        return True

    except Exception as e:
        logger.error(f"Error sending verification email: {e}", exc_info=True)
        return False

def verify_code(channel_id, code):
    """Verify a verification code for a YouTube channel."""
    from app import db
    try:
        # Get the verification record
        verification = VerificationCode.query.filter_by(
            channel_id=channel_id,
            code=code
        ).first()

        if not verification:
            return False, "Invalid verification code"

        # Check if the code has expired
        if verification.expiry < datetime.utcnow():
            return False, "Verification code has expired"

        # Mark the channel as verified
        channel = YouTubeChannel.query.get(channel_id)
        if channel:
            channel.is_verified = True
            channel.verification_code = None
            channel.verification_code_expiry = None
            db.session.commit()
            return True, "Channel verified successfully"
        else:
            return False, "Channel not found"

    except Exception as e:
        logger.error(f"Error verifying code: {e}")
        db.session.rollback()
        return False, f"An error occurred: {str(e)}"