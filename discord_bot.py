import discord
import requests
import os
import json
from bs4 import BeautifulSoup

api_key = os.environ.get("GEMINI_API_KEY")
discord_token = os.environ.get("DISCORD_TOKEN")
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={api_key}"

def web_search(query):
    search_url = f"https://html.duckduckgo.com/html/?q={query}"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(search_url, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")
    results = []
    for link in soup.find_all("a", class_="result__a", limit=3):
        results.append(f"{link.text} - {link['href']}")
    return "\n".join(results) if results else "कोई नतीजा नहीं मिला।"

def save_file(filename, content):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    return f"फाइल '{filename}' सेव हो गई।"

def ask_gemini(messages):
    payload = {"contents": messages}
    response = requests.post(url, json=payload)
    data = response.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        return json.dumps({"action": "answer", "message": f"[Error] {data}"})

SYSTEM_INSTRUCTION = """
तुम Hermes नाम के एक autonomous AI एजेंट हो। हर बार तुम्हें सिर्फ नीचे दिए गए JSON फॉर्मेट में जवाब देना है, कुछ और नहीं:

{"action": "search", "query": "जो खोजना है"}
या
{"action": "save", "filename": "नाम.txt", "content": "जो कंटेंट सेव करना है"}
या
{"action": "answer", "message": "यूज़र को अंतिम जवाब"}

नियम:
- अगर काम पूरा करने के लिए इंटरनेट जानकारी चाहिए, तो "search" इस्तेमाल करो।
- अगर कुछ फाइल में सेव करना है, तो "save" इस्तेमाल करो।
- जब पूरा काम हो जाए, तो "answer" से अंतिम जवाब दो।
- सिर्फ JSON दो, कोई और टेक्स्ट नहीं, कोई मार्कडाउन बैकटिक नहीं।
"""

def run_agent(goal):
    messages = [
        {"role": "user", "parts": [{"text": SYSTEM_INSTRUCTION + "\n\nयूज़र का लक्ष्य: " + goal}]}
    ]
    max_steps = 6
    for step in range(max_steps):
        reply_text = ask_gemini(messages)
        clean = reply_text.strip().strip("`").replace("json", "", 1).strip()
        try:
            action_data = json.loads(clean)
        except json.JSONDecodeError:
            return reply_text

        action = action_data.get("action")

        if action == "search":
            query = action_data.get("query", "")
            result = web_search(query)
            messages.append({"role": "model", "parts": [{"text": reply_text}]})
            messages.append({"role": "user", "parts": [{"text": f"सर्च नतीजे:\n{result}"}]})

        elif action == "save":
            filename = action_data.get("filename", "output.txt")
            content = action_data.get("content", "")
            result = save_file(filename, content)
            messages.append({"role": "model", "parts": [{"text": reply_text}]})
            messages.append({"role": "user", "parts": [{"text": result}]})

        elif action == "answer":
            return action_data.get("message", "")

        else:
            return reply_text

    return "[Hermes ने max steps पूरे कर लिए।]"

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"{client.user} Discord पर लॉगिन हो गया!")

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    async with message.channel.typing():
        reply = run_agent(message.content)
        await message.channel.send(reply)

client.run(discord_token)
