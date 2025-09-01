import discord
from discord.ext import commands

class Greetings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @commands.command(name='hello')
    async def hello(self, ctx, *, member: discord.Member):
        """Responds with a greeting"""
        print(f'ctx.author: {ctx.author}, command is: {ctx.command}')
        member = member or ctx.author
        if self._last_member is None or self._last_member.id != member.id:
            await ctx.send(f'Hello {member.name}~')
        else:
            await ctx.send(f'Hello {member.name}... This feels familiar.')
        self._last_member = member

async def setup(bot):
    await bot.add_cog(Greetings(bot))