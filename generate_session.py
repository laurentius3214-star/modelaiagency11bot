"""
Run this script once locally to generate a session string for Render deployment
This avoids needing to upload session files
"""

import asyncio
import os
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession

load_dotenv()

async def generate_session():
    """Generate a session string for deployment"""
    api_id = int(os.getenv('API_ID'))
    api_hash = os.getenv('API_HASH')
    phone = os.getenv('PHONE_NUMBER')
    
    if not all([api_id, api_hash, phone]):
        print("❌ Missing API_ID, API_HASH, or PHONE_NUMBER in .env")
        return
    
    print("🔄 Creating session string...")
    
    async with TelegramClient(StringSession(), api_id, api_hash) as client:
        await client.start(phone=phone)
        session_string = client.session.save()
        
        print("\n✅ Session string generated successfully!")
        print("\n📝 Add this to your Render environment variables:")
        print("="*60)
        print(f"SESSION_STRING={session_string}")
        print("="*60)
        print("\n⚠️  Keep this string secure! It gives full access to your Telegram account.")

if __name__ == "__main__":
    asyncio.run(generate_session())
