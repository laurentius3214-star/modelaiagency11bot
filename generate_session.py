import asyncio
import os
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession

load_dotenv()

async def generate_session():
    api_id = int(os.getenv('API_ID'))
    api_hash = os.getenv('API_HASH')
    phone = os.getenv('PHONE_NUMBER')
    
    print("🔄 Generating session string...")
    
    async with TelegramClient(StringSession(), api_id, api_hash) as client:
        await client.start(phone=phone)
        session_string = client.session.save()
        
        print("\n✅ Session string generated!")
        print("\n📝 Add this to your .env file:")
        print(f"SESSION_STRING={session_string}")
        print("\n⚠️  Keep this secure!")

if __name__ == "__main__":
    asyncio.run(generate_session())
