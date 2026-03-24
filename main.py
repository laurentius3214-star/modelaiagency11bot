import asyncio
import sys
import os
from message_handler import MessageHandler

async def main():
    print("="*60)
    print("🚀 Telegram DM Bot Starting...")
    print("="*60)
    
    # Check required environment variables
    required_vars = ['API_ID', 'API_HASH']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set them in .env file or Render environment variables")
        sys.exit(1)
    
    # Create handler and run
    handler = MessageHandler()
    await handler.run()
    
    print("\n✨ Bot execution completed")
    print("="*60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)
