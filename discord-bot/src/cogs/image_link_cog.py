import discord
from discord.ext import commands
import re

class ImageLinkCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='imagelink')
    async def imagelink(self, ctx):
        """Extracts image links from the message content or attachments"""
        
        
        if ctx.message is None:
            # Fetch the last message in the channel
            async for msg in ctx.channel.history(limit=2):
                if msg.id != ctx.message.id:
                    ctx.message = msg
                    break

        if ctx.message is None:
            await ctx.send("No message found to extract image links from.")
            return
        

        # Print out all attachment URLs for testing
        attachment_urls = [attachment.url for attachment in ctx.message.attachments]
        print("Attachment URLs:", attachment_urls)

        # Check for image attachments using MIME type
        image_links = [attachment.url for attachment in ctx.message.attachments if attachment.content_type and attachment.content_type.startswith('image/')]

        if image_links:
            await ctx.send(f"Image link found: {image_links[0]}")
        else:
            await ctx.send("No image links found in attachments.")

    @commands.command(name='videolink')
    async def videolink(self, ctx):
        """Extracts video links from the message content or attachments"""
        if ctx.message is None:
            # Fetch the last message in the channel
            async for msg in ctx.channel.history(limit=2):
                if msg.id != ctx.message.id:
                    ctx.message = msg
                    break

        if ctx.message is None:
            await ctx.send("No message found to extract video links from.")
            return

        # Print out all attachment URLs for testing
        attachment_urls = [attachment.url for attachment in ctx.message.attachments]
        print("Attachment URLs:", attachment_urls)

        # Check for video attachments using MIME type
        video_links = [attachment.url for attachment in ctx.message.attachments if attachment.content_type and attachment.content_type.startswith('video/')]

        if video_links:
            await ctx.send(f"Video link found: {video_links[0]}")
        else:
            await ctx.send("No video links found in attachments.")
    
async def setup(bot):
    await bot.add_cog(ImageLinkCog(bot))