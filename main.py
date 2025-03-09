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
            '$hello': self.command_hello,
            '$image': self.command_image,
            '$commands': self.command_commands,
            '/gambling': self.command_gambling,
            '/g': self.command_gambling  
        }

        for command, function in commands.items():
            if message.content.startswith(command):
                await function(message)
                break
    
    async def command_hello(self, message):
        await message.channel.send('Imma touch you lil bro')

    async def command_image(self, message):
        await message.channel.send('')

    async def command_commands(self, message):
        await message.channel.send('List of commands:\n'
        '$hello - Say hello\n'
        '$image - Send an image'
        '$commands - Show commands\n'
        '/g or /gambling - Gamble!\n')

    async def command_gambling(self, message):
        result = self.gambling()
        await message.channel.send(f'{message.author.mention} {result}')

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