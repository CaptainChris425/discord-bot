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
logger.info(f"DEBUG: {DEBUG}, DEBUG_GUILD_ID: {DEBUG_GUILD_ID}, CONVERSATION_CHANNEL_NAME: {CONVERSATION_CHANNEL_NAME}")

class GeminiConvCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT_ID')
        self.location = 'us-central1'  # Change this to your Vertex AI location
        self.bucket_name = os.getenv('GCS_BUCKET_NAME')
        self.model = GenerativeModel("gemini-1.5-flash-002")
        # Initialize the Vertex AI client
        vertexai.init(project=self.project_id, location=self.location)
        self.conversation_history = []
        self.chat_session_active = False
        self.chat_voice_active = False
        self.reset_flag = False

    def check_debug_mode(self, ctx):
        if DEBUG and ctx.guild.id != DEBUG_GUILD_ID:
            logger.info(f"Debug mode is enabled. This command is only available in the debug server. ctx.guild.id: {ctx.guild.id}, DEBUG_GUILD_ID: {DEBUG_GUILD_ID}")
            return False
        return True

    async def fetch_conversation_history(self, channel):
        """Fetch the last 10 messages from the specified channel."""
        self.conversation_history = []
        async for message in channel.history(limit=10, oldest_first=False):
            self.conversation_history.append(f"{message.author.name}: {message.content}")
        self.conversation_history.reverse()  # Ensure the messages are in chronological order

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
        """Resets the conversation history."""
        logger.info(f"{ctx.author} called the ai-chat-reset command")
        if not self.check_debug_mode(ctx):
            return

        self.conversation_history = []
        self.reset_flag = True
        await ctx.send("Conversation history has been reset. New messages will be tracked from now on.")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Responds to messages in the chatroom when the chat session is active."""
        ctx = await self.bot.get_context(message)
        if not self.chat_session_active:
            return

        if message.author == self.bot.user:
            return

        if message.channel.name != CONVERSATION_CHANNEL_NAME:
            return

        try:
            # If reset flag is set, clear the conversation history and reset the flag
            if self.reset_flag:
                self.conversation_history = []
                self.reset_flag = False

            # Fetch the specified channel
            channel = discord.utils.get(message.guild.channels, name=CONVERSATION_CHANNEL_NAME)
            if not channel:
                await message.channel.send(f"Channel '{CONVERSATION_CHANNEL_NAME}' not found.")
                return

            # Fetch the last 10 messages from the channel
            await self.fetch_conversation_history(channel)

            # Combine the conversation history with the new message
            conversation_context = "\n".join(self.conversation_history)
            full_prompt = f"TASK: You are cool-ai man in a conversation. I will provide the conversation. Read the conversation then respond as someone would to continue the conversation. \
                If the last part of the conversation doesnt reference anything specific then look back in the conversation to find some context.\n\
                CONVERSATION: {conversation_context}\n{message.author.name}: {message.content}"

            logger.info(f"Full prompt: {full_prompt}")

            # Send the combined prompt to the Gemini model
            text_response = await process_and_generate_response(ctx, self.model, self.bucket_name, full_prompt)
            await message.channel.send(text_response)

            # Update the conversation history with the new message
            self.conversation_history.append(f"{message.author.name}: {message.content}")
            if len(self.conversation_history) > 20:
                self.conversation_history.pop(0)

            # If voice chat is active, play the response in the voice channel
            if self.chat_voice_active:
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
            else:
                # If voice chat is not active, leave the voice channel if connected
                if message.guild.voice_client:
                    await message.guild.voice_client.disconnect()

        except Exception as e:
            await message.channel.send(f"Error: {str(e)}")

async def setup(bot):
    await bot.add_cog(GeminiConvCog(bot))