import os
import discord
import random
import psycopg2
# import psycopg
from nltk.sentiment.vader import SentimentIntensityAnalyzer # import this after running the below imports
from dotenv import load_dotenv
import time
from google import genai
from datetime import datetime
import logging
# from openai import OpenAI

# Import all modules: pip install -r requirements.txt
# Run docker: docker-compose up -d --build

# run this first if you want to use nltk
# import nltk
# nltk.download('all')

load_dotenv()
API_KEY = os.getenv("GENAI_API_KEY")
# GPT_KEY = os.getenv("CHATGPT_API_KEY")
TOKEN = os.getenv("DISCORD_TOKEN")
SERVER_NAME = os.getenv("SERVER_NAME")
BOT_CHANNEL = int(os.getenv("BOT_CHANNEL_ID"))
AUDIT_CHANNEL = int(os.getenv("AUDIT_CHANNEL_ID"))
LEADERBOARD_MAX = 15

client = genai.Client(api_key=API_KEY)
# client = OpenAI(api_key=GPT_KEY)

# messages = [ {"role": "system", "content": 
#               'You are Nozomi Tachibana, a member of the Central Control Center, the student council of Highlander from the game Blue Archive.'
#                     'Despite your position, you tend not to take your work seriously and are often causing trouble with your twin sister Hikari Tachibana.'
#                     'You are usually bratty and often mischievous, frequently causing trouble due to your playful behavior and lack of concern for consequences.'
#                     'Keep your responses sharp, snappy, and brief.'} ]

"""
To invite this bot into your dicord server, use the link
https://discord.com/oauth2/authorize?client_id=1348147223426236487&permissions=2147600448&integration_type=0&scope=bot

https://github.com/google-gemini/generative-ai-python
"""

# TODO: update code to new psycop module

logging.basicConfig(filename="activity.log", level=logging.INFO)

db = psycopg2.connect(database = "discord", 
                        user = "postgres", 
                        host= 'localhost',
                        password = "123456",
                        port = 5432)

def getSentiment(text):
    """
    Uses the NLTK library to calculate a sentiment score from a message
    """
    analyzer = SentimentIntensityAnalyzer()
    scores = analyzer.polarity_scores(text)
    return scores

class MyClient(discord.Client):
    async def on_ready(self):
        """
        Send a message on startup, and insert every user in every server into the leaderboard
        """
        print(f'We have logged in as {self.user}')

        status = discord.CustomActivity('Gambling!')
        await self.change_presence(activity=status)

        channel = self.get_channel(BOT_CHANNEL)
        if channel:
            # await channel.send('LETS GO GAMBLING!')
            # print(datetime.today().strftime('%Y-%m-%d %H:%M:%S'))
            pass
        else:
            print("Failed to send message to channel", channel)
        
        # TODO: Create a table per server with member data and whenever a guild member sends a message, update the member data for that guild
        
        server = [guild for guild in self.guilds if guild.name == SERVER_NAME]
        member_info = [(member.name, member.id) for member in server[0].members]
        cur = db.cursor()
        for member in member_info:
            id = str(member[1])
            user = str(member[0])
            # cur.execute(f"INSERT INTO leaderboard(author_id, author_username, points) VALUES({id}, '{user}', 1) " +
            #             f"WHERE NOT EXISTS (SELECT * FROM leaderboard WHERE author_id = {id});")
            cur.execute(f"INSERT INTO leaderboard(author_id, author_username, points) VALUES('{id}', '{user}', 0)" +
                        " ON CONFLICT (author_id) DO UPDATE SET points = leaderboard.points;")
        db.commit()
        cur.close()
        
    async def on_user_update(self, before, after):
        """
        Audits when a user changes their username. Getting their old display avatar doesn't work so this function is only for username changes
        """
        server = [guild for guild in self.guilds if guild.name == SERVER_NAME]
        if after in [member for member in server[0].members]:
            channel = self.get_channel(AUDIT_CHANNEL)
            message = ''

            if before.name != after.name:
                message = f'<@{after.id}> changed their username from {before.name} to {after.name}'

            if message:
                await channel.send(message)

    async def on_member_update(self, before, after):
        """
        When a member updates their information, disclose what information has changed
        """
        server = [guild for guild in self.guilds if guild.name == SERVER_NAME]
        if after in [member for member in server[0].members]:
            channel = self.get_channel(AUDIT_CHANNEL)
            message = ''
            attachment = ''

            if before.nick != after.nick:
                message = f'<@{after.id}> changed their nickname from {before.nick} to {after.nick}'
            elif before.roles != after.roles:
                result = self.compare_roles(before.roles, after.roles)
                message = f'<@{after.id}>: {result[0]} role {result[1]}'
            else:
                message = f'<@{after.id}> changed their profile picture or avatar decoration'
                attachment = await after.display_avatar.to_file(spoiler = False)

            await channel.send(message, file=attachment)

    async def on_voice_state_update(self, member, before, after):
        """
        Log the time, user, and channel whenever someone joins/leaves a voice channel
        """
        timestamp = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        if not before.channel and after.channel and after.channel.guild.name == SERVER_NAME:
            logging.info(f'[{timestamp}] {member} has joined {after.channel.name}')
        elif before.channel and not after.channel and before.channel.guild.name == SERVER_NAME:
            logging.info(f'[{timestamp}] {member} has left {before.channel.name}')
        

    async def on_message_delete(self, message):
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
            channel = self.get_channel(AUDIT_CHANNEL)
            try:
                await channel.send(f'Deleted message from {message.author.name}: {message.content}', files=deletedFiles)
            except:
                await channel.send(f'Deleted message from {message.author.name}: {message.content}\nAttachments: File too large')

    async def on_message_edit(self, before, after):
        """
        Detects when a message is edited and sends the before and after into the audit channel
        """
        if not after.author.bot and before.content != after.content and after.guild and after.guild.name == SERVER_NAME:
            channel = self.get_channel(AUDIT_CHANNEL)
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
                

    async def on_message(self, message):
        """
        Performs various actions pertaining to the content of a user message
        """
        if message.author == self.user or message.author.bot:
            return        
        else:
            # Generate a response when a user either direct messages the bot or pings the bot in a server
            if (message.guild is None and not message.attachments) or (self.user.mentioned_in(message) and message.guild is not None):
                # ------------GEMINI IMPLEMENTATION------------
                user_prompt = message.content
                response = client.models.generate_content(
                    model='gemini-2.0-flash', 
                    # Insert your prompt here
                    contents='You are Nozomi Tachibana, a member of the Central Control Center, the student council of Highlander from the game Blue Archive.'
                    'Despite your position, you tend not to take your work seriously and are often causing trouble with your twin sister Hikari Tachibana.'
                    'You are usually bratty and often mischievous, frequently causing trouble due to your playful behavior and lack of concern for consequences.'
                    f'Given this context, compose an appropriate reponse consistent with your personality to {user_prompt}. Keep your response sharp, snappy, and brief.'
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

            cur = db.cursor()
            cur.execute(f"INSERT INTO leaderboard(author_id, author_username, points) VALUES('{message.author.id}', '{message.author.name}', 1)" +
                        " ON CONFLICT (author_id) DO UPDATE SET points = leaderboard.points + 1;")
            db.commit()
            cur.close()

            # Get sentiment score and ignore neutral messages
            print(f"{message.author.name}: {message.content}")
            timestamp = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
            logging.info(f"[{timestamp}] {message.author.name}: {message.content}")
            if len(message.content.split()) >= 3 and message.channel.id == BOT_CHANNEL:
                score = getSentiment(message.content)
                if score['compound'] != 0:
                    await message.channel.send(f'Sentiment score: {score}')
        

        # Emotionally uplifting videos

        wordbank = {'kms', 'killmyself', 'killingmyself'}

        for word in wordbank:
            if word in message.content.lower().replace(" ", ""):
                file = (discord.File('assets/videos/nkys0.mp4', filename='never_kill_yourself.mp4') if random.randint(0,1) == 0 else 
                        discord.File('assets/videos/nkys1.mp4', filename='never_kill_yourself.mp4'))
                await message.reply(file=file)
                break

        commands = {
            '$commands': self.command_commands,
            '$hello': self.command_hello,
            '$image': self.command_image,
            '$video': self.command_video,
            '$gamble': self.command_gamble,
            '$leaderboard': self.command_leaderboard
        }

        for command, function in commands.items():
            if message.content.startswith(command.lower()):
                await function(message)
                break

    async def command_commands(self, message):
        """
        Send the command list and their descriptions
        TODO Make some better system to hold command information
        """
        await message.channel.send('List of commands:\n'
        '$commands - Show commands\n'
        '$hello - Say hello\n'
        '$image - Send an image\n'
        '$video - Send a video\n'
        '$gamble - Gamble!\n'
        '$leaderboard - Display leaderboard\n')

    async def command_hello(self, message):
        """
        Sends a message to the channel and to the user
        """
        await message.channel.send('Imma touch you lil bro')
        await message.author.send('I know where you live')

    async def command_image(self, message):
        """
        Sends an image
        """
        file = discord.File('assets/images/hikari_and_nozomi.jpg', filename='hikari_and_nozomi.jpg')
        await message.channel.send(file=file)

    async def command_video(self, message):  
        """
        Sends a video
        """
        file = discord.File('assets/videos/apt.mp4', filename='apt.mp4')
        await message.channel.send(file=file)

    async def command_gamble(self, message):
        """
        Gambles pings the user the result 
        """
        result = self.gambling()
        await message.channel.send(f'{message.author.mention} {result}')

    async def command_leaderboard(self, message):
        """
        Prints out a leaderboard in an Embed format
        """
        cur = db.cursor()
        cur.execute("SELECT author_username, points FROM leaderboard ORDER BY points DESC;")
        rows = cur.fetchall()
        cur.close()

        server = [guild for guild in self.guilds if guild.name == message.guild.name]
        memberNames = [member.name for member in server[0].members]
        playerScores = [name.replace("_", r"\_") + ':\t' + str(points) for name, points in rows if name in memberNames and points > 0]
        if len(playerScores) > LEADERBOARD_MAX:
            playerScores = playerScores[:LEADERBOARD_MAX]
        playerdata = '\n'.join(playerScores)
        file = discord.File('assets/images/hikari_and_nozomi.jpg', filename='hikari_and_nozomi.jpg')
        embed = discord.Embed(title='Leaderboard', description=playerdata, color=0x00ff00)
        embed.set_image(url='attachment://hikari_and_nozomi.jpg')
        await message.channel.send(file=file, embed=embed)

    def compare_roles(self, prev_roles, curr_roles):
        """        
        Compare two role lists to determine whether roles were added or removed and returns a list
        """        
        operation = 'Added' if len(prev_roles) < len(curr_roles) else 'Removed' # True if add
        difference = list(set(curr_roles) - set(prev_roles)) if operation == 'Added' else list(set(prev_roles) - set(curr_roles))
        return [operation] + difference

    def gambling(self):
        """
        Get a number between 1 and 100 and return a string pertaining to a win/loss
        """
        chance_of_win = 1
        random_number = random.randint(1, 100)

        if random_number <= chance_of_win:
            return 'WON!'
        else:
            return 'AW DANGIT'

def main():
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    client = MyClient(intents=intents)
    client.run(TOKEN)

if __name__ == "__main__":
    main()