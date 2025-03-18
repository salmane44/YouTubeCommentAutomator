import os
import json
import requests
from flask import Blueprint, redirect, request, url_for, current_app, session, flash
from flask_login import login_user, logout_user, login_required
from app import db, oauth
from models import User, UserSettings

auth_blueprint = Blueprint("google_auth", __name__)  # Changed name to avoid conflicts

@auth_blueprint.route("/google_login")
def login():
    try:
        # Get replit domain for redirect
        replit_domain = os.environ.get('REPLIT_DEV_DOMAIN')
        redirect_uri = f"https://{replit_domain}/google_login/callback"

        # Print the exact redirect URI to the console for configuration
        exact_uri = redirect_uri
        current_app.logger.info(f"=== IMPORTANT: YOUR EXACT REDIRECT URI IS: {exact_uri} ===")
        current_app.logger.info("Make sure this EXACT URI is registered in Google Cloud Console")

        return oauth.google.authorize_redirect(redirect_uri)
    except Exception as e:
        current_app.logger.error(f"Error in Google login route: {str(e)}", exc_info=e)
        flash('Failed to initialize Google login. Please try again.', 'danger')
        return redirect(url_for('index'))

@auth_blueprint.route("/google_login/callback")
def callback():
    try:
        token = oauth.google.authorize_access_token()
        current_app.logger.debug("Successfully obtained access token")

        # Store token in session for YouTube API use
        session['google_token'] = token

        # Get user info
        resp = oauth.google.get('https://www.googleapis.com/oauth2/v3/userinfo')
        user_info = resp.json()

        current_app.logger.debug(f"Google user info received for email: {user_info.get('email', 'email not found')}")

        # Check if user exists in our database
        user = User.query.filter_by(email=user_info['email']).first()

        if not user:
            # Create a new user with either the Google name or email prefix as username
            username = user_info.get('name', user_info['email'].split('@')[0])

            # Make sure the username is unique
            base_username = username
            count = 1
            while User.query.filter_by(username=username).first():
                username = f"{base_username}{count}"
                count += 1

            user = User(
                username=username,
                email=user_info['email'],
                oauth_id=user_info.get('sub'),  # Store Google user ID
                is_verified=True  # Google users are pre-verified
            )
            db.session.add(user)

            # Create default settings for the user
            settings = UserSettings(user=user)
            db.session.add(settings)

            db.session.commit()
            current_app.logger.debug(f"Created new user: {username}")
        else:
            # Update existing user's OAuth ID if needed
            if not user.oauth_id:
                user.oauth_id = user_info.get('sub')
                db.session.commit()

        # Log in the user
        login_user(user)

        flash('Successfully logged in with Google', 'success')
        return redirect(url_for('dashboard'))
    except Exception as e:
        current_app.logger.error(f"Error in Google OAuth callback: {str(e)}", exc_info=e)
        flash('Failed to authenticate with Google. Please try again.', 'danger')
        return redirect(url_for('index'))

@auth_blueprint.route("/logout")
@login_required
def logout():
    session.pop('google_token', None)
    logout_user()
    return redirect(url_for('index'))