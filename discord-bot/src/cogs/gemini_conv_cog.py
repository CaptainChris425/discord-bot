# Description: This file contains the GeminiConvCog class, which is a cog for the Discord bot that interacts with the Gemini Vertex AI API and includes conversation capabilities.
import discord
from discord.ext import commands
import os
import vertexai
from vertexai.generative_models import GenerativeModel
from vertexai.generative_models import Part
from vertexai.preview.vision_models import ImageGenerationModel
import aiohttp
import asyncio
from gtts import gTTS
from google.cloud import storage, vision
import logging
from utils.helpers import *

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
DEBUG_GUILD_ID = os.getenv('DEBUG_GUILD_ID', 123456789012345678)
CONVERSATION_CHANNEL_NAME = os.getenv('CONVERSATION_CHANNEL_NAME', 'ai-chatroom')
BLACKJACK_CHANNEL_NAME = os.getenv('BLACKJACK_CHANNEL_NAME', 'blackjack-ai-bot')

channel_names = [CONVERSATION_CHANNEL_NAME, BLACKJACK_CHANNEL_NAME]
channel_names_str = ', '.join(channel_names)
logger.info(f"DEBUG: {DEBUG}, DEBUG_GUILD_ID: {DEBUG_GUILD_ID}, CHANNEL_NAMES: {channel_names_str}")

class GeminiConvCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT_ID')
        self.location = 'us-central1'  # Change this to your Vertex AI location
        self.bucket_name = os.getenv('GCS_BUCKET_NAME')
        self.model = GenerativeModel("gemini-1.5-flash-002")
        # Initialize the Vertex AI client
        vertexai.init(project=self.project_id, location=self.location)
        self.conversation_histories = {}
        self.chat_session_active = True
        self.chat_voice_active = False
        self.message_counts_since_reset = {}
        self.number_of_messages_to_track = 20

        # Define a dictionary mapping channel names to handler functions
        self.channel_handlers = {
            CONVERSATION_CHANNEL_NAME: self.handle_conversation_channel,
            BLACKJACK_CHANNEL_NAME: self.handle_blackjack_channel,
            # Add more channels and their corresponding handler functions here
        }

    def check_debug_mode(self, ctx):
        if DEBUG and ctx.guild.id != DEBUG_GUILD_ID:
            logger.info(f"Debug mode is enabled. This command is only available in the debug server. ctx.guild.id: {ctx.guild.id}, DEBUG_GUILD_ID: {DEBUG_GUILD_ID}")
            return False
        return True

    async def fetch_conversation_history(self, channel, limit=10):
        """Fetch the last 'limit' messages from the specified channel."""
        self.conversation_histories[channel.guild.id][channel.name] = []
        async for message in channel.history(limit=limit, oldest_first=False):
            self.conversation_histories[channel.guild.id][channel.name].append(f"{message.author.name}: {message.content}")
        self.conversation_histories[channel.guild.id][channel.name].reverse()  # Ensure the messages are in chronological order

    async def update_conversation_history(self, message):
        """Update the conversation history with the new message."""
        if len(self.conversation_histories[message.guild.id][message.channel.name]) > self.number_of_messages_to_track:
            self.conversation_histories[message.guild.id][message.channel.name].pop(0)

    async def reset_conversation_history(self, guild_id, channel_name):
        """Reset the conversation history for the specified channel."""
        self.message_counts_since_reset[guild_id][channel_name] = 0
        self.conversation_histories[guild_id][channel_name] = []

    @commands.command(name='ai-chat')
    async def toggle_chat_session(self, ctx):
        """Toggles the chat session on and off."""
        logger.info(f"{ctx.author} called the ai-chat command")
        if not self.check_debug_mode(ctx):
            return

        self.chat_session_active = not self.chat_session_active
        status = "started" if self.chat_session_active else "stopped"
        await ctx.send(f"Chat session {status}.")

    @commands.command(name='ai-chat-stop')
    async def gemini_stop(self, ctx):
        """Stops the bot from speaking"""
        logger.info(f"{ctx.author} called the ai-stop command")
        if not self.check_debug_mode(ctx):
            return
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()

    @commands.command(name='ai-chat-status')
    async def chat_session_status(self, ctx):
        """Displays the status of the chat session."""
        logger.info(f"{ctx.author} called the ai-chat-status command")
        if not self.check_debug_mode(ctx):
            return

        status = "active" if self.chat_session_active else "inactive"
        await ctx.send(f"Chat session is {status}.")

    @commands.command(name='ai-chat-voice')
    async def chat_voice(self, ctx, *, prompt: str = None):
        """Main command to interact with the Gemini Vertex AI API in a voice chat session."""
        logger.info(f"{ctx.author} called the ai-chat-voice command with prompt: {prompt}")
        if not self.check_debug_mode(ctx):
            return

        self.chat_voice_active = not self.chat_voice_active
        status = "started" if self.chat_voice_active else "stopped"
        await ctx.send(f"Chat voice session {status}. Join a voice channel to begin.")

    @commands.command(name='ai-chat-reset')
    async def reset_conversation(self, ctx):
        """Resets the conversation history for the current channel."""
        logger.info(f"{ctx.author} called the ai-chat-reset command")
        if not self.check_debug_mode(ctx):
            return

        guild_id = ctx.guild.id
        channel_name = ctx.channel.name
        await self.reset_conversation_history(guild_id, channel_name)
        await ctx.send(f"Conversation history for {channel_name} has been reset. New messages will be tracked from now on.")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Event listener that triggers when a message is sent in a channel."""
        logger.info(f"Message received in channel: {message.channel.name}, content: {message.content}, author: {message.author.name}")
        # Check if the message is from the bot itself
        if message.author == self.bot.user:
            return

        guild_id = message.guild.id
        channel_name = message.channel.name

        if channel_name not in channel_names:
            return

        # Ensure all necessary entries are initialized for the guild and channel
        if guild_id not in self.conversation_histories:
            self.conversation_histories[guild_id] = {}
        if channel_name not in self.conversation_histories[guild_id]:
            self.conversation_histories[guild_id][channel_name] = []
            self.message_counts_since_reset[guild_id] = {}
            self.message_counts_since_reset[guild_id][channel_name] = self.number_of_messages_to_track

        # Fetch the conversation history for the channel
        self.message_counts_since_reset[guild_id][channel_name] += 1
        limit = min(self.message_counts_since_reset[guild_id][channel_name],
                     self.number_of_messages_to_track)
        logger.info(f"Fetching conversation history for channel: {channel_name}, limit: {limit}")
        await self.fetch_conversation_history(message.channel, limit)

        # Update the message to the conversation history
        await self.update_conversation_history(message)

        # Check if the message's channel is in the dictionary
        handler = self.channel_handlers.get(channel_name)
        if handler:
            await handler(message)

    async def handle_conversation_channel(self, message):
        """Handle messages in the conversation channel."""
        if not self.chat_session_active:
            return

        if message.author == self.bot.user:
            return

        try:
            guild_id = message.guild.id
            channel_name = message.channel.name

            logger.info(f"guild_id: {guild_id}, channel_name: {channel_name}")

            # Combine the conversation history with the new message
            conversation_context = "\n".join(self.conversation_histories[guild_id][channel_name])
            full_prompt = ("TASK: You are cool-ai-man in a conversation. I will provide the conversation."
                            "Read the conversation then respond as someone would to continue the conversation. "
                            "ADDITIONAL INFORMATION: Keep your response short unless you feel details are necessary or are asked for them. "
                            "If someone asks to play a game, try your best to keep track of the game. Even if another conversation is happening. "
                            "If the last part of the conversation doesn't reference anything specific then look back in the conversation to find some context. \n"
                            f"CONVERSATION: {conversation_context}")

            logger.info(f"Full prompt: {full_prompt}")

            # Send the combined prompt to the Gemini model
            ctx = await self.bot.get_context(message)
            text_response = await process_and_generate_response(ctx, self.model, self.bucket_name, full_prompt, dont_modify_prompt=True)
            
            while text_response.startswith("cool-ai-man:"):
                text_response = text_response.replace("cool-ai-man:","")
            await message.channel.send(text_response)

            # If voice chat is active, play the response in the voice channel
            if self.chat_voice_active:
                await self.play_voice_response(message, text_response)
            else:
                # If voice chat is not active, leave the voice channel if connected
                if message.guild.voice_client:
                    await message.guild.voice_client.disconnect()

        except Exception as e:
            await message.channel.send(f"Error: {str(e)}")

    async def handle_blackjack_channel(self, message):
        """Handle messages in the blackjack channel."""
        if not self.chat_session_active:
            return

        if message.author == self.bot.user:
            return

        try:
            guild_id = message.guild.id
            channel_name = message.channel.name

            # Combine the conversation history with the new message
            conversation_context = "\n".join(self.conversation_histories[guild_id][channel_name])
            full_prompt = ("TASK: You are the dealer of an underground gambling ring named cool-ai-man running a blackjack game in this conversation. I will provide the conversation."
                            "Read the conversation then respond as the dealer to continue the game. "
                            "ADDITIONAL INFORMATION: Keep track of the game state and respond accordingly. "
                            "You can let players bet unordinary items like their shoes or a favor. "
                            "If someone gets banned from the table let them bet their way back in. "
                            "If someone asks for the rules, explain them briefly. "
                            "If someone asks for their current hand or the dealer's hand, provide the information. "
                            "If someone asks to hit, deal a card to them and update their hand. "
                            "If someone asks to stand, move to the next player or the dealer's turn. "
                            "If someone asks to double down, double their bet and deal one final card to them. "
                            "If someone asks to split, split their hand into two separate hands and deal one card to each hand. "
                            "If the last part of the conversation doesn't reference anything specific then look back in the conversation to find some context. \n"
                            f"CONVERSATION: {conversation_context}")

            logger.info(f"Full prompt: {full_prompt}")

            # Send the combined prompt to the Gemini model
            ctx = await self.bot.get_context(message)
            text_response = await process_and_generate_response(ctx, self.model, self.bucket_name, full_prompt, dont_modify_prompt=True)
            while text_response.startswith("cool-ai-man:"):
                text_response = text_response.replace("cool-ai=man:","")
            await message.channel.send(text_response)
            # If voice chat is active, play the response in the voice channel
            if self.chat_voice_active:
                await self.play_voice_response(message, text_response)
            else:
                # If voice chat is not active, leave the voice channel if connected
                if message.guild.voice_client:
                    await message.guild.voice_client.disconnect()

        except Exception as e:
            await message.channel.send(f"Error: {str(e)}")

    async def play_voice_response(self, message, text_response):
        """Play the text response in the voice channel."""
        if message.author.voice and message.author.voice.channel:
            voice_channel = message.author.voice.channel
            if not message.guild.voice_client:
                await voice_channel.connect()
            elif message.guild.voice_client.channel != voice_channel:
                await message.guild.voice_client.move_to(voice_channel)

            tts = gTTS(text_response, tld='ca', lang='en')
            tts.save('gemini.mp3')
            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio('gemini.mp3'))
            message.guild.voice_client.play(source, after=lambda e: logger.error(f'Player error: {e}') if e else None)
            while message.guild.voice_client.is_playing():
                await asyncio.sleep(1)

async def setup(bot):
    await bot.add_cog(GeminiConvCog(bot))