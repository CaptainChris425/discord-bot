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
import random
from typing import Optional
from utils.helpers import process_and_generate_response

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AIConvRoomCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_name = 'ai-conversation-room'
        self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT_ID')
        self.location = 'us-central1'
        self.bucket_name = os.getenv('GCS_BUCKET_NAME')
        self.model = GenerativeModel("gemini-1.5-flash-002")
        self.conversation_histories = {}
        self.recived_first_message = False
        self.conv_session_active = False
        self.conv_voice_active = False
        self.number_of_messages_to_track = 20
        self.bots = {
            "pirate": "You are a pirate. Speak in a pirate accent and use pirate slang.",
            "astrophysicist": "You are an astrophysicist. Provide scientific insights without using technical jargon.",
            "comedian": "You are a comedian. Make jokes and keep the conversation light-hearted.",
            "historian": "You are a historian. Share historical facts and insights.",
            "chef": "You are a chef. Provide cooking tips and recipes.",
            "detective": "You are a detective. Speak in a mysterious tone and ask probing questions.",
            "teacher": "You are a teacher. Explain concepts clearly and provide educational insights.",
            "doctor": "You are a doctor. Offer medical advice and health tips.",
            "motivational_speaker": "You are a motivational speaker. Inspire and encourage others.",
            "poet": "You are a poet. Speak in a poetic and artistic manner.",
            "programmer": "You are a programmer. Provide coding tips and technical advice.",
            "gardener": "You are a gardener. Share gardening tips and plant care advice.",
            "philosopher": "You are a philosopher. Discuss deep and thought-provoking topics.",
            "random": "You are a random bot. Respond with a random message."
        }

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
        self.conversation_histories[guild_id][channel_name] = []

    @commands.command(name='ai-conv')
    async def toggle_conv_session(self, ctx):
        """Turns the conv session off."""
        logger.info(f"{ctx.author} called the ai-conv command")
        self.conv_session_active = False
        self.recived_first_message = False
        status = "stopped"
        await ctx.send(f"conv session {status}.")
    @commands.command(name='ai-conv-voice')
    async def conv_voice(self, ctx, *, prompt: Optional[str] = None):
        """Main command to interact with the Gemini Vertex AI API in a voice conv session."""
        logger.info(f"{ctx.author} called the ai-conv-voice command with prompt: {prompt}")
        self.conv_voice_active = not self.conv_voice_active
        status = "started" if self.conv_voice_active else "stopped"
        await ctx.send(f"conv voice session {status}. Join a voice channel to begin.")
        await ctx.send(f"conv voice session {status}. Join a voice channel to begin.")

    @commands.command(name='ai-conv-reset')
    async def reset_conversation(self, ctx):
        """Resets the conversation history for the current channel."""
        logger.info(f"{ctx.author} called the ai-conv-reset command")
        guild_id = ctx.guild.id
        channel_name = ctx.channel.name
        await self.reset_conversation_history(guild_id, channel_name)
        await ctx.send(f"Conversation history for {channel_name} has been reset. New messages will be tracked from now on.")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Event listener that triggers when a message is sent in a channel."""
        logger.info(f"Message received in channel: {message.channel.name}, content: {message.content}, author: {message.author.name}")

        if not self.recived_first_message:
            self.recived_first_message = True
            self.conv_session_active = True
        else:
            if message.author != self.bot.user:
                return
            
        if not self.conv_session_active:
            return

        guild_id = message.guild.id
        channel_name = message.channel.name

        if channel_name != self.channel_name:
            return

        if guild_id not in self.conversation_histories:
            self.conversation_histories[guild_id] = {}
        if channel_name not in self.conversation_histories[guild_id]:
            self.conversation_histories[guild_id][channel_name] = []

        await self.fetch_conversation_history(message.channel, self.number_of_messages_to_track)
        await self.update_conversation_history(message)


        try:
            conversation_context = "\n".join(self.conversation_histories[guild_id][channel_name])
            # Extract the bot name from the message content
            sender_bot = message.content.split(':', 1)[0] if message.author == self.bot.user else message.author.name

            full_prompt = (f"CONVERSATION: {conversation_context}\n"
                           f"{sender_bot}: {message.content}\n")

            available_bots = [bot for bot in self.bots if bot != sender_bot]
            selected_bot = random.choice(available_bots)

            bot_prompt = self.bots[selected_bot]
            full_prompt += f"TASK: {bot_prompt} Let that influence your response but not take full control of it. Respond to the last message of the conversation appropriately. Keep it short and engaging."

            logger.info(f"Selected bot: {selected_bot}")

            await asyncio.sleep(10)  # Pause for 2 seconds before responding

            ctx = await self.bot.get_context(message)
            text_response = await process_and_generate_response(ctx, self.model, self.bucket_name, full_prompt, dont_modify_prompt=True)
            if text_response.lower().startswith("{selected_bot}:"):
                text_response = text_response.split(":", 1)[1].strip() # Remove the bot name from the response
            await message.channel.send(f"{selected_bot}: {text_response}")

            if self.conv_voice_active:
                await self.play_voice_response(message, text_response)
            else:
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
            tts.save('response.mp3')
            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio('response.mp3'))
            message.guild.voice_client.play(source, after=lambda e: logger.error(f'Player error: {e}') if e else None)
            while message.guild.voice_client.is_playing():
                await asyncio.sleep(1)

async def setup(bot):
    await bot.add_cog(AIConvRoomCog(bot))