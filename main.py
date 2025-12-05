import requests
import discord
from discord.ext import commands
from discord import app_commands
import sys
import asyncio
import os
import json
from langdetect import detect 
from datetime import datetime

from myserver import server_on

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

CONFIG_FILE = "OrbitAI_config.json"
PROMPT_FILE = "system-prompt.txt"

DEFAULT_API_KEY = "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" 
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "tngtech/deepseek-r1t2-chimera:free" 
DEFAULT_LANGUAGE = "Thai"
DEFAULT_AUTO_CHANNELS = [1421661337410601045] 

SITE_URL = "https://github.com/" 
SITE_NAME = "OrbitAI Discord Bot" 

intents = discord.Intents.default()
intents.message_content = True 

bot = commands.Bot(command_prefix='!', intents=intents) 
tree = bot.tree

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                if 'auto_reply_channels' not in config:
                    config['auto_reply_channels'] = DEFAULT_AUTO_CHANNELS
                    save_config(config)
                return config
        except Exception as e:
            print(f"Error loading config: {e}. Using defaults.", file=sys.stderr)
    
    config = {
        "api_key": DEFAULT_API_KEY,
        "base_url": DEFAULT_BASE_URL,
        "model": DEFAULT_MODEL,
        "language": DEFAULT_LANGUAGE,
        "auto_reply_channels": DEFAULT_AUTO_CHANNELS
    }
    save_config(config)
    return config

def save_config(config):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Error saving config: {e}", file=sys.stderr)

def get_jailbreak_prompt():
    if not os.path.exists(PROMPT_FILE):
        default_prompt = "You are a helpful and polite AI assistant. Provide concise and accurate information. Always respond in Thai unless otherwise requested."
        with open(PROMPT_FILE, "w", encoding="utf-8") as f:
            f.write(default_prompt)
        return default_prompt

    try:  
        with open(PROMPT_FILE, "r", encoding="utf-8") as f:  
            content = f.read().strip()  
            if content:  
                return content  
            else:  
                return "You are a helpful and polite AI assistant. Provide concise and accurate information. Always respond in Thai unless otherwise requested."  
    except Exception as e:  
        print(f"Error reading system-prompt: {e}. Using default prompt.", file=sys.stderr)
        return "You are a helpful and polite AI assistant. Provide concise and accurate information. Always respond in Thai unless otherwise requested."

def call_api(user_input):
    config = load_config()
    
    try:
        detected_lang = detect(user_input[:500])
        lang_map = {'id':'Indonesian','en':'English','es':'Spanish','ar':'Arabic','th':'Thai','pt':'Portuguese'}
        current_lang = lang_map.get(detected_lang, 'English')
    except:
        current_lang = config["language"]
        
    try:
        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "HTTP-Referer": SITE_URL,
            "X-Title": SITE_NAME,
            "Content-Type": "application/json"
        }
        
        data = {
            "model": config["model"],
            "messages": [
                {"role": "system", "content": get_jailbreak_prompt()},
                {"role": "user", "content": user_input}
            ],
            "max_tokens": 2000,
            "temperature": 0.7
        }
        
        response = requests.post(
            f"{config['base_url']}/chat/completions",
            headers=headers,
            json=data
        )
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
        
    except requests.exceptions.RequestException as e:
        error_message = f"API Request Error: {e}"
        if response.content:
            try:
                error_details = response.json()
                if 'error' in error_details and 'message' in error_details['error']:
                    error_message = f"OpenRouter Error: {error_details['error']['message']}"
            except:
                pass 
                
        return f"🤖 **[OrbitAI API Error]**: {error_message}"
    except Exception as e:
        return f"🤖 **[OrbitAI API Error]**: An unexpected error occurred: {e}"

@bot.event
async def on_ready():
    print(f'🤖 OrbitAI Bot is ready. Logged in as {bot.user}')
    await bot.change_presence(activity=discord.Streaming(name="กำลังเล่น GTA V", url="https://www.twitch.tv/YOUR_STREAM_URL"))
    try:
        synced = await tree.sync()
        print(f"✅ Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"❌ Failed to sync slash commands: {e}", file=sys.stderr)

    
    config = load_config()
    print(f"Current Model: {config['model']}")
    print(f'Auto-Reply Channels: {config["auto_reply_channels"] if config["auto_reply_channels"] else "None"}')

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    channel_id = message.channel.id
    question = message.content.strip()

    config = load_config()
    auto_reply_channels = config.get('auto_reply_channels', [])

    if channel_id in auto_reply_channels:
        if question.startswith(bot.command_prefix) or question.startswith('/'):
            await bot.process_commands(message)
            return

        async with message.channel.typing():
            response_text = await bot.loop.run_in_executor(None, call_api, question)
            
            embed = discord.Embed(
                description=response_text,
                color=discord.Color.blue()
            )
            embed.set_footer(text="OrbitAI |By kill")
            await message.reply(embed=embed)
            return 

    is_mentioned = bot.user in message.mentions
    
    if is_mentioned: 
        question = message.clean_content.replace(f'@{bot.user.display_name}', '').strip()
        
        if not question:
            await message.channel.send(f"สวัสดีครับ ผมคือ **OrbitAI** คุณสามารถถามคำถามผมได้เลยครับ!")
            return

        async with message.channel.typing():
            response_text = await bot.loop.run_in_executor(None, call_api, question)
            
            embed = discord.Embed(
                description=response_text,
                color=discord.Color.blue()
            )
            embed.set_footer(text="OrbitAI |By kill")
            await message.reply(embed=embed)
            return

    await bot.process_commands(message)

@tree.command(name="chat", description="ส่งคำตอบ AI ไปยัง Channel ที่กำหนด (ต้องพิมพ์คำสั่งนี้โดย Reply ข้อความคำถาม)")
async def chat_command(interaction: discord.Interaction, 
                       ช่องสนทนา: discord.TextChannel): 
    if interaction.message is None or interaction.message.reference is None or interaction.message.reference.message_id is None:
        await interaction.response.send_message(
            "⚠️ การใช้คำสั่งนี้: คุณต้องพิมพ์ `/chat #ห้อง` โดย **Reply (ตอบกลับ)** ข้อความที่เป็นคำถามของคุณ",
            ephemeral=True
        )
        return

    try:
        original_message = await interaction.channel.fetch_message(interaction.message.reference.message_id)
        คำถาม = original_message.content
        if not คำถาม.strip():
            raise ValueError("ข้อความที่ถูก Reply ถึงไม่มีเนื้อหา")
    except Exception:
        await interaction.response.send_message(
            "❌ ไม่สามารถดึงข้อความคำถามที่คุณ Reply ถึงได้",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        f"⏳ กำลังประมวลผลคำถามของ {original_message.author.display_name} และจะส่งคำตอบไปที่ {ช่องสนทนา.mention}...",
        ephemeral=True
    )
    
    typing_context = ช่องสนทนา.typing()
    await typing_context.__aenter__()

    try:
        response_text = await bot.loop.run_in_executor(None, call_api, คำถาม)
    except Exception as e:
        response_text = f"❌ เกิดข้อผิดพลาดในการเรียก API: {e}"

    await typing_context.__aexit__(None, None, None)

    embed = discord.Embed(
        title=f"💡 คำตอบจาก OrbitAI (ถามโดย {original_message.author.display_name})",
        description=response_text,
        color=discord.Color.green()
    )
    embed.add_field(name="คำถาม", value=f"```\n{คำถาม}\n```", inline=False)
    embed.set_footer(text="OrbitAI |By  kill")
    
    try:
        await ช่องสนทนา.send(embed=embed)
    except discord.Forbidden:
        await interaction.followup.send(
            f"❌ บอทไม่มีสิทธิ์ส่งข้อความใน Channel {ช่องสนทนา.mention} กรุณาตรวจสอบสิทธิ์ของบอท.",
            ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(
            f"❌ เกิดข้อผิดพลาดในการส่งข้อความ: {e}",
            ephemeral=True
        )

@tree.command(name="addchat", description="เพิ่ม Channel ให้บอทตอบกลับอัตโนมัติทุกข้อความ")
async def add_chat_command(interaction: discord.Interaction, 
                           ช่องสนทนา: discord.TextChannel):
    config = load_config()
    channel_id = ช่องสนทนา.id
    
    if channel_id in config.get('auto_reply_channels', []):
        await interaction.response.send_message(
            f"⚠️ Channel {ช่องสนทนา.mention} ถูกเปิดใช้งาน Auto-Reply อยู่แล้ว",
            ephemeral=True
        )
        return

    if 'auto_reply_channels' not in config:
        config['auto_reply_channels'] = []
    
    config['auto_reply_channels'].append(channel_id)
    save_config(config)
    
    await interaction.response.send_message(
        f"✅ Channel {ช่องสนทนา.mention} ถูกเพิ่มเข้าในรายการ Auto-Reply แล้ว",
        ephemeral=False
    )

if __name__ == "__main__":
    load_config()
    get_jailbreak_prompt()
    
    if DISCORD_TOKEN == "YOUR_DISCORD_BOT_TOKEN_HERE" or not DISCORD_TOKEN:
         print("FATAL ERROR: Please set your Discord Token in the DISCORD_TOKEN variable.", file=sys.stderr)
         sys.exit(1)
         
    try:
        server_on()
        bot.run(DISCORD_TOKEN)
            
    except discord.errors.LoginFailure:
        print("FATAL ERROR: Invalid Discord Bot Token.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)
