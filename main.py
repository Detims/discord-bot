from enum import member
import os
import discord
import random
import psycopg2
from nltk.sentiment.vader import SentimentIntensityAnalyzer

"""
Are these needed?
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
"""


# import nltk
# nltk.download('all')

"""
To invite this bot into your dicord server, use the link
https://discord.com/oauth2/authorize?client_id=1348147223426236487&permissions=2147600448&integration_type=0&scope=bot

Article Links:
https://www.datacamp.com/tutorial/tutorial-postgresql-python
https://discordpy.readthedocs.io/en/stable/intro.html
https://github.com/datatime27/videos/blob/main/word-tracker/build-scatter-plot.py
https://stackoverflow.com/questions/44862112/how-can-i-send-an-embed-via-my-discord-bot-w-python
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
        channel = self.get_channel(1348173982221991946)
        if channel:
            await channel.send('LETS GO GAMBLING!')
        else:
            print("Failed to send message to channel", channel)
        
        """
        server = [guild for guild in self.guilds if guild.name == '🔥𝓘𝓭𝓸𝓽🔥']
        member_info = [(member.name, member.id) for member in server[0].members]
        cur = db.cursor()
        for member in member_info:
            id = str(member[1])
            user = str(member[0])
            cur.execute(f"INSERT INTO leaderboard(author_id, author_username, points) VALUES({id}, '{user}', 1) WHERE NOT EXISTS (SELECT * FROM leaderboard WHERE author_id = {id});")
        db.commit()
        cur.close()
        """

    async def on_message(self, message):
        # print(message)
        # responds when a user sends a message with a valid command prefix
        if message.author == self.user:
            return        
        else:
            cur = db.cursor()
            cur.execute(f"INSERT INTO leaderboard(author_id, author_username, points) VALUES('{message.author.id}', '{message.author.name}', 1)" +
                        " ON CONFLICT (author_id) DO UPDATE SET points = leaderboard.points + 1;")
            db.commit()
            cur.close()

            print(message.content)
            score = getSentiment(message.content)
            if message.content and message.channel.id == 1348173982221991946:
                await message.channel.send(f'Sentiment score: {score}')
        
        commands = {
            '$commands': self.command_commands,
            '$hello': self.command_hello,
            '$image': self.command_image,
            '$video': self.command_video,
            '$gambling': self.command_gambling,
            '$test': self.command_test,
            '$leaderboard': self.command_leaderboard
        }

        for command, function in commands.items():
            if message.content.startswith(command):
                await function(message)
                break

    async def command_commands(self, message):
        # Man I don't want to write into this thing every single time we add something it would be so cool if we stored command objects 
        # problem for another day
        await message.channel.send('List of commands:\n'
        '$commands - Show commands\n'
        '$hello - Say hello\n'
        '$image - Send an image\n'
        '$video - Send a video\n'
        '$gambling - Gamble!\n'
        '$test - Parameter checking\n'
        '$leaderboard - Display leaderboard\n')

    async def command_hello(self, message):
        await message.channel.send('Imma touch you lil bro')
        await message.author.send('I know where you live')

    async def command_image(self, message):
        file = discord.File('assets/images/hikari_and_nozomi.jpg', filename='hikari_and_nozomi.jpg')
        await message.channel.send('')

    async def command_video(self, message):  
        file = discord.File('assets/videos/apt.mp4', filename='apt.mp4')
        await message.channel.send(file=file)

    async def command_gambling(self, message):
        result = self.gambling()
        await message.channel.send(f'{message.author.mention} {result}')

    async def command_test(self, message):
        params = message.content.split()
        await message.channel.send(f'There are {len(params)} parameters in this message.')

    async def command_leaderboard(self, message):
        cur = db.cursor()
        cur.execute("SELECT author_username, points FROM leaderboard ORDER BY points DESC LIMIT 15;")
        rows = cur.fetchall()
        cur.close()
        
        server = [guild for guild in self.guilds if guild.name == '🔥𝓘𝓭𝓸𝓽🔥']
        # member_names = [mem.name async for mem in server[0].fetch_members(limit=None)] # unneeded API call
        member_names = [member.name for member in server[0].members]
        playerdata = '\n'.join([row + ':\t' + str(points) for row, points in rows if row in member_names])
        embedVar = discord.Embed(title='Leaderboard', description=playerdata, color=0x00ff00)
        await message.channel.send(embed=embedVar)

    def gambling(self):
        chance_of_win = 1
        random_number = random.randint(1, 100)

        if random_number <= chance_of_win:
            return 'WON!'
        else:
            return 'AW DANGIT'
            
def read_token(file_path):
    with open(file_path, 'r') as file:
        return file.read().strip()

def main():
    token = read_token('token.txt')
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    client = MyClient(intents=intents)
    client.run(token)

if __name__ == "__main__":
    main()