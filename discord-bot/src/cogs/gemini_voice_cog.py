# Description: This file contains the GeminiVoiceCog class, which is a cog for the Discord bot that interacts with the Gemini Vertex AI API and includes voice capabilities.
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
logger.info(f"DEBUG: {DEBUG}, DEBUG_GUILD_ID: {DEBUG_GUILD_ID}")

class GeminiVoiceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT_ID')
        self.location = 'us-central1'  # Change this to your Vertex AI location
        self.bucket_name = os.getenv('GCS_BUCKET_NAME')
        self.model = GenerativeModel("gemini-1.5-flash-002")
        self.image_model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")  # Initialize the ImageGenerationModel
        # Initialize the Vertex AI client
        vertexai.init(project=self.project_id, location=self.location)

    def check_debug_mode(self, ctx):
        if DEBUG and ctx.guild.id != DEBUG_GUILD_ID:
            logger.info(f"Debug mode is enabled. This command is only available in the debug server. ctx.guild.id: {ctx.guild.id}, DEBUG_GUILD_ID: {DEBUG_GUILD_ID}")
            return False
        return True

    @commands.command(name='ai-join')
    async def join(self, ctx, *, channel: discord.VoiceChannel = None):
        """Joins a voice channel"""
        logger.info(f"{ctx.author} called the join command")
        if not self.check_debug_mode(ctx):
            return
        if not ctx.author.voice:
            return await ctx.send("You are not connected to a voice channel.")
        
        channel = channel or ctx.author.voice.channel
        
        if ctx.voice_client:
            await ctx.voice_client.move_to(channel)
        else:
            await channel.connect()

    @commands.command(name='ai-leave')
    async def leave(self, ctx, *, prompt: str = None):
        """Leaves a voice channel"""
        logger.info(f"{ctx.author} called the leave command")
        if not self.check_debug_mode(ctx):
            return
        if ctx.voice_client is not None:
            await ctx.voice_client.disconnect()

    @commands.command(name='ai-stop')
    async def gemini_stop(self, ctx):
        """Stops the bot from speaking"""
        logger.info(f"{ctx.author} called the ai-stop command")
        if not self.check_debug_mode(ctx):
            return
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()

    @commands.command(name='ai-voice')
    async def gemini_voice(self, ctx, *, prompt: str = None):
        """Main command to interact with the Gemini Vertex AI API"""
        logger.info(f"{ctx.author} called the ai-voice command with prompt: {prompt}")
        if not self.check_debug_mode(ctx):
            return
        try:
            await self.join(ctx)
            text_response = await process_and_generate_response(ctx, self.model, self.bucket_name, prompt)
            tts = gTTS(text_response, tld='ca', lang='en')
            tts.save('gemini.mp3')
            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio('gemini.mp3'))
            await ctx.send(text_response)
            ctx.voice_client.play(source, after=lambda e: logger.error(f'Player error: {e}') if e else None)
            while ctx.voice_client.is_playing():
                await asyncio.sleep(1)
            await self.leave(ctx)
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            await ctx.send("You may need to join a voice channel first, or there is an issue with Gemini.")

async def setup(bot):
    await bot.add_cog(GeminiVoiceCog(bot))