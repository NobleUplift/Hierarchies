import sys
import traceback
import discord
from discord.ext import commands
import os.path
from os import path
from pathlib import Path
import json
from discord_token import token
from typing import Union

import importlib

from cogs.HierarchiesUtilities import lock_server_file, get_server_json, save_server_file, unlock_server_file, logger, has_manage_roles


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

    @commands.command(pass_context=True)
    @has_manage_roles()
    async def setlogger(self, ctx: discord.ext.commands.Context, channel: discord.TextChannel):
        """Sets the channel that Hierarchies commands will be logged to."""

        server_id = ctx.message.guild.id
        lock_server_file(server_id)
        server_json = get_server_json(server_id)

        server_json['log_channel'] = channel.id

        save_server_file(server_id, server_json)
        unlock_server_file(server_id)

        # Can only log setlogger to console, not Discord
        print(f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) ran `setlogger` <#{channel.mention}.')
        return await ctx.send(f'Set logger channel to {channel.mention}.')

    @commands.command(pass_context=True)
    @has_manage_roles()
    async def unlock(self, ctx: discord.ext.commands.Context):
        """Unlocks the mutex file if the bot crashes during a Hierarchies command."""

        server_id = ctx.message.guild.id
        if path.isfile(str(server_id) + '.lck'):
            unlock_server_file(server_id)
            await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator})' +
                         ' successfully ran `unlock`.')
            return await ctx.send('Server file unlocked.')
        else:
            await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator})' +
                         ' unsuccessfully ran `unlock`.')
            return await ctx.send('Server file was not locked.')

