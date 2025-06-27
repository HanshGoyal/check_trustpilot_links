import os
import csv
import asyncio
from dotenv import load_dotenv

import discord
from discord.ext import commands
from discord import File

from app import process_link  # Your existing scraping logic

# Load bot token
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN missing in .env")

# Set up intents (ensure message content intent is enabled in Developer Portal)
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Helper: count live/deleted
def count_live_deleted(path: str):
    live = deleted = 0
    if not os.path.exists(path):
        print(f"[count_live_deleted] File not found: {path}")
        return live, deleted
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if len(row) > 1 and row[1].strip() == "Live":
                live += 1
            elif len(row) > 1 and row[1].strip() == "Deleted":
                deleted += 1
    print(f"[count_live_deleted] Live: {live}, Deleted: {deleted}")
    return live, deleted

# Shared processing logic
async def process_links_and_respond(ctx, urls):
    print(f"[process_links_and_respond] Processing {len(urls)} links")

    with open("result.csv", "w", newline="", encoding="utf-8") as cf:
        writer = csv.writer(cf)
        writer.writerow(["Link", "Status", "Comment"])
        for url in urls:
            print(f"[processing] {url}")
            link, status, comment = process_link(url)
            writer.writerow([link, status, comment])
            print(f"[processed] {link}: {status} — {comment}")

    live, deleted = count_live_deleted("result.csv")
    await ctx.send(f"✅ Live: {live}   🗑️ Deleted: {deleted}")
    await ctx.send(file=File("result.csv"))

# /start command
@bot.command()
async def start(ctx):
    print(f"[start] User: {ctx.author.id}, Channel: {ctx.channel}")
    await ctx.send("👋 I’m online! Use `/process <link1> [link2]…` or upload a `.txt` file with `/input`.")

# /process command
@bot.command()
async def process(ctx, *args):
    if not args:
        return await ctx.send("❌ Usage: `/process https://… [https://…]…`")

    urls = [u.strip() for u in args if u.strip()]
    if not urls:
        return await ctx.send("❌ No valid links found.")

    with open("links.txt", "w", encoding="utf-8") as lf:
        for url in urls:
            lf.write(url + "\n")
    print("[process] URLs saved to links.txt")

    # Kickoff message
    await ctx.send("🔄 Starting to process your links…")

    await process_links_and_respond(ctx, urls)

# /input command
@bot.command()
async def input(ctx):
    if not ctx.message.attachments:
        return await ctx.send("❌ Please upload a `.txt` file with the `/input` command.")

    attachment = ctx.message.attachments[0]
    if not attachment.filename.endswith(".txt"):
        return await ctx.send("❌ Only `.txt` files are allowed.")

    file_path = f"temp_{attachment.filename}"
    await attachment.save(file_path)
    print(f"[input] File saved: {file_path}")

    with open(file_path, "r", encoding="utf-8") as rf:
        urls = [line.strip() for line in rf if line.strip()]
    if not urls:
        return await ctx.send("❌ File is empty or has no valid links.")

    with open("links.txt", "w", encoding="utf-8") as wf:
        for url in urls:
            wf.write(url + "\n")
    print(f"[input] Saved {len(urls)} URLs to links.txt")
    
    # Kickoff message
    await ctx.send("🔄 Starting to process your links…")

    await process_links_and_respond(ctx, urls)

# Start the bot
if __name__ == "__main__":
    print("[main] Discord bot starting...")
    bot.run(DISCORD_TOKEN)
