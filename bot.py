import asyncio
from pyrogram import Client, filters
from pyrogram.enums import ChatType
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- CONFIGURATION ---
API_ID =  24435985  # Replace with your API ID
API_HASH = "0fec896446625478537e43906a4829f8"  # Replace with your API Hash
BOT_TOKEN = ""  # Replace with your Bot Token

app = Client(
    "ChannelEditorBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# --- STATE MANAGEMENT ---
WAITING_FOR_FORWARD = 0
WAITING_FOR_BUTTONS = 1

user_states = {}
target_posts = {}  # Maps user_id -> {"chat_id": channel_id, "msg_id": message_id}

@app.on_message(filters.private & filters.command("start"))
async def start_command(client, message):
    user_states[message.chat.id] = WAITING_FOR_FORWARD
    await message.reply_text(
        "👋 Welcome to the Channel Editor Bot!\n\n"
        "**Step 1:** Add me as an **Admin** in your channel with the **'Edit Messages'** permission.\n"
        "**Step 2:** Forward the post you want to edit from your channel to me.\n"
        "**Step 3:** Send the new buttons to replace the old ones."
    )

@app.on_message(filters.private & ~filters.command("start"))
async def handle_messages(client, message):
    chat_id = message.chat.id
    current_state = user_states.get(chat_id, WAITING_FOR_FORWARD)

    # --- STEP 1: RECEIVE FORWARDED POST FROM CHANNEL ---
    if current_state == WAITING_FOR_FORWARD:
        
        # Verify the message was actually forwarded from a channel
        if not message.forward_from_chat or message.forward_from_chat.type != ChatType.CHANNEL:
            await message.reply_text("⚠️ Please forward a message directly from your **Channel**.")
            return
        
        # Extract the original channel ID and the message ID inside that channel
        channel_id = message.forward_from_chat.id
        original_msg_id = message.forward_from_message_id
        
        # Save this data
        target_posts[chat_id] = {"chat_id": channel_id, "msg_id": original_msg_id}
        user_states[chat_id] = WAITING_FOR_BUTTONS
        
        await message.reply_text(
            f"✅ **Target Post Locked!**\n"
            f"Channel: {message.forward_from_chat.title}\n"
            f"Message ID: `{original_msg_id}`\n\n"
            "Now, send me the new buttons in this format:\n"
            "`Download Now - https://example.com`\n\n"
            "*(Use `|` for multiple buttons on the same line)*"
        )

    # --- STEP 2: RECEIVE BUTTONS AND EDIT CHANNEL POST ---
    elif current_state == WAITING_FOR_BUTTONS:
        if not message.text:
            await message.reply_text("⚠️ Please send text containing the button layout.")
            return

        post_data = target_posts.get(chat_id)
        if not post_data:
            await message.reply_text("⚠️ I lost track of the post. Please forward it again.")
            user_states[chat_id] = WAITING_FOR_FORWARD
            return

        # Parse the text into an inline keyboard
        lines = message.text.split('\n')
        keyboard = []
        
        for line in lines:
            row = []
            buttons = line.split('|')
            for btn in buttons:
                if " - " in btn:
                    try:
                        text, url = btn.split(" - ", 1)
                        row.append(InlineKeyboardButton(text.strip(), url=url.strip()))
                    except ValueError:
                        continue
            if row:
                keyboard.append(row)

        if not keyboard:
            await message.reply_text(
                "❌ **Invalid Format!**\n"
                "Make sure you use ` - ` to separate the name and URL. Try sending it again."
            )
            return

        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            # This directly edits the buttons on the original post in the channel!
            await client.edit_message_reply_markup(
                chat_id=post_data["chat_id"],
                message_id=post_data["msg_id"],
                reply_markup=reply_markup
            )
            
            await message.reply_text(
                "🎉 **Success!** The buttons on the original channel post have been updated. "
                "The message ID remains exactly the same.\n\n"
                "Forward another post to start over."
            )
            
            # Reset state for the next post
            user_states[chat_id] = WAITING_FOR_FORWARD
            
        except Exception as e:
            await message.reply_text(
                f"❌ **Failed to edit post.**\n\n"
                f"**Did you forget?** I must be an Admin in the channel with 'Edit Messages' enabled.\n"
                f"Error details: `{e}`"
            )

if __name__ == "__main__":
    print("Bot is starting...")
    app.run()
