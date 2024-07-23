import discord
from discord.ext import commands, tasks
import os
import hashlib
import requests
import json
from dotenv import load_dotenv
import base64
from itertools import cycle


bot = commands.Bot(command_prefix=".", intents=discord.Intents.all())
bot_statuses = cycle(["giving scripts", "Hello from skidded", "Skidding Code rn", "Sub to @RuckConfigs"])

@tasks.loop(seconds=20)
async def change_bot_status():
    await bot.change_presence(activity=discord.Game(next(bot_statuses)))

@bot.event
async def on_ready():
    print("Bot is ready!")
    change_bot_status.start()
    try:
        synced_commands = await bot.tree.sync()
        print(f"Synced {len(synced_commands)} commands.")
    except Exception as e:
        print("An error with syncing application commands has occurred: ", e)

# Slash Command for Hashing a User
@bot.tree.command(name="hash_a_account", description="Hashes player Username and userid")
async def hashuser(interaction: discord.Interaction, roblox_user_name: str, roblox_user_id: str):
    # Concatenate the username and user_id
    data = roblox_user_name + roblox_user_id
    
    # Hash the data using SHA-512
    hashed_data = hashlib.sha512(data.encode()).hexdigest()

    # Send the hashed data back to the user
    await interaction.response.send_message(f"Your Hashed Data: {hashed_data}", ephemeral=True)

# Modal for Sending a Whitelist Request
class SendWhitelistRequestModal(discord.ui.Modal, title="Send a Whitelist Request"):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    roblox_hash = discord.ui.TextInput(label="User's Hash", placeholder="Get your hash with the **/hash_a_account** command", required=True, style=discord.TextStyle.long)
    discord_user_id = discord.ui.TextInput(label="Discord ID", placeholder="e.g., 9293812310293", required=True, style=discord.TextStyle.short)
    discord_user_name = discord.ui.TextInput(label="Discord Username", placeholder="e.g., skidded101", required=True, style=discord.TextStyle.short)

    async def on_submit(self, interaction: discord.Interaction):
        owner_id = 786248813270532107  # Replace with the actual Discord user ID of the bot owner
        owner = await self.bot.fetch_user(owner_id)

        embed = discord.Embed(title="Whitelist Request", description="A new whitelist request has been submitted.", color=discord.Color.green())
        embed.add_field(name="Roblox Hash", value=self.roblox_hash.value, inline=False)
        embed.add_field(name="Discord ID", value=self.discord_user_id.value, inline=False)
        embed.add_field(name="Discord Username", value=self.discord_user_name.value, inline=False)

        await owner.send(embed=embed)
        await interaction.response.send_message("Whitelist request sent. Please wait for approval.", ephemeral=True)

# Slash Command for Sending a Whitelist Request
@bot.tree.command(name="send_whitelist_request", description="Sends a Whitelist request to Skidded")
@commands.cooldown(1, 20, commands.BucketType.user)
@commands.has_role("「Ember™」Premium")  # Replace 'SpecificRoleName' with the name of the role you want to restrict the command to
async def send_whitelist_request(interaction: discord.Interaction):
    modal = SendWhitelistRequestModal(bot)  # Pass the bot instance
    await interaction.response.send_modal(modal)

# Slash Command for Adding to Whitelist
@bot.tree.command(name="add_to_whitelist", description="Add or update a user in the whitelist")
@commands.has_role("Scorched")
async def add_to_whitelist(
    interaction: discord.Interaction,
    discord_user_id: str,
    roblox_hash: str,
    attackable: str,
    level: int,
    tag_text: str,
    tag_color: str
):
    # Validate the 'attackable' value
    if attackable.lower() not in ['true', 'false']:
        await interaction.response.send_message("Invalid value for 'attackable'. Please use 'true' or 'false'.", ephemeral=True)
        return

    # Process the inputs
    attackable = attackable.lower() == 'true'
    tag_color = list(map(int, tag_color.split(',')))

    # Update GitHub repository
    github_token = os.getenv("GITHUB_TOKEN")
    repo_name = "skiddedruck/whitelists"
    file_path = "PlayerWhitelist.json"
    branch_name = "main"

    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Fetch the existing file
    response = requests.get(f"https://api.github.com/repos/{repo_name}/contents/{file_path}?ref={branch_name}", headers=headers)
    if response.status_code != 200:
        await interaction.response.send_message("Failed to fetch the JSON file from GitHub.", ephemeral=True)
        return

    content = response.json()
    file_content = requests.get(content['download_url']).text
    data = json.loads(file_content)

    # Update or add the whitelist entry
    if discord_user_id in data["WhitelistedUsers"]:
        # Update existing entry
        data["WhitelistedUsers"][discord_user_id].update({
            "hash": roblox_hash,
            "attackable": attackable,
            "level": level,
            "tags": [
                {
                    "text": tag_text,
                    "color": tag_color
                }
            ]
        })
        message = f"Updated whitelisted user {discord_user_id}"
    else:
        # Add new entry
        data["WhitelistedUsers"][discord_user_id] = {
            "hash": roblox_hash,
            "attackable": attackable,
            "level": level,
            "tags": [
                {
                    "text": tag_text,
                    "color": tag_color
                }
            ]
        }
        message = f"Added whitelisted user {discord_user_id}"

    # Prepare the updated content for GitHub
    updated_content = json.dumps(data, indent=4).encode('utf-8')

    update_data = {
        "message": message,
        "content": base64.b64encode(updated_content).decode('utf-8'),
        "sha": content["sha"],
        "branch": branch_name
    }

    # Update the file on GitHub
    update_response = requests.put(f"https://api.github.com/repos/{repo_name}/contents/{file_path}", headers=headers, data=json.dumps(update_data))
    if update_response.status_code == 200:
        await interaction.response.send_message("Whitelist updated successfully.", ephemeral=True)
    else:
        await interaction.response.send_message("Failed to update the JSON file on GitHub.", ephemeral=True)



# Slash Command for Removing from Whitelist
@bot.tree.command(name="unwhitelist", description="Remove a user from the whitelist")
@commands.has_role("Scorched")
async def unwhitelist(interaction: discord.Interaction, discord_user_id: str):
    # Update GitHub repository
    github_token = os.getenv("GITHUB_TOKEN")
    repo_name = "skiddedruck/whitelists"
    file_path = "PlayerWhitelist.json"
    branch_name = "main"

    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Fetch the existing file
    response = requests.get(f"https://api.github.com/repos/{repo_name}/contents/{file_path}?ref={branch_name}", headers=headers)
    if response.status_code != 200:
        await interaction.response.send_message("Failed to fetch the JSON file from GitHub.", ephemeral=True)
        return

    content = response.json()
    file_content = requests.get(content['download_url']).text
    data = json.loads(file_content)

    # Remove the user from the whitelist if they exist
    if discord_user_id in data["WhitelistedUsers"]:
        del data["WhitelistedUsers"][discord_user_id]
        message = f"Removed whitelisted user {discord_user_id}"
    else:
        await interaction.response.send_message(f"No whitelist entry found for user ID {discord_user_id}.", ephemeral=True)
        return

    # Prepare the updated content for GitHub
    updated_content = json.dumps(data, indent=4).encode('utf-8')

    update_data = {
        "message": message,
        "content": base64.b64encode(updated_content).decode('utf-8'),
        "sha": content["sha"],
        "branch": branch_name
    }

    # Update the file on GitHub
    update_response = requests.put(f"https://api.github.com/repos/{repo_name}/contents/{file_path}", headers=headers, data=json.dumps(update_data))
    if update_response.status_code == 200:
        await interaction.response.send_message("User removed from the whitelist.", ephemeral=True)
    else:
        await interaction.response.send_message("Failed to update the JSON file on GitHub.", ephemeral=True)





# Error handling for the whitelist request command
@send_whitelist_request.error
async def sendwhitelistreq_error(interaction: discord.Interaction, error: commands.CommandError):
    if isinstance(error, commands.CommandOnCooldown):
        await interaction.response.send_message(f"This command is on cooldown. Please try again after {int(error.retry_after)} seconds.", ephemeral=True)
    elif isinstance(error, commands.MissingRole):
        await interaction.response.send_message("You do not have the required role to use this command.", ephemeral=True)
    else:
        await interaction.response.send_message("An error occurred while processing the command.", ephemeral=True)




async def Load():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")

async def main():
    async with bot:
        await Load()
        await bot.start(os.getenv("TOKEN"))

@bot.command(aliases=["hello", "gaming", "gaming2"])
async def hi(ctx=None):
    await ctx.send(f"hi! {ctx.author.mention}")

@bot.command()
async def sendembed(ctx):
    embeded_msg = discord.Embed(title="title of embed", description="description of embed", colour=discord.Color.red())
    embeded_msg.set_thumbnail(url=ctx.author.avatar.url)
    embeded_msg.add_field(name="Name of field", value="Value of field", inline=False)
    embeded_msg.set_image(url=ctx.guild.icon.url)
    embeded_msg.set_footer(text="FooterText", icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embeded_msg)

@bot.command()
async def ping(ctx):
    ping_embed = discord.Embed(title="Ping", description="Latency in ms", color=discord.Color.red())
    ping_embed.add_field(name=f"{bot.user.name}'s Latency (ms): ", value=f"{round(bot.latency * 1000)}ms. ", inline=False)
    ping_embed.set_footer(text=f"(Requested by {ctx.author.name}.)", icon_url=ctx.author.avatar.url)
    await ctx.send(embed=ping_embed)

load_dotenv()
bot.run(os.getenv("TOKEN"))
