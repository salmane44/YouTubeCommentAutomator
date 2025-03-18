import os
import logging
import json
from datetime import datetime, timedelta
from flask import render_template, redirect, url_for, flash, request, jsonify, session, g
from flask_login import login_required, current_user
from app import app, db
from models import User, YouTubeChannel, UserSettings, CommentHistory, VerificationCode
from forms import (AddYouTubeChannelForm, VerifyChannelForm, 
                  SettingsForm, CommentFilterForm, BulkModerationForm, CommentReplyForm)
from utils.youtube_api import get_youtube_service, get_channel_info, get_recent_comments, reply_to_comment
from utils.gemini_api import generate_comment_reply
from utils.email_service import generate_verification_code, save_verification_code, send_verification_email, verify_code
from config import COMMENTS_PER_PAGE

logger = logging.getLogger(__name__)

@app.before_request
def before_request():
    g.current_year = datetime.now().year

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/dashboard')
@login_required
def dashboard():
    channels = YouTubeChannel.query.filter_by(user_id=current_user.id).all()
    form = AddYouTubeChannelForm()
    return render_template('dashboard.html', channels=channels, form=form)

@app.route('/add_channel', methods=['POST'])
@login_required
def add_channel():
    form = AddYouTubeChannelForm()
    if form.validate_on_submit():
        channel_id = form.channel_id.data

        # Check if channel already exists 
        existing_channel = YouTubeChannel.query.filter_by(channel_id=channel_id).first()

        if existing_channel:
            if existing_channel.user_id == current_user.id:
                flash('This channel is already added to your account.', 'warning')
            else:
                flash('This channel has already been registered by another user.', 'danger')
            return redirect(url_for('dashboard'))

        # Get channel info from YouTube API
        youtube_service = get_youtube_service()
        if not youtube_service:
            flash('Failed to connect to YouTube API. Please try again later.', 'danger')
            return redirect(url_for('dashboard'))

        channel_info = get_channel_info(youtube_service, channel_id)
        if not channel_info:
            flash('Channel not found. Please check the ID and try again.', 'danger')
            return redirect(url_for('dashboard'))
            
        # Verify the channel exists
        if not channel_info.get('id'):
            flash('Invalid channel ID. Please check and try again.', 'danger')
            return redirect(url_for('dashboard'))

        # Create the channel record
        new_channel = YouTubeChannel(
            channel_id=channel_id,
            channel_name=channel_info['title'],
            user_id=current_user.id
        )

        db.session.add(new_channel)
        db.session.commit()

        flash(f'Channel "{channel_info["title"]}" added successfully!', 'success')
        return redirect(url_for('verify_channel', channel_id=new_channel.id))

    for field, errors in form.errors.items():
        for error in errors:
            flash(f"{getattr(form, field).label.text}: {error}", 'danger')

    return redirect(url_for('dashboard'))

@app.route('/verify_channel/<int:channel_id>', methods=['GET', 'POST'])
@login_required
def verify_channel(channel_id):
    channel = YouTubeChannel.query.get_or_404(channel_id)

    if channel.user_id != current_user.id:
        flash('You do not have permission to verify this channel.', 'danger')
        return redirect(url_for('dashboard'))

    form = VerifyChannelForm()

    if request.method == 'GET':
        verification_code = generate_verification_code()
        youtube_service = get_youtube_service()
        channel_info = get_channel_info(youtube_service, channel.channel_id)
        
        # Always use current user's email since YouTube API doesn't provide channel email
        if save_verification_code(channel.id, verification_code):
            if send_verification_email(current_user.email, channel.channel_name, verification_code):
                flash(f'Verification code sent to {current_user.email}', 'success')
            else:
                app.logger.error(f'Failed to send verification email to: {current_user.email}')
                flash('Failed to send verification email. Please try again.', 'danger')
        else:
            app.logger.error('Failed to save verification code')
            flash('Failed to generate verification code. Please try again.', 'danger')

    if form.validate_on_submit():
        verification_code = form.verification_code.data
        success, message = verify_code(channel.id, verification_code)

        if success:
            flash(message, 'success')
            return redirect(url_for('dashboard'))
        else:
            flash(message, 'danger')

    return render_template('verify_channel.html', channel=channel, form=form)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    user_settings = UserSettings.query.filter_by(user_id=current_user.id).first()
    if not user_settings:
        user_settings = UserSettings(user_id=current_user.id)
        db.session.add(user_settings)
        db.session.commit()

    form = SettingsForm(obj=user_settings)

    if form.validate_on_submit():
        form.populate_obj(user_settings)
        db.session.commit()
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('settings'))

    return render_template('settings.html', form=form)

@app.route('/history', methods=['GET'])
@login_required
def history():
    try:
        page = request.args.get('page', 1, type=int)
        channels = YouTubeChannel.query.filter_by(user_id=current_user.id).all()
        channel_ids = [channel.id for channel in channels]

        if not channels:
            flash('No channels found. Please add a channel first.', 'info')
            return redirect(url_for('dashboard'))

        form = CommentFilterForm()
        bulk_form = BulkModerationForm()

        query = CommentHistory.query.filter(CommentHistory.channel_id.in_(channel_ids))

        if 'start_date' in request.args and request.args['start_date']:
            start_date = datetime.strptime(request.args['start_date'], '%Y-%m-%d')
            query = query.filter(CommentHistory.published_at >= start_date)
            form.start_date.data = start_date

        if 'end_date' in request.args and request.args['end_date']:
            end_date = datetime.strptime(request.args['end_date'], '%Y-%m-%d')
            end_date = end_date + timedelta(days=1)
            query = query.filter(CommentHistory.published_at <= end_date)
            form.end_date.data = end_date

        query = query.order_by(CommentHistory.published_at.desc())
        pagination = query.paginate(page=page, per_page=COMMENTS_PER_PAGE, error_out=False)

        return render_template('history.html', 
                             pagination=pagination, 
                             form=form, 
                             bulk_form=bulk_form)

    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/api/check_auth', methods=['GET'])
def check_auth():
    """API endpoint to check if user is authenticated."""
    if current_user.is_authenticated:
        return jsonify({'authenticated': True, 'username': current_user.username})
    else:
        return jsonify({'authenticated': False})

@app.route('/oauth_setup')
def oauth_setup():
    """Display Google OAuth setup instructions."""
    replit_domain = os.environ.get('REPLIT_DEV_DOMAIN')
    redirect_uri = f"https://{replit_domain}/google_login/callback"
    app.logger.info(f"OAuth setup page displaying redirect URI: {redirect_uri}")
    return render_template("oauth_setup.html", redirect_uri=redirect_uri)

@app.route('/comment/select/<int:comment_id>', methods=['POST'])
@login_required
def select_comment(comment_id):
    """Toggle selection status of a comment for bulk operations"""
    comment = CommentHistory.query.get_or_404(comment_id)
    
    # Verify ownership through channel
    channel = YouTubeChannel.query.get(comment.channel_id)
    if not channel or channel.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'You do not have permission to select this comment.'})
    
    # Toggle selection
    comment.is_selected = not comment.is_selected
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'selected': comment.is_selected,
        'comment_id': comment.id
    })

@app.route('/moderation/bulk', methods=['POST'])
@login_required
def bulk_moderate():
    """Apply bulk moderation to selected comments"""
    form = BulkModerationForm()
    
    if form.validate_on_submit():
        # Get all user's channels
        channels = YouTubeChannel.query.filter_by(user_id=current_user.id).all()
        channel_ids = [channel.id for channel in channels]
        
        # Get all selected comments for this user's channels
        selected_comments = CommentHistory.query.filter(
            CommentHistory.channel_id.in_(channel_ids),
            CommentHistory.is_selected == True
        ).all()
        
        if not selected_comments:
            flash('No comments selected for moderation.', 'warning')
            return redirect(url_for('history'))
        
        moderation_status = form.moderation_status.data
        moderation_notes = form.moderation_notes.data
        moderated_at = datetime.utcnow()
        count = 0
        
        for comment in selected_comments:
            comment.moderation_status = moderation_status
            comment.moderation_notes = moderation_notes
            comment.moderated_at = moderated_at
            comment.is_selected = False  # Unselect after moderation
            count += 1
        
        db.session.commit()
        flash(f'Successfully moderated {count} comments.', 'success')
        
    return redirect(url_for('history'))

@app.route('/comment/reply/<int:comment_id>', methods=['GET', 'POST'])
@login_required
def reply_to_comment_route(comment_id):
    """Manually reply to a comment"""
    comment = CommentHistory.query.get_or_404(comment_id)
    
    # Verify ownership through channel
    channel = YouTubeChannel.query.get(comment.channel_id)
    if not channel or channel.user_id != current_user.id:
        flash('You do not have permission to reply to this comment.', 'danger')
        return redirect(url_for('history'))
    
    # Check if already replied
    if comment.replied:
        flash('This comment has already been replied to.', 'warning')
        return redirect(url_for('history'))
    
    form = CommentReplyForm()
    
    if form.validate_on_submit():
        reply_text = form.reply_text.data
        
        # Get YouTube service
        youtube_service = get_youtube_service()
        if not youtube_service:
            flash('Failed to connect to YouTube API. Please try again later.', 'danger')
            return redirect(url_for('history'))
        
        # Send reply to YouTube
        reply_result = reply_to_comment(youtube_service, comment.comment_id, reply_text)
        
        if reply_result:
            comment.replied = True
            comment.reply_text = reply_text
            comment.replied_at = datetime.utcnow()
            db.session.commit()
            flash('Reply sent successfully!', 'success')
            return redirect(url_for('history'))
        else:
            flash('Failed to send reply. Please try again.', 'danger')
    
    return render_template('comment_reply.html', comment=comment, form=form)

@app.route('/process_comments/<int:channel_id>', methods=['POST'])
@login_required
def process_comments(channel_id):
    channel = YouTubeChannel.query.get_or_404(channel_id)
    
    # Check if the channel belongs to the current user
    if channel.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'You do not have permission to process comments for this channel.'})
    
    # Check if the channel is verified
    if not channel.is_verified:
        return jsonify({'success': False, 'message': 'This channel is not verified. Please verify the channel first.'})
    
    # Get user settings
    settings = UserSettings.query.filter_by(user_id=current_user.id).first()
    if not settings:
        return jsonify({'success': False, 'message': 'User settings not found.'})
    
    # Parse date range
    data = request.get_json()
    start_date = None
    end_date = None
    
    if data.get('start_date'):
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d')
        
    if data.get('end_date'):
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d')
        # Include the entire end date
        end_date = end_date + timedelta(days=1)
        
    # Get YouTube service
    youtube_service = get_youtube_service()
    if not youtube_service:
        return jsonify({'success': False, 'message': 'Failed to connect to YouTube API. Please try again later.'})
    
    # Get recent comments
    comments = get_recent_comments(
        youtube_service, 
        channel.channel_id,
        max_results=100,
        start_date=start_date,
        end_date=end_date
    )
    
    if not comments:
        return jsonify({'success': True, 'message': 'No comments found in the specified date range.', 'processed': 0})
    
    # Process comments
    processed_count = 0
    for comment in comments:
        # Check if comment has already been processed
        existing_comment = CommentHistory.query.filter_by(comment_id=comment['comment_id']).first()
        if existing_comment:
            continue
        
        # Generate reply using Gemini
        reply_text = generate_comment_reply(comment['text'])
        if not reply_text:
            continue
        
        # Post reply to YouTube if auto-reply is enabled
        if settings.auto_reply_enabled:
            reply_result = reply_to_comment(youtube_service, comment['comment_id'], reply_text)
            replied = bool(reply_result)
            replied_at = datetime.utcnow() if replied else None
        else:
            replied = False
            replied_at = None
        
        # Save comment to history
        new_comment = CommentHistory(
            channel_id=channel.id,
            comment_id=comment['comment_id'],
            video_id=comment['video_id'],
            comment_text=comment['text'],
            author_name=comment['author_name'],
            author_id=comment['author_id'],
            published_at=comment['published_at'],
            replied=replied,
            reply_text=reply_text,
            replied_at=replied_at
        )
        
        db.session.add(new_comment)
        processed_count += 1
        
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': f'Successfully processed {processed_count} comments.',
        'processed': processed_count
    })

@app.route('/api/generate_reply', methods=['POST'])
@login_required
def generate_reply_api():
    """API endpoint to generate a comment reply without sending it."""
    data = request.get_json()
    comment_text = data.get('comment_text')
    
    if not comment_text:
        return jsonify({'success': False, 'error': 'Comment text is required'})
    
    reply = generate_comment_reply(comment_text)
    if reply:
        return jsonify({'success': True, 'reply': reply})
    else:
        return jsonify({'success': False, 'error': 'Failed to generate reply'})

@app.route('/remove_channel/<int:channel_id>', methods=['POST'])
@login_required
def remove_channel(channel_id):
    channel = YouTubeChannel.query.get_or_404(channel_id)

    # Verify ownership
    if channel.user_id != current_user.id:
        flash('You do not have permission to remove this channel.', 'danger')
        return redirect(url_for('dashboard'))

    try:
        # Delete associated verification codes
        VerificationCode.query.filter_by(channel_id=channel.id).delete()

        # Delete associated comment history
        CommentHistory.query.filter_by(channel_id=channel.id).delete()

        # Delete the channel
        db.session.delete(channel)
        db.session.commit()

        flash(f'Channel "{channel.channel_name}" has been removed successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error removing channel: {e}")
        flash('An error occurred while removing the channel. Please try again.', 'danger')

    return redirect(url_for('dashboard'))