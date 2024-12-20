import discord
from discord.ext import commands
import os
from dotenv import load_dotenv


# 初始化bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='[', intents=intents)

# 改變bot狀態
@bot.event
async def on_ready():
    print(f'目前登入身份 >> {bot.user} <<')
    game = discord.Game('蕉綠')
    await bot.change_presence(status=discord.Status.idle, activity=game)
    
@bot.command()
async def load(ctx, extension):
    bot.load_extension(f"cogs.{extension}")
    await ctx.send(f"loaded {extension} done")

@bot.command()
async def unload(ctx, extension):
    bot.unload_extension(f"cogs.{extension}")
    await ctx.send(f"unloaded {extension} done")

@bot.command()
async def reload(ctx, extension):
    bot.reload_extension(f"cogs.{extension}")
    await ctx.send(f"reloaded {extension} done")


cogs_path = r"C:/Users/a5514/OneDrive/文件/VSCODE/專題題目：語音辨識機器人(語音逐字稿)/cogs"
for filename in os.listdir(cogs_path):
    if filename.endswith('.py'):
        bot.load_extension(f"cogs.{filename[:-3]}")

load_dotenv('C:/Users/a5514/OneDrive/文件/VSCODE/專題題目：語音辨識機器人(語音逐字稿)/key.env')

TOKEN = os.getenv('DISCORD_TOKEN')

if __name__ == "__main__":
    bot.run(TOKEN)
