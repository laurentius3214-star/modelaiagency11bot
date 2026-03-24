import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters, ContextTypes
from datetime import datetime
import config
from database import Database
from message_handler import MessageSender

# Conversation states
WAITING_FOR_USERNAMES = 1
WAITING_FOR_MESSAGE = 2
CONFIRM_SEND = 3

class TelegramDMBot:
    def __init__(self):
        self.db = Database()
        self.message_sender = None
        self.user_data = {}  # Store temporary data per user
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command handler"""
        user = update.effective_user
        self.db.register_user(
            user.id, 
            user.username, 
            user.first_name, 
            user.last_name
        )
        
        welcome_text = f"""
🎯 *Welcome to Telegram DM Bot, {user.first_name}!*

This bot helps you send direct messages to Telegram users using your account.

*Commands:*
/send - Start a new DM campaign
/status - Check your campaign history
/help - Show this help message
/cancel - Cancel current operation

*Important Notes:*
• Maximum {config.Config.MAX_RECIPIENTS} recipients per campaign
• Messages will be sent from YOUR account
• Please respect Telegram's rate limits
• Do not send spam messages

To start, use /send command.
        """
        
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Help command"""
        help_text = """
*How to use this bot:*

1. *Start a campaign:* Use /send
2. *Enter usernames:* Send usernames (one per line)
   - Maximum 50 usernames
   - Format: username or @username
3. *Enter your message:* Type your message
4. *Confirm:* Review and confirm to send

*Commands:*
/send - Start new DM campaign
/status - View your past campaigns
/cancel - Cancel current operation
/help - Show this help

*Tips:*
• Each username should be on a new line
• Messages will be sent with a delay to avoid rate limits
• Check /status for campaign results
        """
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def send_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start send conversation"""
        await update.message.reply_text(
            f"📝 *Start New DM Campaign*\n\n"
            f"Please send me the usernames (one per line).\n"
            f"Maximum: {config.Config.MAX_RECIPIENTS} recipients\n\n"
            f"Example:\n"
            f"username1\n"
            f"@username2\n"
            f"username3\n\n"
            f"Send /cancel to cancel.",
            parse_mode='Markdown'
        )
        return WAITING_FOR_USERNAMES
    
    async def receive_usernames(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive and validate usernames"""
        text = update.message.text
        
        if text == '/cancel':
            await update.message.reply_text("❌ Operation cancelled.")
            return ConversationHandler.END
        
        # Parse usernames
        usernames = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Remove @ if present
        usernames = [u[1:] if u.startswith('@') else u for u in usernames]
        
        # Validate
        if len(usernames) > config.Config.MAX_RECIPIENTS:
            await update.message.reply_text(
                f"❌ Too many recipients! Maximum is {config.Config.MAX_RECIPIENTS}.\n"
                f"You provided {len(usernames)}. Please try again with fewer recipients.\n"
                f"Send /cancel to cancel."
            )
            return WAITING_FOR_USERNAMES
        
        if len(usernames) < config.Config.MIN_RECIPIENTS:
            await update.message.reply_text(
                f"❌ At least {config.Config.MIN_RECIPIENTS} recipient is required.\n"
                f"Please provide at least one username.\n"
                f"Send /cancel to cancel."
            )
            return WAITING_FOR_USERNAMES
        
        # Store in user_data
        user_id = update.effective_user.id
        self.user_data[user_id] = {
            'recipients': usernames,
            'recipient_count': len(usernames)
        }
        
        # Show preview
        preview = "\n".join([f"• {u}" for u in usernames[:10]])
        if len(usernames) > 10:
            preview += f"\n... and {len(usernames) - 10} more"
        
        await update.message.reply_text(
            f"✅ *Recipients saved!*\n\n"
            f"📊 Total: {len(usernames)} recipient(s)\n\n"
            f"*Preview:*\n{preview}\n\n"
            f"Now, please send me the message you want to send to these users.\n\n"
            f"Send /cancel to cancel.",
            parse_mode='Markdown'
        )
        
        return WAITING_FOR_MESSAGE
    
    async def receive_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive the message to send"""
        text = update.message.text
        user_id = update.effective_user.id
        
        if text == '/cancel':
            await update.message.reply_text("❌ Operation cancelled.")
            return ConversationHandler.END
        
        # Store message
        self.user_data[user_id]['message'] = text
        
        # Show confirmation
        recipients = self.user_data[user_id]['recipients']
        message = self.user_data[user_id]['message']
        
        confirm_text = f"""
📨 *Campaign Ready for Confirmation*

*Recipients:* {len(recipients)} user(s)
*Message:* 
{message[:200]}{'...' if len(message) > 200 else ''}

⚠️ *Important:*
• Messages will be sent from YOUR Telegram account
• Each message will have a {config.Config.DEFAULT_DELAY} second delay
• You cannot undo this action once started

Do you want to proceed?

Send *YES* to confirm or *NO* to cancel.
        """
        
        await update.message.reply_text(confirm_text, parse_mode='Markdown')
        return CONFIRM_SEND
    
    async def confirm_send(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Confirm and send messages"""
        text = update.message.text.upper()
        user_id = update.effective_user.id
        
        if text == '/cancel' or text == 'NO':
            await update.message.reply_text("❌ Campaign cancelled.")
            return ConversationHandler.END
        
        if text != 'YES':
            await update.message.reply_text(
                "Please send *YES* to confirm or *NO* to cancel.\n"
                "Send /cancel to abort.",
                parse_mode='Markdown'
            )
            return CONFIRM_SEND
        
        # Get campaign data
        data = self.user_data.get(user_id)
        if not data:
            await update.message.reply_text("❌ Session expired. Please start over with /send.")
            return ConversationHandler.END
        
        recipients = data['recipients']
        message = data['message']
        
        # Create campaign in database
        campaign_id = self.db.create_campaign(user_id, message, recipients)
        
        # Send initial status
        status_msg = await update.message.reply_text(
            f"🚀 *Campaign Started!*\n\n"
            f"📊 Sending to {len(recipients)} recipient(s)...\n"
            f"🆔 Campaign ID: {campaign_id}\n\n"
            f"Please wait, this may take a few minutes...",
            parse_mode='Markdown'
        )
        
        # Initialize message sender if not already
        if not self.message_sender:
            self.message_sender = MessageSender(self.db)
            if not await self.message_sender.initialize_client():
                await status_msg.edit_text(
                    "❌ Failed to initialize message sender. Please check your account credentials."
                )
                return ConversationHandler.END
        
        # Progress tracking
        async def update_progress(current, total, successful, failed):
            progress_text = f"""
🚀 *Campaign in Progress*
🆔 Campaign ID: {campaign_id}

📊 Progress: {current}/{total}
✅ Successful: {successful}
❌ Failed: {failed}
⏳ Remaining: {total - current}

Please wait...
            """
            try:
                await status_msg.edit_text(progress_text, parse_mode='Markdown')
            except:
                pass  # Ignore edit errors
        
        # Send messages
        successful, failed, results = await self.message_sender.send_bulk_messages(
            campaign_id, recipients, message, update_progress
        )
        
        # Prepare final report
        success_list = [r for r in results if r.startswith('✅')]
        failed_list = [r for r in results if r.startswith('❌')]
        
        final_report = f"""
✅ *Campaign Completed!*

📊 *Statistics:*
🆔 Campaign ID: {campaign_id}
✅ Successful: {successful}
❌ Failed: {failed}
📈 Success Rate: {(successful/(successful+failed)*100):.1f}%

*Successful Sends:* {len(success_list)}/{len(recipients)}
*Failed Sends:* {len(failed_list)}/{len(recipients)}

{f'*Failed Details:*\n' + '\n'.join(failed_list[:5]) if failed_list else ''}
{'...' if len(failed_list) > 5 else ''}

Use /status to view all your campaigns.
        """
        
        await status_msg.edit_text(final_report, parse_mode='Markdown')
        
        # Clean up user data
        if user_id in self.user_data:
            del self.user_data[user_id]
        
        return ConversationHandler.END
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show campaign status"""
        user_id = update.effective_user.id
        campaigns = self.db.get_user_campaigns(user_id)
        
        if not campaigns:
            await update.message.reply_text(
                "📭 No campaigns found. Use /send to create your first campaign."
            )
            return
        
        status_text = "*📊 Your Campaign History*\n\n"
        
        for campaign in campaigns:
            campaign_id, message, total, successful, failed, status, created_at, completed_at = campaign
            status_emoji = {
                'pending': '⏳',
                'completed': '✅',
                'partial': '⚠️',
                'failed': '❌'
            }.get(status, '❓')
            
            status_text += f"*{status_emoji} Campaign #{campaign_id}*\n"
            status_text += f"📅 {created_at[:10]}\n"
            status_text += f"📊 {successful}/{total} successful\n"
            status_text += f"📝 {message[:50]}...\n"
            status_text += f"Status: {status}\n\n"
        
        status_text += "Use /send to start a new campaign."
        
        await update.message.reply_text(status_text, parse_mode='Markdown')
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel current operation"""
        await update.message.reply_text("❌ Operation cancelled.")
        return ConversationHandler.END
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        print(f"Error: {context.error}")
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ An error occurred. Please try again later."
            )
    
    def run(self):
        """Run the bot"""
        # Create application
        application = Application.builder().token(config.Config.BOT_TOKEN).build()
        
        # Add conversation handler for send command
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('send', self.send_command)],
            states={
                WAITING_FOR_USERNAMES: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_usernames)],
                WAITING_FOR_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_message)],
                CONFIRM_SEND: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.confirm_send)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
        )
        
        # Add handlers
        application.add_handler(CommandHandler('start', self.start))
        application.add_handler(CommandHandler('help', self.help))
        application.add_handler(CommandHandler('status', self.status_command))
        application.add_handler(conv_handler)
        application.add_error_handler(self.error_handler)
        
        # Start bot
        print("🤖 Bot started...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    bot = TelegramDMBot()
    bot.run()
