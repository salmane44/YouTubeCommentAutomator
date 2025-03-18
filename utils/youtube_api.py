import os
import logging
from datetime import datetime, timedelta
from flask import session
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config import YOUTUBE_API_SCOPES, YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION

logger = logging.getLogger(__name__)

def get_youtube_service(credentials_dict=None):
    """Build and return a YouTube API service object."""
    try:
        # Use OAuth credentials from session
        if session.get('google_token'):
            token_data = session['google_token']
            credentials = Credentials(
                token=token_data.get('access_token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=os.environ.get('GOOGLE_OAUTH_CLIENT_ID'),
                client_secret=os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET'),
                scopes=YOUTUBE_API_SCOPES
            )
            return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=credentials)
        else:
            logger.error("No OAuth credentials found in session")
            return None
    except Exception as e:
        logger.error(f"Error creating YouTube service: {e}")
        return None

def get_channel_info(youtube_service, channel_id=None):
    """Get information about a YouTube channel."""
    try:
        if channel_id:
            request = youtube_service.channels().list(
                part="snippet,contentDetails,contentOwnerDetails,brandingSettings",
                id=channel_id
            )
        else:
            # If no channel ID is specified, get the authenticated user's channel
            request = youtube_service.channels().list(
                part="snippet,contentDetails,contentOwnerDetails,brandingSettings",
                mine=True
            )

        response = request.execute()
        logger.debug(f"YouTube API Response: {response}")

        if not response.get('items'):
            logger.error(f"No channel found for ID: {channel_id}")
            return None

        channel = response['items'][0]

        # Use channel title and ID
        email = channel.get('contentOwnerDetails', {}).get('email')
        return {
            'id': channel['id'],
            'title': channel['snippet']['title'],
            'email': email
        }
    except HttpError as e:
        logger.error(f"Error retrieving channel info: {e}")
        return None

def get_recent_comments(youtube_service, channel_id, max_results=100, start_date=None, end_date=None):
    """
    Get recent comments on a YouTube channel's videos.

    Args:
        youtube_service: The YouTube API service object
        channel_id: The YouTube channel ID
        max_results: Maximum number of comments to retrieve
        start_date: Optional datetime object for start date filter
        end_date: Optional datetime object for end date filter

    Returns:
        List of comment objects
    """
    try:
        # First get the channel's uploads playlist ID
        channels_response = youtube_service.channels().list(
            part="contentDetails",
            id=channel_id
        ).execute()

        if not channels_response.get('items'):
            logger.error(f"Channel not found: {channel_id}")
            return []

        uploads_playlist_id = channels_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

        # Get the channel's videos
        playlist_items_response = youtube_service.playlistItems().list(
            part="snippet",
            playlistId=uploads_playlist_id,
            maxResults=50  # Get up to 50 recent videos
        ).execute()

        video_ids = [item['snippet']['resourceId']['videoId'] 
                     for item in playlist_items_response.get('items', [])]

        if not video_ids:
            logger.warning(f"No videos found for channel: {channel_id}")
            return []

        # Get comments for each video
        all_comments = []
        for video_id in video_ids:
            try:
                comments_response = youtube_service.commentThreads().list(
                    part="snippet",
                    videoId=video_id,
                    maxResults=max(20, max_results // len(video_ids))
                ).execute()

                for item in comments_response.get('items', []):
                    comment = item['snippet']['topLevelComment']['snippet']
                    published_at = datetime.strptime(comment['publishedAt'], "%Y-%m-%dT%H:%M:%SZ")

                    # Apply date filtering if specified
                    if start_date and published_at < start_date:
                        continue
                    if end_date and published_at > end_date:
                        continue

                    all_comments.append({
                        'comment_id': item['id'],
                        'video_id': video_id,
                        'text': comment['textDisplay'],
                        'author_name': comment['authorDisplayName'],
                        'author_id': comment['authorChannelId']['value'],
                        'published_at': published_at,
                        'like_count': comment['likeCount']
                    })

                    if len(all_comments) >= max_results:
                        break

            except HttpError as e:
                logger.warning(f"Error getting comments for video {video_id}: {e}")
                continue

            if len(all_comments) >= max_results:
                break

        # Sort by publication date (newest first)
        all_comments.sort(key=lambda x: x['published_at'], reverse=True)
        return all_comments

    except HttpError as e:
        logger.error(f"Error retrieving comments: {e}")
        return []

def reply_to_comment(youtube_service, comment_id, reply_text):
    """
    Post a reply to a YouTube comment.

    Args:
        youtube_service: The YouTube API service object
        comment_id: The ID of the comment to reply to
        reply_text: The text of the reply

    Returns:
        The reply comment object if successful, None otherwise
    """
    try:
        response = youtube_service.comments().insert(
            part="snippet",
            body={
                "snippet": {
                    "parentId": comment_id,
                    "textOriginal": reply_text
                }
            }
        ).execute()

        return {
            'comment_id': response['id'],
            'text': response['snippet']['textOriginal'],
            'published_at': datetime.strptime(response['snippet']['publishedAt'], "%Y-%m-%dT%H:%M:%SZ")
        }

    except HttpError as e:
        logger.error(f"Error replying to comment {comment_id}: {e}")
        return None