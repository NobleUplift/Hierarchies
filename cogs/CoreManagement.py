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


class ApplicationCommandOptionType:
    SUB_COMMAND = 1
    SUB_COMMAND_GROUP = 2
    STRING = 3
    INTEGER = 4
    BOOLEAN = 5
    USER = 6
    CHANNEL = 7
    ROLE = 8
    MENTIONABLE = 9


class Core:
    """Core static methods for management of the bot."""

    @staticmethod
    def lock_server_file(server_id):
        if path.isfile('./servers/' + str(server_id) + '.lck'):
            raise Exception('Server file is currently locked.')

        Path('./servers/' + str(server_id) + '.lck').touch()

    @staticmethod
    def get_server_json(server_id):
        if path.isfile('./servers/' + str(server_id) + '.json'):
            contents = Path('./servers/' + str(server_id) + '.json').read_text()
            server_json = json.loads(contents)
            if 'hierarchies' not in server_json:
                server_json['hierarchies'] = {}
            if 'roles' not in server_json:
                server_json['roles'] = {}
            if 'channels' not in server_json:
                server_json['channels'] = {'log': None}
            return server_json
        else:
            Path('./servers/' + str(server_id) + '.json').touch()
            server_json = {
                'hierarchies': {},
                'roles': {},
                'channels': {'log': None}
            }
            return server_json

    @staticmethod
    def save_server_file(server_id, server_json):
        if 'hierarchies' not in server_json:
            server_json['hierarchies'] = {}
        if 'roles' not in server_json:
            server_json['roles'] = {}
        if 'channels' not in server_json:
            server_json['channels'] = {'log': None}
        contents = json.dumps(server_json, indent=4)
        with open('./servers/' + str(server_id) + '.json', "w") as json_file:
            json_file.write(contents)

    @staticmethod
    def unlock_server_file(server_id):
        if path.isfile('./servers/' + str(server_id) + '.lck'):
            os.remove('./servers/' + str(server_id) + '.lck')

    @staticmethod
    async def logger(bot, ctx, message: str):
        print(message)
        server_id = ctx.message.guild.id
        server_json = Core.get_server_json(server_id)

        if 'log_channel' not in server_json:
            raise Exception('Must use `setCore.logger` to set log channel.')

        channel = bot.get_channel(server_json['log_channel'])
        if channel is None:
            raise Exception('No logging channel set.')

        return await channel.send(message)

    #@staticmethod
    #def has_manage_roles():
    #    async def predicate(ctx):
    #        if ctx.author and hasattr(ctx.author, 'guild_permissions') and ctx.author.guild_permissions.manage_roles is True:
    #            return True
    #        else:
    #            raise NoManageRoles('You must have the Manage Roles permission to create, delete, and modify hierarchies.')
    #    return commands.check(predicate)

