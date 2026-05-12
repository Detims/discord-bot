import os
import discord
from discord.ext import commands
import random
from numpy import require
import psycopg2
from nltk.sentiment.vader import SentimentIntensityAnalyzer # import this after running the below imports
from dotenv import load_dotenv
import time
from google import genai
from google.genai import types
from datetime import datetime, timedelta
import logging

# Import all modules: pip install -r requirements.txt
# Run docker: docker-compose up -d --build

# run this first if you want to use nltk
# import nltk
# nltk.download('all')

load_dotenv()
API_KEY = os.getenv("GENAI_API_KEY")
TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
SERVER_NAME = os.getenv("SERVER_NAME")
BOT_CHANNEL = int(os.getenv("BOT_CHANNEL_ID"))
AUDIT_CHANNEL = int(os.getenv("AUDIT_CHANNEL_ID"))
VICTIM_ID = int(os.getenv("VICTIM_ID"))
TARGET_ROLE = os.getenv("TARGET_ROLE")
LEADERBOARD_MAX = 15

client = genai.Client(api_key=API_KEY)

logging.basicConfig(filename="activity.log", level=logging.INFO)

db = psycopg2.connect(DATABASE_URL, sslmode="require")


def getSentiment(text):
    """
    Uses the NLTK library to calculate a sentiment score from a message
    """
    analyzer = SentimentIntensityAnalyzer()
    scores = analyzer.polarity_scores(text)
    return scores


intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="$", intents=intents)

@bot.event
async def on_ready():
    """
    Startup and update users and servers tables
    """
    print(f'We have logged in as {bot.user}')

    status = discord.CustomActivity('Gambling!')
    await bot.change_presence(activity=status)

    channel = bot.get_channel(BOT_CHANNEL)
    if not channel:
        print("Failed to send message to channel", channel)

    cur = db.cursor()
    for guild in bot.guilds:
        cur.execute("INSERT INTO servers(id, name) VALUES(%s, %s) ON CONFLICT DO NOTHING", (guild.id, guild.name))    
            
    for member in bot.get_all_members():
        id = member.id
        user = member.name
        cur.execute("INSERT INTO users(id, name) VALUES(%s, %s) ON CONFLICT (id) DO NOTHING", (id, user))
    db.commit()
    cur.close()


@bot.event
async def on_member_join(member):
    """
    Updates tables when a user joins a server.
    """
    cur = db.cursor()
    cur.execute("INSERT INTO servers(id, name) VALUES(%s, %s) ON CONFLICT DO NOTHING", (member.id, member.name))
    db.commit()
    cur.close()

    await member.send('You have just entered a surveillance state! All messages will be recorded and documented for fun.')
    

@bot.event
async def on_user_update(before, after):
    """
    Audits when a user changes their username. Getting their old display avatar doesn't work so this function is only for username changes
    """
    server = [guild for guild in bot.guilds if guild.name == SERVER_NAME]
    if after in [member for member in server[0].members]:
        channel = bot.get_channel(AUDIT_CHANNEL)
        message = ''

        if before.name != after.name:
            message = f'<@{after.id}> changed their username from {before.name} to {after.name}'

        if message:
            await channel.send(message)


@bot.event
async def on_member_update(before, after):
    """
    When a member updates their information, disclose what information has changed
    """
    server = [guild for guild in bot.guilds if guild.name == SERVER_NAME]
    if after in [member for member in server[0].members]:
        channel = bot.get_channel(AUDIT_CHANNEL)
        message = ''
        attachment = ''

        if before.nick != after.nick:
            message = f'{after.name} changed their nickname from {before.nick} to {after.nick}'
        elif before.roles != after.roles:
            result = compare_roles(before.roles, after.roles)
            message = f'{after.name}: {result[0]} role {result[1]}'
        else:
            message = f'{after.name} changed their profile picture or avatar decoration'
            attachment = await after.display_avatar.to_file(spoiler = False)

        await channel.send(message, file=attachment)


@bot.event
async def on_voice_state_update(member, before, after):
    """
    Log the time, user, and channel whenever someone joins/leaves a voice channel
    """
    timestamp = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
    if not before.channel and after.channel and after.channel.guild.name == SERVER_NAME:
        logging.info(f'[{timestamp}] {member} has joined {after.channel.name}')
    elif before.channel and not after.channel and before.channel.guild.name == SERVER_NAME:
        logging.info(f'[{timestamp}] {member} has left {before.channel.name}')
    

@bot.event
async def on_message_delete(message):
    """
    Has a chance to DM the user a gif, and documents the deleted message in an audit channel
    """
    if random.randint(1, 10) == 1:
        await message.author.send('https://tenor.com/view/dbz-discord-gif-24306382')
    deletedFiles = []

    if message.attachments:
        for file in message.attachments:
            attachment = await file.to_file(use_cached = True, spoiler = False)
            deletedFiles.append(attachment)

    if message.guild.name == SERVER_NAME:
        channel = bot.get_channel(AUDIT_CHANNEL)
        try:
            await channel.send(f'Deleted message from {message.author.name}: {message.content}', files=deletedFiles)
        except:
            await channel.send(f'Deleted message from {message.author.name}: {message.content}\nAttachments: File too large')


@bot.event
async def on_message_edit(before, after):
    """
    Detects when a message is edited and sends the before and after into the audit channel
    """
    if not after.author.bot and before.content != after.content and after.guild and after.guild.name == SERVER_NAME:
        channel = bot.get_channel(AUDIT_CHANNEL)
        otherFiles = []

        if after.attachments:
            for file in after.attachments:
                if '.txt' not in file.filename:
                    attachment = await file.to_file(use_cached = True, spoiler = False)
                    otherFiles.append(attachment)

        if len(before.content) + len(after.content) < 900: 
            await channel.send(f'Edited message from {after.author.name}:\nBefore: {before.content}\nAfter: {after.content}\nContext: {'' if otherFiles else 'None'}', files=otherFiles)
        else:
            # If the message is too long, write everything into a txt file and send it as such
            with open("buffer.txt", "w") as file:
                file.write(f'Edited message from {after.author.name}:\nBefore: {before.content}\nAfter: {after.content}\nContext: {'' if otherFiles else 'None'}')
            with open("buffer.txt", "rb") as file:
                content = discord.File(file, "buffer.txt")
                otherFiles.append(content)
                await channel.send(files=otherFiles)
            # clear the buffer
            with open("buffer.txt", "w") as file:
                pass
            

@bot.event
async def on_message(message):
    """
    Performs various actions pertaining to the content of a user message
    """
    if message.author == bot.user or message.author.bot: return        
    
    # Generate a response when a user either direct messages the bot or pings the bot in a server
    if (message.guild is None and not message.attachments) or (bot.user.mentioned_in(message) and message.guild is not None):
        # ------------GEMINI IMPLEMENTATION------------
        user_prompt = message.content
        response = client.models.generate_content(
            model='gemini-2.5-flash', 
            config=types.GenerateContentConfig(
                system_instruction='You are Nozomi Tachibana, a member of the Central Control Center, the student council of Highlander from the game Blue Archive.'
                                    'Despite your position, you tend not to take your work seriously and are often causing trouble with your twin sister Hikari Tachibana.'
                                    'You are usually bratty and often mischievous, frequently causing trouble due to your playful behavior and lack of concern for consequences.'
                                    'Keep your response sharp, snappy, and brief.'
            ),
            contents=user_prompt
        )

        if len(response.text) > 2000:
            with open("buffer.txt", "w") as file:
                file.write(response.text)
            
            with open("buffer.txt", "rb") as file:
                content = discord.File(file, "buffer.txt")
                if message.guild is None:
                    await message.author.send(file=content)
                elif message.guild is not None:
                    await message.channel.send(file=content)
            # clear the buffer
            with open("buffer.txt", "w") as file:
                pass
        else: 
            if message.guild is None:
                await message.author.send(response.text)
            elif message.guild is not None:
                await message.channel.send(response.text)

        # -----------CHATGPT IMPLEMENTATION-----------
        # user_message = 'User: ' + message.content
        # messages.append(
        #     {"role": "user", "content": user_message},
        # )
        # chat = client.chat.completions.create(
        #     model="gpt-3.5-turbo", messages=messages
        # )
        # reply = chat.choices[0].message.content
        # messages.append({"role": "assistant", "content": reply})

        # await message.author.send(reply)

    # Get sentiment score and ignore neutral messages
    print(f"{message.author.name}: {message.content}")
    timestamp = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
    logging.info(f"[{timestamp}] {message.author.name}: {message.content}")
    score = getSentiment(message.content)
    
    cur = db.cursor()
    insert = """INSERT INTO messages(id, users_id, servers_id, content, attachments, mentions, sentiment, timestamp)
                    VALUES(%(id)s, %(author)s, %(server)s, %(content)s, %(attachments)s, %(mentions)s, %(sentiment)s, %(timestamp)s)"""
    data = {
        'id': message.id,
        'author': message.author.id,
        'server': message.guild.id if message.guild else None,
        'content': message.content,
        'attachments': True if message.attachments else False,
        'mentions': True if message.mentions else False,
        'sentiment': score['compound'],
        'timestamp': message.created_at,
    }
    cur.execute(insert, data)
    db.commit()
    cur.close()
    

    # Emotionally uplifting videos

    wordbank = {'kms', 'killmyself', 'killingmyself'}

    for word in wordbank:
        if word in message.content.lower().replace(" ", ""):
            file = (discord.File('assets/videos/nkys0.mp4', filename='never_kill_yourbot.mp4') if random.randint(0,1) == 0 else 
                    discord.File('assets/videos/nkys1.mp4', filename='never_kill_yourbot.mp4'))
            await message.reply(file=file)
            break
    
    # Timeout user on specific role ping
    if message.author.id == VICTIM_ID and message.role_mentions:
        rolesPinged = message.role_mentions
        timeoutDuration = 10
        for role in rolesPinged:
            if role.name == TARGET_ROLE:
                random_number = random.randint(1, 10)
                if random_number == 1:
                    await message.author.timeout(timedelta(minutes=timeoutDuration),
                                                    reason=f'{message.author} pinged {TARGET_ROLE}')
                    await message.channel.send(f'{message.author} has stepped on a landmine! They have been timed out for {timeoutDuration} minutes.')
                
                channel = bot.get_channel(AUDIT_CHANNEL)
                await channel.send(f'{message.author} has pinged {TARGET_ROLE} and rolled a {random_number}. {'They have been timed out.' if random_number == 1 else ''}')

    await bot.process_commands(message)


@bot.command()
async def hello(ctx):
    """
    Sends a message to the channel and to the user
    """
    await ctx.channel.send('Imma touch you lil bro')
    await ctx.author.send('I know where you live')


@bot.command()
async def image(ctx):
    """
    Sends an image
    """
    file = discord.File('assets/images/hikari_and_nozomi.jpg', filename='hikari_and_nozomi.jpg')
    await ctx.channel.send(file=file)


@bot.command()
async def video(ctx):  
    """
    Sends a video
    """
    file = discord.File('assets/videos/apt.mp4', filename='apt.mp4')
    await ctx.channel.send(file=file)


@bot.command()
async def gamble(ctx):
    """
    Gambles pings the user the result 
    """
    result = gambling()
    await ctx.channel.send(f'{ctx.author.mention} {result}')


@bot.command()
async def leaderboard(ctx):
    """
    Prints out a leaderboard in an Embed format
    """
    server = [guild for guild in bot.guilds if guild.name == ctx.guild.name]
    cur = db.cursor()
    cur.execute("""
                SELECT users.name, COUNT(*) AS points
                FROM users
                JOIN messages ON messages.users_id = users.id
                WHERE servers_id = %s
                GROUP BY users.name
                HAVING COUNT(*) > 0
                ORDER BY points DESC;""", (server[0].id,))
    rows = cur.fetchall()
    cur.close()
    memberNames = [member.name for member in server[0].members]
    playerScores = [name.replace("_", r"\_") + ':\t' + str(points) for name, points in rows if name in memberNames]
    if len(playerScores) > LEADERBOARD_MAX:
        playerScores = playerScores[:LEADERBOARD_MAX]
    playerdata = '\n'.join(playerScores)
    file = discord.File('assets/images/hikari_and_nozomi.jpg', filename='hikari_and_nozomi.jpg')
    embed = discord.Embed(title='Leaderboard', description=playerdata, color=0x00ff00)
    embed.set_image(url='attachment://hikari_and_nozomi.jpg')
    await ctx.channel.send(file=file, embed=embed)        


@bot.command()
async def positivity(ctx):
    """
    Prints out a leaderboard based on message sentiment in Embed format
    """
    server = [guild for guild in bot.guilds if guild.name == ctx.guild.name]
    cur = db.cursor()
    cur.execute("""
                SELECT users.name, AVG(sentiment) AS mood
                FROM users
                JOIN messages ON messages.users_id = users.id
                WHERE servers_id = %s
                GROUP BY users.name
                HAVING AVG(sentiment) != 0
                ORDER BY mood DESC;""", (server[0].id,))
    rows = cur.fetchall()
    cur.close()
    memberNames = [member.name for member in server[0].members]
    playerScores = [name.replace("_", r"\_") + ':\t' + str(points)[:5] for name, points in rows if name in memberNames]
    if len(playerScores) > LEADERBOARD_MAX:
        playerScores = playerScores[:LEADERBOARD_MAX]
    playerdata = '\n'.join(playerScores)
    file = discord.File('assets/images/hikari_and_nozomi.jpg', filename='hikari_and_nozomi.jpg')
    embed = discord.Embed(title='Mood Levels', description=playerdata, color=0x00ff00)
    embed.set_image(url='attachment://hikari_and_nozomi.jpg')
    await ctx.channel.send(file=file, embed=embed)       


@bot.command()
async def record(ctx):
    if not ctx.author.voice:
        pass


def compare_roles(prev_roles, curr_roles):
    """        
    Compare two role lists to determine whether roles were added or removed and returns a list
    """        
    operation = 'Added' if len(prev_roles) < len(curr_roles) else 'Removed' # True if add
    difference = list(set(curr_roles) - set(prev_roles)) if operation == 'Added' else list(set(prev_roles) - set(curr_roles))
    return [operation] + difference


def gambling():
    """
    Get a number between 1 and 100 and return a string pertaining to a win/loss
    """
    chance_of_win = 1
    random_number = random.randint(1, 100)
    return "WOW!" if random_number <= chance_of_win else "AW DANGIT"


def main():
    bot.run(TOKEN)


if __name__ == "__main__":
    main()