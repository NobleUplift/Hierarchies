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

from cogs.Bot import BotManagement
from cogs.Hierarchy import HierarchyManagement
from cogs.Player import PlayerManagement
from custom.Custom import CustomManagement

intents = discord.Intents(messages=True, members=True, guilds=True)

description = '''
Replacement for the "Manage Roles" permission that allows for multiple hierarchies to be defined in Discord roles.
'''
bot = commands.Bot(command_prefix='^', description=description, intents=intents)

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

# SOURCE/COPYRIGHT: https://gist.github.com/EvieePy/7822af90858ef65012ea500bcecf1612
@bot.event
async def on_command_error(ctx: discord.ext.commands.Context, error: Exception):
    """The event triggered when an error is raised while invoking a command.
            Parameters
            ------------
            ctx: commands.Context
                The context used for command invocation.
            error: commands.CommandError
                The Exception raised.
            """

    # This prevents any commands with local handlers being handled here in on_command_error.
    if hasattr(ctx.command, 'on_error'):
        print("Error has on_error attribute, do not process error.")
        ctx.send(error)
        return

    # This prevents any cogs with an overwritten cog_command_error being handled here.
    cog = ctx.cog
    if cog:
        if cog._get_overridden_method(cog.cog_command_error) is not None:
            print("Cog has cog_command_error, allow cog to process this error.")
            ctx.send(error)
            return

    ignored = (commands.CommandNotFound)

    # Allows us to check for original exceptions raised and sent to CommandInvokeError.
    # If nothing is found. We keep the exception passed to on_command_error.
    error = getattr(error, 'original', error)

    # Anything in ignored will return and prevent anything happening.
    if isinstance(error, ignored):
        print("Error is an ignored error instance.")
        return

    if isinstance(error, commands.DisabledCommand):
        await ctx.send(f'{ctx.command} has been disabled.')

    elif isinstance(error, commands.NoPrivateMessage):
        try:
            await ctx.author.send(f'{ctx.command} cannot be used in Private Messages.')
        except discord.HTTPException:
            pass

    # For this error example we check to see where it came from...
    elif isinstance(error, commands.BadArgument):
        if ctx.command.qualified_name == 'setlogger' \
                or ctx.command.qualified_name == 'show' \
                or ctx.command.qualified_name == 'create' \
                or ctx.command.qualified_name == 'delete' \
                or ctx.command.qualified_name == 'add' \
                or ctx.command.qualified_name == 'remove' \
                or ctx.command.qualified_name == 'modify' \
                or ctx.command.qualified_name == 'promote' \
                or ctx.command.qualified_name == 'demote' \
                or ctx.command.qualified_name == 'assign' \
                or ctx.command.qualified_name == 'unassign':
            await ctx.send("Error: " + str(error))

    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Error: " + str(error))

    else:
        # All other Errors not returned come here. And we can just print the default TraceBack.
        print('Unknown exception in command {}:'.format(ctx.command), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
        await ctx.send("Error: " + str(error))

bot.add_cog(BotManagement(bot))
bot.add_cog(HierarchyManagement(bot))
bot.add_cog(PlayerManagement(bot))
bot.add_cog(CustomManagement(bot))
bot.run(token)
