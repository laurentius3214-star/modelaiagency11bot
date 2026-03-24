import asyncio
import random
import time
import os
from datetime import datetime
from telethon import TelegramClient, errors
from telethon.sessions import StringSession
from config import Config

class MessageHandler:
    def __init__(self):
        # Initialize client based on whether we have a session string or not
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
        self.message_count = 0
        self.hour_start_time = time.time()
        self.successful_sends = []
        self.failed_sends = []
        
    async def start_client(self):
        """Start the Telegram client"""
        try:
            if Config.SESSION_STRING:
                # Using string session, no phone number needed if session is valid
                await self.client.start()
            else:
                # Using file session, need phone number for initial auth
                await self.client.start(phone=Config.PHONE_NUMBER)
            
            me = await self.client.get_me()
            print(f"✅ Client started as: {me.first_name} (@{me.username})")
            return True
        except Exception as e:
            print(f"❌ Failed to start client: {str(e)}")
            return False
        
    async def read_recipients(self):
        """Read recipients from file"""
        try:
            if not os.path.exists(Config.RECIPIENTS_FILE):
                print(f"⚠️ {Config.RECIPIENTS_FILE} not found, creating empty file")
                with open(Config.RECIPIENTS_FILE, 'w') as f:
                    pass
                return []
                
            with open(Config.RECIPIENTS_FILE, 'r', encoding='utf-8') as f:
                recipients = [line.strip() for line in f if line.strip()]
            
            # Remove duplicates while preserving order
            seen = set()
            unique_recipients = []
            for r in recipients:
                if r not in seen:
                    seen.add(r)
                    unique_recipients.append(r)
                    
            return unique_recipients
        except Exception as e:
            print(f"❌ Error reading recipients: {str(e)}")
            return []
    
    async def read_messages(self):
        """Read messages from file"""
        try:
            if not os.path.exists(Config.MESSAGE_FILE):
                print(f"⚠️ {Config.MESSAGE_FILE} not found, using default message")
                return ["Hello! This is an automated message from Telegram DM Bot."]
                
            with open(Config.MESSAGE_FILE, 'r', encoding='utf-8') as f:
                messages = [line.strip() for line in f if line.strip()]
            
            if not messages:
                print("⚠️ No messages found, using default")
                return ["Hello! This is an automated message from Telegram DM Bot."]
                
            return messages
        except Exception as e:
            print(f"❌ Error reading messages: {str(e)}")
            return ["Hello! This is an automated message from Telegram DM Bot."]
    
    async def check_rate_limit(self):
        """Check and enforce hourly rate limit"""
        current_time = time.time()
        
        # Reset hourly counter if hour has passed
        if current_time - self.hour_start_time >= 3600:
            self.message_count = 0
            self.hour_start_time = current_time
            print("📊 Hourly counter reset")
        elif self.message_count >= Config.MAX_MESSAGES_PER_HOUR:
            wait_time = 3600 - (current_time - self.hour_start_time)
            minutes = wait_time / 60
            print(f"⏰ Hourly limit reached ({Config.MAX_MESSAGES_PER_HOUR}/hour). Waiting {minutes:.1f} minutes")
            await asyncio.sleep(wait_time)
            self.message_count = 0
            self.hour_start_time = time.time()
    
    async def send_message_to_recipient(self, recipient, message):
        """Send a single message with error handling"""
        try:
            # Clean recipient format
            recipient = recipient.strip()
            if recipient.startswith('@'):
                recipient = recipient[1:]  # Remove @ if present
            
            # Try to get entity
            entity = await self.client.get_entity(recipient)
            
            # Send message
            result = await self.client.send_message(entity, message)
            
            self.message_count += 1
            print(f"✅ Sent to {recipient} at {datetime.now().strftime('%H:%M:%S')}")
            return True, None
            
        except errors.FloodWaitError as e:
            wait_time = e.seconds
            print(f"🌊 Flood wait for {recipient}: {wait_time} seconds")
            await asyncio.sleep(min(wait_time, 3600))  # Max wait 1 hour
            return False, "Flood wait"
            
        except errors.rpcerrorlist.UserIsBlockedError:
            print(f"🚫 User {recipient} has blocked the account")
            return False, "User blocked"
            
        except errors.rpcerrorlist.PeerIdInvalidError:
            print(f"❌ Invalid ID/username: {recipient}")
            return False, "Invalid username/ID"
            
        except errors.rpcerrorlist.UserPrivacyRestrictedError:
            print(f"🔒 User {recipient} has privacy settings preventing messages")
            return False, "Privacy restricted"
            
        except errors.rpcerrorlist.BotMethodInvalidError:
            print(f"🤖 {recipient} is a bot (bots cannot receive DMs like this)")
            return False, "Bot account"
            
        except errors.rpcerrorlist.InputUserDeactivatedError:
            print(f"💀 User {recipient} account deactivated")
            return False, "Account deactivated"
            
        except ValueError as e:
            if "Cannot find any entity" in str(e):
                print(f"❌ Cannot find user: {recipient}")
                return False, "User not found"
            else:
                print(f"❌ ValueError: {str(e)}")
                return False, str(e)
                
        except Exception as e:
            print(f"❌ Failed to send to {recipient}: {str(e)[:100]}")
            return False, str(e)[:100]
    
    async def send_bulk_messages(self):
        """Send messages to all recipients"""
        recipients = await self.read_recipients()
        messages = await self.read_messages()
        
        if not recipients:
            print("❌ No recipients found. Please add recipients to recipients.txt")
            print("Format: one username, phone number, or user ID per line")
            return
        
        print("\n" + "="*60)
        print(f"📊 BULK MESSAGING CONFIGURATION:")
        print(f"   - Recipients: {len(recipients)}")
        print(f"   - Messages: {len(messages)}")
        print(f"   - Delay between messages: {Config.DELAY_BETWEEN_MESSAGES}s")
        print(f"   - Hourly rate limit: {Config.MAX_MESSAGES_PER_HOUR}/hour")
        print(f"   - Estimated total time: ~{len(recipients) * Config.DELAY_BETWEEN_MESSAGES / 60:.1f} minutes")
        print("="*60 + "\n")
        
        # Confirm before sending (optional)
        if os.getenv('CONFIRM_BEFORE_SEND', 'true').lower() == 'true':
            confirm = input("⚠️  Ready to start sending messages? (yes/no): ")
            if confirm.lower() != 'yes':
                print("❌ Operation cancelled by user")
                return
        
        success_count = 0
        start_time = time.time()
        
        for idx, recipient in enumerate(recipients, 1):
            # Rotate through messages if multiple
            message = messages[(idx - 1) % len(messages)]
            
            print(f"[{idx}/{len(recipients)}] Processing: {recipient}")
            
            # Check rate limit before each send
            await self.check_rate_limit()
            
            # Send message
            success, error = await self.send_message_to_recipient(recipient, message)
            
            if success:
                success_count += 1
                self.successful_sends.append(recipient)
            else:
                self.failed_sends.append({'recipient': recipient, 'error': error})
            
            # Add delay between messages (with random variation)
            if idx < len(recipients):  # Don't delay after last message
                delay = Config.DELAY_BETWEEN_MESSAGES + random.uniform(0, 2)
                await asyncio.sleep(delay)
        
        # Calculate statistics
        elapsed_time = time.time() - start_time
        success_rate = (success_count / len(recipients)) * 100 if recipients else 0
        
        print("\n" + "="*60)
        print(f"📈 FINAL SUMMARY:")
        print(f"   - Total recipients: {len(recipients)}")
        print(f"   - Successful: {success_count}")
        print(f"   - Failed: {len(recipients) - success_count}")
        print(f"   - Success rate: {success_rate:.1f}%")
        print(f"   - Total time: {elapsed_time/60:.1f} minutes")
        print(f"   - Messages/hour: {self.message_count / (elapsed_time/3600):.1f}")
        print("="*60)
        
        # Show failed recipients if any
        if self.failed_sends:
            print("\n❌ Failed recipients:")
            for failed in self.failed_sends[:10]:  # Show first 10 failures
                print(f"   - {failed['recipient']}: {failed['error']}")
            if len(self.failed_sends) > 10:
                print(f"   ... and {len(self.failed_sends) - 10} more")
        
        # Save log
        await self.save_log()
        
        return success_count
    
    async def save_log(self):
        """Save execution log to file"""
        try:
            log_filename = f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(log_filename, 'w', encoding='utf-8') as f:
                f.write(f"Telegram DM Bot Log - {datetime.now()}\n")
                f.write("="*50 + "\n\n")
                f.write(f"Total recipients: {len(self.successful_sends) + len(self.failed_sends)}\n")
                f.write(f"Successful: {len(self.successful_sends)}\n")
                f.write(f"Failed: {len(self.failed_sends)}\n\n")
                
                if self.successful_sends:
                    f.write("SUCCESSFUL SENDS:\n")
                    for recipient in self.successful_sends:
                        f.write(f"  ✓ {recipient}\n")
                    f.write("\n")
                
                if self.failed_sends:
                    f.write("FAILED SENDS:\n")
                    for failed in self.failed_sends:
                        f.write(f"  ✗ {failed['recipient']}: {failed['error']}\n")
            
            print(f"\n📝 Log saved to: {log_filename}")
        except Exception as e:
            print(f"⚠️ Could not save log: {str(e)}")
    
    async def run(self):
        """Main execution flow"""
        try:
            # Start client
            if not await self.start_client():
                print("❌ Cannot proceed without client connection")
                return
            
            # Send messages
            await self.send_bulk_messages()
            
        except KeyboardInterrupt:
            print("\n⚠️ Bot interrupted by user")
            
        except Exception as e:
            print(f"❌ Fatal error: {str(e)}")
            import traceback
            traceback.print_exc()
            
        finally:
            await self.client.disconnect()
            print("🔌 Client disconnected")
