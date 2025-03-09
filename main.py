import os
import discord
import random

class MyClient(discord.Client):
    async def on_ready(self):
        print(f'We have logged in as {self.user}')
        channel = self.get_channel(1348173982221991946)
        if channel:
            await channel.send('LETS GO GAMBLING!')
        else:
            print("Failed to send message to channel", channel)
            
    async def on_message(self, message):
        if message.author == self.user:
            return        
        commands = {
            '$commands': self.command_commands,
            '$hello': self.command_hello,
            '$image': self.command_image,
            '$video': self.command_video,
            '$gambling': self.command_gambling,
            '$test': self.command_test
        }

        for command, function in commands.items():
            if message.content.startswith(command):
                await function(message)
                break
    
    async def command_commands(self, message):
        await message.channel.send('List of commands:\n'
        '$commands - Show commands\n'
        '$hello - Say hello\n'
        '$image - Send an image\n'
        '$video - Send a video\n'
        '$gambling - Gamble!\n'
        '$test - Parameter checking\n')

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

    client = MyClient(intents=intents)
    client.run(token)

if __name__ == "__main__":
    main()