import discord
from discord import app_commands
from discord.ext import commands
import os

class Tips(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="tips", description="Post Viking and Cesare tips images to specific threads")
    async def tips_command(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("❌ This command must be used in a server.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        channel_name = "r4-assistant-tips"

        # 1. Find or Create Channel
        target_channel = discord.utils.get(guild.text_channels, name=channel_name)
        
        if not target_channel:
            try:
                target_channel = await guild.create_text_channel(name=channel_name)
                await interaction.followup.send(f"✅ Created channel: {target_channel.mention}", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"❌ Failed to create channel '{channel_name}': {e}", ephemeral=True)
                return
        
        # Configurations for different tips
        tip_configs = [
            {
                "thread_name": "viking tips / 維京人攻略",
                "img_dir": "img/viking"
            },
            {
                "thread_name": "cesare tips / 雷哥攻略",
                "img_dir": "img/cesare"
            }
        ]

        results = []

        for config in tip_configs:
            result = await self.process_tip_thread(interaction, target_channel, config)
            results.append(result)

        await interaction.followup.send("\n".join(results), ephemeral=True)

    async def process_tip_thread(self, interaction, channel, config):
        thread_name = config["thread_name"]
        img_dir = config["img_dir"]

        # 2. Find or Create Thread
        target_thread = None
        
        # Check active threads
        for thread in channel.threads:
            if thread.name == thread_name:
                target_thread = thread
                break
        
        # If not found in active, ideally we should check archived, but for now we create if not active per user request logic implied
        # (User said: "if the thread of cesare and viking already exist, no need to create the thread again")
        
        if not target_thread:
            try:
                target_thread = await channel.create_thread(name=thread_name, type=discord.ChannelType.public_thread)
            except Exception as e:
                return f"❌ Failed to create thread '{thread_name}': {e}"
        
        # 3. Post Images
        if not os.path.isdir(img_dir):
             return f"⚠️ Directory '{img_dir}' not found for '{thread_name}'."

        # Get all files and sort them to ensure order (e.g. Viking_1, Viking_2 or just alphabetical)
        try:
            files = sorted([f for f in os.listdir(img_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))])
        except Exception as e:
            return f"❌ Error listing files in '{img_dir}': {e}"

        if not files:
            return f"⚠️ No images found in '{img_dir}'."

        count = 0
        try:
            for filename in files:
                file_path = os.path.join(img_dir, filename)
                with open(file_path, 'rb') as f:
                    picture = discord.File(f, filename=filename)
                    await target_thread.send(file=picture)
                count += 1
            
            return f"✅ Posted {count} images to {target_thread.mention}!"

        except Exception as e:
            return f"❌ Error posting images to '{thread_name}': {e}"


async def setup(bot):
    await bot.add_cog(Tips(bot))
