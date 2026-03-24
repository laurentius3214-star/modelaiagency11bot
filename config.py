import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_ID = int(os.getenv('API_ID'))
    API_HASH = os.getenv('API_HASH')
    PHONE_NUMBER = os.getenv('PHONE_NUMBER')
    SESSION_STRING = os.getenv('SESSION_STRING', None)  # Optional: use string session
    MESSAGE_FILE = os.getenv('MESSAGE_FILE', 'messages.txt')
    RECIPIENTS_FILE = os.getenv('RECIPIENTS_FILE', 'recipients.txt')import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Bot Token
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    
    # User Account for sending DMs
    API_ID = int(os.getenv('API_ID'))
    API_HASH = os.getenv('API_HASH')
    PHONE_NUMBER = os.getenv('PHONE_NUMBER')
    SESSION_STRING = os.getenv('SESSION_STRING')
    
    # Limits
    MAX_RECIPIENTS = int(os.getenv('MAX_RECIPIENTS', 50))
    MIN_RECIPIENTS = int(os.getenv('MIN_RECIPIENTS', 1))
    DEFAULT_DELAY = int(os.getenv('DEFAULT_DELAY', 3))
    
    # File paths
    SESSION_NAME = 'telegram_session'
    DELAY_BETWEEN_MESSAGES = int(os.getenv('DELAY_BETWEEN_MESSAGES', 5))
    MAX_MESSAGES_PER_HOUR = int(os.getenv('MAX_MESSAGES_PER_HOUR', 60))
    SESSION_NAME = os.getenv('SESSION_NAME', 'telegram_session')
