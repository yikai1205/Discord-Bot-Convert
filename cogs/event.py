import discord
from discord.ext import commands
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv('C:/Users/a5514/OneDrive/文件/VSCODE/專題題目：語音辨識機器人(語音逐字稿)/key.env')

genai.configure(api_key=os.getenv('GoogleaiKey'))
model = genai.GenerativeModel('gemini-pro')

class Event(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()  # 使用 commands.command 裝飾器
    async def ping(self, ctx):
        await ctx.send("Pong!")

    @commands.command()
    async def clean(self, ctx, num: int):
        await ctx.channel.purge(limit=num+1)
        await ctx.send(f'清除 {num} 條消息 15秒後此則消息自動刪除 ', delete_after=15)
    
    @commands.command()
    async def says(self ,ctx , *, msg):
        await ctx.message.delete()
        await ctx.send(msg)

    @commands.Cog.listener()
    async def on_application_command_error(self, ctx:discord.ApplicationContext, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.followup.send(content='Command on cooldown... please wait', ephemeral=True)
        elif isinstance(error, commands.MissingPermissions):
            await ctx.followup.send(content="You don't have required permission to ude the command.", ephemeral=True)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.followup.send(content="There are some arguments missing to use the command.", ephemeral=True)
        else:
            await ctx.followup.send(error, ephemeral=True)
    
    @commands.Cog.listener()
    async def on_message(self, msg:discord.Message):
        if msg.content.startswith(self.bot.user.mention):
            div = msg.content.split()
            for i in range(len(div)):
                if div[i].startswith('<@'):
                    user:discord.User = await self.bot.fetch_user(div[i][2:-1])
                    div[i] = user.name
            prompt = ' '.join(div)
            response = model.generate_content(prompt)
            await msg.channel.send(response.text)
    
def setup(bot):
    bot.add_cog(Event(bot))