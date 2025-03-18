import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# YouTube API configuration
YOUTUBE_API_SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'

# Google OAuth configuration
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

# Gemini API configuration
GEMINI_API_URL = os.getenv('GEMINI_API_URL', 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent')

# Application configuration
VERIFICATION_CODE_LENGTH = 6
VERIFICATION_CODE_EXPIRY = 30 * 60  # 30 minutes in seconds
COMMENTS_PER_PAGE = 20

# Session configuration
SESSION_TYPE = 'filesystem'
SESSION_PERMANENT = False
SESSION_USE_SIGNER = True

# Response templates for Gemini
GEMINI_PROMPT_TEMPLATE = """
You are a helpful YouTube comment responder for a channel. 
Please write a friendly, personalized response to the following comment.
Make sure the response is concise (1-3 sentences), conversational, and 
encourages further engagement.

Comment: {comment_text}
"""