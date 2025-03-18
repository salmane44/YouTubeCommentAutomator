import os
import json
import logging
import requests
from config import GEMINI_API_URL, GEMINI_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

def generate_comment_reply(comment_text):
    """
    Generate a reply to a YouTube comment using Gemini Flash 1.5.
    
    Args:
        comment_text: The text of the comment to reply to
        
    Returns:
        The generated reply text if successful, None otherwise
    """
    try:
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            logger.error("GEMINI_API_KEY environment variable is not set")
            return None
            
        # Prepare the prompt with the comment text
        prompt = GEMINI_PROMPT_TEMPLATE.format(comment_text=comment_text)
        
        # Prepare the API request
        headers = {
            'Content-Type': 'application/json',
        }
        
        params = {
            'key': api_key
        }
        
        data = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 1024,
                "stopSequences": []
            },
            "safetySettings": [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                }
            ]
        }
        
        # Make the API request
        response = requests.post(
            GEMINI_API_URL,
            headers=headers,
            params=params,
            json=data
        )
        
        if response.status_code != 200:
            logger.error(f"Error from Gemini API: {response.status_code} - {response.text}")
            return None
            
        # Parse the response
        result = response.json()
        
        if not result.get('candidates') or not result['candidates'][0].get('content'):
            logger.error(f"Unexpected response format from Gemini API: {result}")
            return None
            
        # Extract the generated text
        generated_text = result['candidates'][0]['content']['parts'][0]['text']
        
        # Clean up the text (remove quotes, normalize line breaks, etc.)
        generated_text = generated_text.strip()
        
        return generated_text
        
    except Exception as e:
        logger.error(f"Error generating reply with Gemini API: {e}")
        return None
