import os
import asyncio
import telebot
from bs4 import BeautifulSoup
from pyrogram import Client, filters
from pyrogram.types import Message

# Get credentials from environment variables
API_ID = int(os.getenv("API_ID", ""))  # Ensuring it's an integer
API_HASH = os.getenv("API_HASH", "")
TOKEN = os.getenv("BOT_TOKEN", "")

# Initialize bots
bot = telebot.TeleBot(TOKEN)
pyro_bot = Client("html_to_txt_bot", api_id=API_ID, api_hash=API_HASH, bot_token=TOKEN)

# Function to extract text, URLs, and video links from an HTML file
def html_to_txt(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        soup = BeautifulSoup(file, "html.parser")
    
    text_content = []
    urls = []
    videos = []
    
    for tag in soup.find_all(['p', 'a', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']):
        text = tag.get_text(strip=True)
        if tag.name == "a" and tag.get("href"):
            url = tag['href']
            urls.append(url)
            text += f" (Link: {url})"
        text_content.append(text)
    
    # Extract video links from tables
    tables = soup.find_all('table')
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if len(cols) > 1:
                name = cols[0].get_text().strip()
                link = cols[1].find('a')['href'] if cols[1].find('a') else ''
                if link:
                    videos.append(f'{name}:{link}')
    
    return "\n".join(text_content), urls, videos

# ✅ Telebot Handler for Document Uploads
@bot.message_handler(content_types=['document'])
def handle_docs(message):
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    file_name = message.document.file_name

    if not file_name.endswith(".html"):
        bot.reply_to(message, "❌ Please upload an HTML file.")
        return

    os.makedirs("downloads", exist_ok=True)
    html_path = f"downloads/{file_name}"
    txt_path = html_path.replace(".html", ".txt")
    urls_path = html_path.replace(".html", "_urls.txt")
    videos_path = html_path.replace(".html", "_videos.txt")

    with open(html_path, "wb") as f:
        f.write(downloaded_file)
    
    extracted_text, urls, videos = html_to_txt(html_path)

    if not extracted_text.strip():
        bot.reply_to(message, "❌ The uploaded HTML file contains no valid text content.")
        os.remove(html_path)
        return
    
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(extracted_text)
    with open(urls_path, "w", encoding="utf-8") as f:
        f.write("\n".join(urls))
    with open(videos_path, "w", encoding="utf-8") as f:
        f.write("\n".join(videos))

    with open(txt_path, "rb") as f:
        bot.send_document(message.chat.id, f)
    with open(urls_path, "rb") as f:
        bot.send_document(message.chat.id, f)
    with open(videos_path, "rb") as f:
        bot.send_document(message.chat.id, f)

    os.remove(html_path)
    os.remove(txt_path)
    os.remove(urls_path)
    os.remove(videos_path)

# ✅ Pyrogram Handler for /h2t Command
@pyro_bot.on_message(filters.command("txt"))
async def ask_for_file(client: Client, message: Message):
    await message.reply_text("📂 **Send Your HTML file**")

@pyro_bot.on_message(filters.document)
async def handle_html_file(client: Client, message: Message):
    if not message.document.file_name.endswith(".html"):
        await message.reply_text("❌ Please upload a valid HTML file.")
        return

    html_file = await message.download()
    extracted_text, urls, videos = html_to_txt(html_file)

    if not extracted_text.strip():
        await message.reply_text("❌ The uploaded HTML file contains no valid text content.")
        os.remove(html_file)
        return

    txt_file = os.path.splitext(html_file)[0] + ".txt"
    urls_file = os.path.splitext(html_file)[0] + "_urls.txt"
    videos_file = os.path.splitext(html_file)[0] + "_videos.txt"

    with open(txt_file, "w", encoding="utf-8") as f:
        f.write(extracted_text)
    with open(urls_file, "w", encoding="utf-8") as f:
        f.write("\n".join(urls))
    with open(videos_file, "w", encoding="utf-8") as f:
        f.write("\n".join(videos))

    await message.reply_document(document=txt_file, caption="📜 Here is your extracted text file.")
    await message.reply_document(document=urls_file, caption="🔗 Here are the extracted URLs.")
    await message.reply_document(document=videos_file, caption="🎥 Here are the extracted video links.")

    os.remove(html_file)
    os.remove(txt_file)
    os.remove(urls_file)
    os.remove(videos_file)

# ✅ Start Command with Animated Progress
@pyro_bot.on_message(filters.command("start"))
async def start(client: Client, msg: Message):
    start_message = await client.send_message(msg.chat.id, "🌟 **Welcome!** 🌟\n")
    for progress, status in [(0, "Initializing bot..."), (25, "Loading features..."), (50, "Almost ready..."), (75, "Finalizing setup..."), (100, "✅ Bot is ready! Type /txt to start!")]:
        await asyncio.sleep(1)
        await start_message.edit_text(f"🌟 **Welcome!** 🌟\n\n{status}\n\nProgress: [{'🟩' * (progress // 10)}{'⬜' * (10 - (progress // 10))}] ")

# ✅ Run Both Bots
pyro_bot.run()
bot.polling()
