from enum import member
import os
import discord
import random
import psycopg2
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from dotenv import load_dotenv
import time
from google import genai
# from openai import OpenAI

# import nltk
# nltk.download('all')

load_dotenv()
API_KEY = os.getenv("GENAI_API_KEY")
# GPT_KEY = os.getenv("CHATGPT_API_KEY")
TOKEN = os.getenv('DISCORD_TOKEN')

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

db = psycopg2.connect(database = "discord", 
                        user = "postgres", 
                        host= 'localhost',
                        password = "123456",
                        port = 5432)

def getSentiment(text):
    analyzer = SentimentIntensityAnalyzer()
    scores = analyzer.polarity_scores(text)
    return scores

class MyClient(discord.Client):
    async def on_ready(self):
        # messages on startup
        print(f'We have logged in as {self.user}')

        status = discord.CustomActivity('Gambling!')
        await self.change_presence(activity=status)

        channel = self.get_channel(1348173982221991946)
        if channel:
            await channel.send('LETS GO GAMBLING!')
            # await channel.send(response.text)
        else:
            print("Failed to send message to channel", channel)
        
        # TODO: Create a table per server with member data and whenever a guild member sends a message, update the member data for that guild
        
        server = [guild for guild in self.guilds if guild.name == '🔥𝓘𝓭𝓸𝓽🔥']
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
        
    async def on_member_update(self, before, after):
        # print(f'Before: {before}')
        # print(f'After: {after}')
        channel = self.get_channel(1348173982221991946)
        await channel.send(f'{after.mention} I know who you are.')
        pass

    async def on_message_delete(self, message):
        await message.author.send('https://tenor.com/view/dbz-discord-gif-24306382')

    async def on_message(self, message):
        # print(message)
        # responds when a user sends a message with a valid command prefix
        if message.author == self.user or message.author.bot:
            return        
        else:
            # print(type(message.author.name))
            if message.guild is None and not message.attachments:
                # if message.attachments:
                #     # print(message.attachments[0].url)
                #     thing = message.attachments[0].url
                #     await message.author.send(thing)
                # else:

                # ------------GEMINI IMPLEMENTATION------------
                user_prompt = message.content
                response = client.models.generate_content(
                    model='gemini-2.0-flash', 
                    contents='You are Nozomi Tachibana, a member of the Central Control Center, the student council of Highlander from the game Blue Archive.'
                    'Despite your position, you tend not to take your work seriously and are often causing trouble with your twin sister Hikari Tachibana.'
                    'You are usually bratty and often mischievous, frequently causing trouble due to your playful behavior and lack of concern for consequences.'
                    f'Given this context, compose an appropriate reponse consistent with your personality to {user_prompt}. Keep your response sharp, snappy, and brief.'
                )
                
                await message.author.send(response.text)

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

            # if 'gambling' in message.content:
            #     await message.add_reaction('😱')

            # if message.author.name == '':
            #     if random.randint(1, 1000) == 1:
            #        file = discord.File('assets/videos/yapper-yap.mp4', filename='yapper-yap.mp4')
            #        await message.reply(file=file)

            # TODO: ignore bot messages
            cur = db.cursor()
            cur.execute(f"INSERT INTO leaderboard(author_id, author_username, points) VALUES('{message.author.id}', '{message.author.name}', 1)" +
                        " ON CONFLICT (author_id) DO UPDATE SET points = leaderboard.points + 1;")
            db.commit()
            cur.close()

            print(f"{message.author.name}: {message.content}")
            if len(message.content.split()) >= 3 and message.channel.id == 1348173982221991946:
                score = getSentiment(message.content)
                await message.channel.send(f'Sentiment score: {score}')
        
        commands = {
            '$commands': self.command_commands,
            '$hello': self.command_hello,
            '$image': self.command_image,
            '$video': self.command_video,
            '$gamble': self.command_gamble,
            '$leaderboard': self.command_leaderboard
        }

        if self.user.mentioned_in(message):
            await message.channel.send(f"{message.author.mention} Check DMs.")
            time.sleep(1)
            await message.author.send('I am rapidly approaching your location.')

        for command, function in commands.items():
            if message.content.startswith(command.lower()):
                await function(message)
                break

    async def command_commands(self, message):
        # Man I don't want to write into this thing every single time we add something it would be so cool if we stored command objects 
        # leave technical debt for another day
        await message.channel.send('List of commands:\n'
        '$commands - Show commands\n'
        '$hello - Say hello\n'
        '$image - Send an image\n'
        '$video - Send a video\n'
        '$gamble - Gamble!\n'
        '$leaderboard - Display leaderboard\n')

    async def command_hello(self, message):
        await message.channel.send('Imma touch you lil bro')
        await message.author.send('I know where you live')

    async def command_image(self, message):
        file = discord.File('assets/images/hikari_and_nozomi.jpg', filename='hikari_and_nozomi.jpg')
        await message.channel.send(file=file)

    async def command_video(self, message):  
        file = discord.File('assets/videos/apt.mp4', filename='apt.mp4')
        await message.channel.send(file=file)

    async def command_gamble(self, message):
        result = self.gambling()
        await message.channel.send(f'{message.author.mention} {result}')

    async def command_leaderboard(self, message):
        cur = db.cursor()
        cur.execute("SELECT author_username, points FROM leaderboard ORDER BY points DESC;")
        rows = cur.fetchall()
        cur.close()

        server = [guild for guild in self.guilds if guild.name == message.guild.name]
        member_names = [member.name for member in server[0].members]
        playerdata = '\n'.join([name.replace("_", r"\_") + ':\t' + str(points) for name, points in rows if name in member_names and points > 0])
        file = discord.File('assets/images/hikari_and_nozomi.jpg', filename='hikari_and_nozomi.jpg')
        embed = discord.Embed(title='Leaderboard', description=playerdata, color=0x00ff00)
        embed.set_image(url='attachment://hikari_and_nozomi.jpg')
        await message.channel.send(file=file, embed=embed)

    def gambling(self):
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