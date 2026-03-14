"""
PagerDuty AE Assistant - Telegram Bot
Powered by Claude (Anthropic API)

What this does:
- You message your Telegram bot
- It sends your message to Claude with your AE context baked in
- Claude replies, you get the answer in Telegram
"""

import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

import anthropic

# ── Logging (shows what's happening in your terminal) ──────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ── Your keys (loaded from environment variables — never hardcode these) ────────
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]      # from BotFather
ANTHROPIC_KEY  = os.environ["ANTHROPIC_API_KEY"]   # from console.anthropic.com

# ── Claude client ───────────────────────────────────────────────────────────────
client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

# ── System prompt: this is what makes Claude "know" who you are ─────────────────
# Edit this freely — the more context, the better Claude's answers
SYSTEM_PROMPT = """
You are a sharp, experienced sales assistant for a PagerDuty Account Executive.

Context about the AE:
- Sells PagerDuty (incident management, AIOps, on-call scheduling, operations cloud)
- Focuses on mid-market and enterprise accounts
- Competes mainly against Opsgenie (Atlassian), VictorOps (Splunk), and homegrown tools
- Key buyers: VP Engineering, CTO, DevOps/SRE leads, and sometimes CFO for larger deals
- Core value props: reduce MTTR, eliminate alert fatigue, improve developer experience, prove ROI on reliability

Your job:
- Help craft personalized outreach emails and LinkedIn messages
- Build discovery call frameworks and objection handling responses
- Research companies and suggest outreach angles
- Write follow-up emails from meeting notes
- Build business cases and ROI arguments
- Give competitive intel and battle card talking points
- Suggest champion enablement strategies

Tone: Direct, concise, no fluff. Sound like a sharp colleague, not a corporate tool.
When writing emails or messages, make them human — not AI-sounding.
Always ask for clarification if the request is vague (e.g. "what's the persona?" or "what stage is this deal?").
"""

# ── Conversation memory (per user, resets when bot restarts) ────────────────────
# Key = Telegram user ID, Value = list of messages
conversation_history: dict[int, list] = {}

MAX_HISTORY = 20  # keep last 20 messages to avoid hitting token limits


# ── /start command ──────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hey! I'm your PagerDuty AE assistant.\n\n"
        "Ask me anything — outreach emails, discovery frameworks, competitive intel, "
        "follow-ups, ROI talking points. Let's close some deals.\n\n"
        "Type /reset anytime to start a fresh conversation."
    )


# ── /reset command — clears conversation memory ─────────────────────────────────
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conversation_history[user_id] = []
    await update.message.reply_text("🔄 Conversation cleared. Fresh start!")


# ── Main message handler ────────────────────────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id   = update.effective_user.id
    user_text = update.message.text

    # Initialize history for new users
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    # Add the user's message to history
    conversation_history[user_id].append({
        "role": "user",
        "content": user_text
    })

    # Trim history if it gets too long
    if len(conversation_history[user_id]) > MAX_HISTORY:
        conversation_history[user_id] = conversation_history[user_id][-MAX_HISTORY:]

    # Show "typing..." indicator in Telegram
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    try:
        # Call Claude API
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=conversation_history[user_id]
        )

        reply = response.content[0].text

        # Add Claude's reply to history so it remembers the conversation
        conversation_history[user_id].append({
            "role": "assistant",
            "content": reply
        })

        await update.message.reply_text(reply)

    except Exception as e:
        logging.error(f"Error calling Claude: {e}")
        await update.message.reply_text(
            "⚠️ Something went wrong. Try again in a moment."
        )


# ── Run the bot ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot is running... Press Ctrl+C to stop.")
    app.run_polling()
