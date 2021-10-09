import discord
# pip install -U discord.py
from discord.ext import commands
# pip install -U discord-py-slash-command
from discord_slash import SlashCommand, SlashContext, cog_ext
from discord_slash.utils.manage_commands import create_option
from discord.ext.commands import Cog, command, has_permissions, MissingPermissions
from os import path
from cogs.Core import Core, ApplicationCommandOptionType

class BotManagement(commands.Cog):
    """Commands for managing the Hierarchies bot."""
    _instance = None

    def __new__(cls, bot):
        if cls._instance is None:
            cls._instance = super(BotManagement, cls).__new__(cls)
            # Put any initialization here.
        return cls._instance

    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    """

    setlogger

    """
    @cog_ext.cog_slash(name="setlogger", description="Sets the channel that Hierarchies commands will be logged to.",
        options=[
          create_option(name="channel", description="The channel for logging", option_type=ApplicationCommandOptionType.CHANNEL, required=True)
        ]
    )
    async def _setlogger(self, ctx: SlashContext, *, channel: discord.TextChannel):
        await self.setlogger(ctx=ctx, channel=channel)

    @commands.command(pass_context=True)
    @has_permissions(manage_roles=True)
    async def setlogger(self, ctx: discord.ext.commands.Context, channel: discord.TextChannel):
        """Sets the channel that Hierarchies commands will be logged to."""

        server_id = ctx.message.guild.id
        Core.lock_server_file(server_id)
        server_json = Core.get_server_json(server_id)

        server_json['log_channel'] = channel.id

        Core.save_server_file(server_id, server_json)
        Core.unlock_server_file(server_id)

        # Can only log setCore.logger to console, not Discord
        print(f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) ran `setCore.logger` <#{channel.mention}.')
        return await ctx.send(f'Set Core.logger channel to {channel.mention}.')

    """

    unlock

    """
    @cog_ext.cog_slash(name="unlock", description="Unlocks the mutex file if the bot crashes during a Hierarchies command.")
    async def _unlock(self, ctx: SlashContext):
        await self.unlock(ctx=ctx)

    @commands.command(pass_context=True)
    @has_permissions(manage_roles=True)
    async def unlock(self, ctx: discord.ext.commands.Context):
        """Unlocks the mutex file if the bot crashes during a Hierarchies command."""

        server_id = ctx.message.guild.id
        if path.isfile(str(server_id) + '.lck'):
            Core.unlock_server_file(server_id)
            await Core.logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator})' +
                         ' successfully ran `unlock`.')
            return await ctx.send('Server file unlocked.')
        else:
            await Core.logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator})' +
                         ' unsuccessfully ran `unlock`.')
            return await ctx.send('Server file was not locked.')

