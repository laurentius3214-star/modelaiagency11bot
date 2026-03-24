import asyncio
import time
from datetime import datetime
from telethon import TelegramClient, errors
from telethon.sessions import StringSession
from config import Config

class MessageSender:
    def __init__(self, db):
        self.db = db
        self.client = None
        self.message_count = 0
        self.hour_start_time = time.time()
        
    async def initialize_client(self):
        """Initialize the Telegram client for sending DMs"""
        try:
            if Config.SESSION_STRING:
                self.client = TelegramClient(
                    StringSession(Config.SESSION_STRING),
                    Config.API_ID,
                    Config.API_HASH
                )
            else:
                self.client = TelegramClient(
                    Config.SESSION_NAME,
                    Config.API_ID,
                    Config.API_HASH
                )
            
            await self.client.start(phone=Config.PHONE_NUMBER)
            me = await self.client.get_me()
            print(f"✅ DM Sender initialized: {me.first_name}")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize DM sender: {e}")
            return False
    
    async def check_rate_limit(self):
        """Check hourly rate limit"""
        current_time = time.time()
        if current_time - self.hour_start_time >= 3600:
            self.message_count = 0
            self.hour_start_time = current_time
        elif self.message_count >= 60:  # Telegram's typical limit
            wait_time = 3600 - (current_time - self.hour_start_time)
            await asyncio.sleep(wait_time)
            self.message_count = 0
            self.hour_start_time = time.time()
    
    async def send_message_to_recipient(self, recipient, message, campaign_id):
        """Send message to a single recipient"""
        try:
            # Clean recipient
            recipient = recipient.strip()
            if recipient.startswith('@'):
                recipient = recipient[1:]
            
            # Get entity and send message
            entity = await self.client.get_entity(recipient)
            await self.client.send_message(entity, message)
            
            self.message_count += 1
            
            # Log success
            self.db.add_message_log(campaign_id, recipient, 'success')
            return True, None
            
        except errors.FloodWaitError as e:
            self.db.add_message_log(campaign_id, recipient, 'failed', f'Flood wait: {e.seconds}s')
            return False, f"Rate limited, wait {e.seconds}s"
            
        except errors.rpcerrorlist.UserIsBlockedError:
            self.db.add_message_log(campaign_id, recipient, 'failed', 'User blocked bot')
            return False, "User has blocked you"
            
        except errors.rpcerrorlist.PeerIdInvalidError:
            self.db.add_message_log(campaign_id, recipient, 'failed', 'Invalid username')
            return False, "Invalid username"
            
        except errors.rpcerrorlist.UserPrivacyRestrictedError:
            self.db.add_message_log(campaign_id, recipient, 'failed', 'Privacy restricted')
            return False, "User's privacy settings prevent messages"
            
        except errors.rpcerrorlist.BotMethodInvalidError:
            self.db.add_message_log(campaign_id, recipient, 'failed', 'Cannot message bots')
            return False, "Cannot send messages to bots"
            
        except ValueError as e:
            error_msg = "User not found" if "Cannot find any entity" in str(e) else str(e)
            self.db.add_message_log(campaign_id, recipient, 'failed', error_msg)
            return False, error_msg
            
        except Exception as e:
            self.db.add_message_log(campaign_id, recipient, 'failed', str(e)[:100])
            return False, str(e)[:100]
    
    async def send_bulk_messages(self, campaign_id, recipients, message, progress_callback=None):
        """Send messages to all recipients"""
        successful = 0
        failed = 0
        results = []
        
        for idx, recipient in enumerate(recipients, 1):
            # Check rate limit
            await self.check_rate_limit()
            
            # Send message
            success, error = await self.send_message_to_recipient(recipient, message, campaign_id)
            
            if success:
                successful += 1
                results.append(f"✅ {recipient}")
            else:
                failed += 1
                results.append(f"❌ {recipient}: {error}")
            
            # Send progress update if callback provided
            if progress_callback:
                await progress_callback(idx, len(recipients), successful, failed)
            
            # Delay between messages
            if idx < len(recipients):
                await asyncio.sleep(Config.DEFAULT_DELAY)
        
        # Update campaign in database
        status = 'completed' if failed == 0 else 'partial' if successful > 0 else 'failed'
        self.db.update_campaign(campaign_id, successful, failed, status)
        
        return successful, failed, results
    
    async def disconnect(self):
        """Disconnect the client"""
        if self.client:
            await self.client.disconnect()
