import sys, traceback
import discord
from discord.ext import commands
import os.path
from os import path
from pathlib import Path
import json
from discord_token import token

description = '''An example bot to showcase the discord.ext.commands extension
module.
There are a number of utility commands being showcased here.'''
bot = commands.Bot(command_prefix='^', description=description)

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

def lock_server_file(server_id):
    if path.isfile(str(server_id) + '.lck'):
        raise Exception('Server file is currently locked.')

    Path(str(server_id) + '.lck').touch()

def get_server_json(server_id):
    if path.isfile(str(server_id) + '.json'):
        contents = Path(str(server_id) + '.json').read_text()
        server_json = json.loads(contents)
        if 'hierarchies' not in server_json:
            server_json['hierarchies'] = {}
        if 'roles' not in server_json:
            server_json['roles'] = {}
        return server_json
    else:
        Path(str(server_id) + '.json').touch()
        server_json = {
            'hierarchies': {},
            'roles': {}
        }
        return server_json

def save_server_file(server_id, server_json):
    if 'hierarchies' not in server_json:
        server_json['hierarchies'] = {}
    if 'roles' not in server_json:
        server_json['roles'] = {}
    contents = json.dumps(server_json)
    with open(str(server_id) + '.json', "w") as json_file:
        json_file.write(contents)

def unlock_server_file(server_id):
    if path.isfile(str(server_id) + '.lck'):
        os.remove(str(server_id) + '.lck')

@bot.event
async def on_command_error(ctx: discord.ext.commands.Context, error: Exception):
    if isinstance(error, (commands.CommandNotFound)): # , commands.UserInputError
        return
    print(error)
    print(traceback.format_exc())
    server_id = ctx.message.guild.id
    unlock_server_file(server_id)
    return await ctx.send(error)

class NoManageRoles(commands.CheckFailure):
    pass

def has_manage_roles():
    async def predicate(ctx):
        if ctx.author and ctx.author.guild_permissions.manage_roles is True:
            return True
        else:
            raise NoManageRoles('You must have the Manage Roles permission to create, delete, and modify hierarchies.')
    return commands.check(predicate)

@bot.command()
async def list(ctx: discord.ext.commands.Context):
    print(f'{ctx.author.name} <@{ctx.author.id}> ran `list`')
    server_id = ctx.message.guild.id
    server_json = get_server_json(server_id)

    if len(server_json['hierarchies']) == 0:
        return await ctx.send('This server has no hierarchies.')

    server_hierarchies = server_json['hierarchies']
    retval = 'Hierarchies: \n'
    for n in server_hierarchies:
        retval += ' • ' + n + "\n"
    return await ctx.send(retval)

@bot.command()
async def show(ctx: discord.ext.commands.Context, HierarchyName: str):
    print(f'{ctx.author.name} <@{ctx.author.id}> ran `show ' + HierarchyName + '`')
    server_id = ctx.message.guild.id
    server_json = get_server_json(server_id)

    if len(server_json['hierarchies']) == 0:
        return await ctx.send('This server has no hierarchies.')

    server_hierarchies = server_json['hierarchies']
    if HierarchyName not in server_json['hierarchies']:
        return await ctx.send('Hierarchy ' + HierarchyName + ' does not exist on this server.')

    tiers = server_json['hierarchies'][HierarchyName]['tiers']
    retval = 'Hierarchy for ' + HierarchyName + ': \n'
    for tier in tiers:
        spaces = ''
        for x in range(tier['depth']):
            spaces += ':arrow_right:' # '  ' •
        if len(spaces) != 0:
            spaces += ' '
        nextline = spaces + '<@&' + str(tier['role_id']) + '> '
        if tier['promotion_min_depth'] != -1 and tier['promotion_max_depth'] != -1:
            nextline += 'Can Promote: ' + \
                str(tier['promotion_min_depth']) + ' :arrow_down_small: ' + \
                str(tier['promotion_max_depth']) + ' :arrow_double_down: '
        else:
            nextline += 'Cannot Promote :negative_squared_cross_mark: '

        if tier['demotion_min_depth'] != -1 and tier['demotion_max_depth'] != -1:
            nextline += 'Can Demote: ' + \
            str(tier['demotion_min_depth']) + ' :arrow_down_small: ' + \
            str(tier['demotion_max_depth']) + ' :arrow_double_down:'
        else:
            nextline += 'Cannot Demote :negative_squared_cross_mark: '

        nextline += '\n'
        if len(retval + nextline) > 2000:
            await ctx.send(retval)
            retval = nextline
        else:
            retval += nextline
    return await ctx.send(retval)

async def logger(ctx, message: str):
    print(str)
    server_id = ctx.message.guild.id
    server_json = get_server_json(server_id)

    if 'log_channel' not in server_json:
        raise Exception('Must use `setlogger` to set log channel.')

    channel = bot.get_channel(server_json['log_channel'])
    if channel is None:
        raise Exception('No logging channel set.')
    return await channel.send(message)

@bot.command()
@has_manage_roles()
async def setlogger(ctx: discord.ext.commands.Context, channel: discord.TextChannel):
    # Can only log setlogger to console, not Discord
    print(f'{ctx.author.name} <@{ctx.author.id}> ran `setlogger` <#{channel.id}>.')
    server_id = ctx.message.guild.id
    lock_server_file(server_id)
    server_json = get_server_json(server_id)

    server_json['log_channel'] = channel.id

    save_server_file(server_id, server_json)
    unlock_server_file(server_id)

    return await ctx.send(f'Set logger to <#{channel.id}>.')

@bot.command()
@has_manage_roles()
async def unlock(ctx: discord.ext.commands.Context):
    await logger(ctx, f'{ctx.author.name} <@{ctx.author.id}> ran `unlock`.')
    server_id = ctx.message.guild.id
    if path.isfile(str(server_id) + '.lck'):
        unlock_server_file(server_id)
        return await ctx.send('Server file unlocked.')
    else:
        return await ctx.send('Server file was not locked.')

@bot.command()
@has_manage_roles()
async def create(ctx: discord.ext.commands.Context, HierarchyName: str, RootTier: discord.Role):
    await logger(ctx, f'{ctx.author.name} <@{ctx.author.id}> ran `create {HierarchyName}` <@&{RootTier.id}>')
    if ' ' in HierarchyName:
        return await ctx.send('Hierarchies name "' + HierarchyName + '" cannot have spaces in it.')

    server_id = ctx.message.guild.id
    lock_server_file(server_id)
    server_json = get_server_json(server_id)
    server_json_hierarchies = server_json['hierarchies']

    if HierarchyName in server_json_hierarchies:
        unlock_server_file(server_id)
        return await ctx.send('Hierarchy "' + HierarchyName + '" already exists.')

    server_json_hierarchies[HierarchyName] = {
        'tiers': [{
            'role_id': RootTier.id,
            'parent_role_id': 0,
            'depth': 0,
            'promotion_min_depth': 0,
            'promotion_max_depth': 2147483647,
            'demotion_min_depth': 0,
            'demotion_max_depth': 2147483647
        }],
        'maximum_depth': 0
    }
    server_json['roles'][str(RootTier.id)] = HierarchyName

    save_server_file(server_id, server_json)
    unlock_server_file(server_id)

    return await ctx.send('Created hierarchy ' + HierarchyName + '.')

@bot.command()
@has_manage_roles()
async def delete(ctx: discord.ext.commands.Context, HierarchyName: str):
    await logger(ctx, f'{ctx.author.name} <@{ctx.author.id}> ran `delete {HierarchyName}`')
    server_id = ctx.message.guild.id
    lock_server_file(server_id)
    server_json = get_server_json(server_id)
    server_json_hierarchies = server_json['hierarchies']

    if HierarchyName in server_json_hierarchies:
        del server_json_hierarchies[HierarchyName]

        for key in dict(server_json['roles']):
            if server_json['roles'][key] == HierarchyName:
                del server_json['roles'][key]

        save_server_file(server_id, server_json)
        unlock_server_file(server_id)
        return await ctx.send('Deleted hierarchy ' + HierarchyName + '.')
    else:
        unlock_server_file(server_id)
        return await ctx.send('Hierarchy ' + HierarchyName + ' does not exist.')

#
# Possible architectures:
# 1. DoublyLinkedList of hierarchies, each tier contains the tier below it etc.
# PROS:
# - Easy to navigate up and down hierarchy
# CONS
# - Can only have one child per parent
#
# 2. Flat list for each hierarchy
# PROS:
# - Multiple children per parent
# CONS:
# - Must sort list after each addition
#

def recursive_hierarchy_update(old_hierarchy, role_id, depth):
    #print('Calling recursive_hierarchy_update at depth ' + str(depth))
    new_hierarchy = []
    for tier in old_hierarchy:
        #print('Does ' + str(tier['parent_role_id']) + ' equal ' + str(role_id) + '?')
        if 'parent_role_id' in tier and tier['parent_role_id'] == role_id:
            tier['depth'] = depth
            new_hierarchy.append(tier)
            new_hierarchy = new_hierarchy + recursive_hierarchy_update(old_hierarchy, tier['role_id'], depth + 1)
    #print(new_hierarchy)
    return new_hierarchy

@bot.command()
@has_manage_roles()
async def add(
        ctx: discord.ext.commands.Context,
        Tier: discord.Role,
        Parent: discord.Role,
        PromotionMinimumDepth: int = -1,
        PromotionMaximumDepth: int = -1,
        DemotionMinimumDepth: int = -1,
        DemotionMaximumDepth: int = -1
    ):
    await logger(ctx, f'{ctx.author.name} <@{ctx.author.id}> ran `add` <@&{Tier.id}> <@&{Parent.id}>')

    server_id = ctx.message.guild.id
    lock_server_file(server_id)
    server_json = get_server_json(server_id)

    if str(Tier.id) in server_json['roles']:
        unlock_server_file(server_id)
        print('Role already exists in hierarchy ' + str(server_json['roles'][str(Tier.id)]) + '.')
        return await ctx.send('Role already exists in hierarchy ' + str(server_json['roles'][str(Tier.id)]) + '.')

    if str(Parent.id) not in server_json['roles']:
        unlock_server_file(server_id)
        print('Parent role <@&' + str(Parent.id) + '> does not exist in a hierarchy.')
        return await ctx.send('Parent role <@&' + str(Parent.id) + '> does not exist in a hierarchy.')
    hierarchy_name = server_json['roles'][str(Parent.id)]

    if hierarchy_name in server_json['hierarchies']:
        role_added = False
        hierarchy = server_json['hierarchies'][hierarchy_name]['tiers']

        new_tier = {
            'role_id': Tier.id,
            'parent_role_id': Parent.id if Parent is not None else 0,
            'depth': 0,
            'promotion_min_depth': PromotionMinimumDepth,
            'promotion_max_depth': PromotionMaximumDepth,
            'demotion_min_depth': DemotionMinimumDepth,
            'demotion_max_depth': DemotionMaximumDepth
        }

        if len(hierarchy) == 0 and Parent is None:
            server_json['roles'][str(Tier.id)] = hierarchy_name
            hierarchy.append(new_tier)
            role_added = True
        else:
            for tier in hierarchy:
                if 'role_id' in tier and tier['role_id'] == Parent.id:
                    server_json['roles'][str(Tier.id)] = hierarchy_name
                    hierarchy.append(new_tier)
                    role_added = True
        if role_added:
            new_hierarchy = recursive_hierarchy_update(hierarchy, 0, 0)
            server_json['hierarchies'][hierarchy_name]['tiers'] = new_hierarchy
            server_json['hierarchies'][hierarchy_name]['maximum_depth'] = 0
            for tier in server_json['hierarchies'][hierarchy_name]['tiers']:
                if tier['depth'] > server_json['hierarchies'][hierarchy_name]['maximum_depth']:
                    server_json['hierarchies'][hierarchy_name]['maximum_depth'] = tier['depth']
            save_server_file(server_id, server_json)
            unlock_server_file(server_id)
            return await ctx.send('Tier successfully added for role <@&' + str(Tier.id) + '>.')
        else:
            unlock_server_file(server_id)
            return await ctx.send('Parent role does not exist in the hierarchy.')
    else:
        unlock_server_file(server_id)
        return await ctx.send('hierarchy_name ' + str(hierarchy_name) + ' does not exist.')

@bot.command()
@has_manage_roles()
async def remove(ctx: discord.ext.commands.Context, Tier: discord.Role):
    await logger(ctx, f'{ctx.author.name} <@{ctx.author.id}> ran `remove` <@&{Tier.id}>.')

    server_id = ctx.message.guild.id
    lock_server_file(server_id)
    server_json = get_server_json(server_id)

    if str(Tier.id) not in server_json['roles']:
        unlock_server_file(server_id)
        return await ctx.send('Role <@&' + str(Tier.id) + '> does not belong to a hierarchy.')
    hierarchy_name = server_json['roles'][str(Tier.id)]

    if hierarchy_name in server_json['hierarchies']:
        old_hierarchy = server_json['hierarchies'][hierarchy_name]['tiers']
        new_hierarchy = []
        role_removed = False

        tier_to_remove = None
        for tier in old_hierarchy:
            if 'role_id' in tier and tier['role_id'] == Tier.id:
                tier_to_remove = tier
                if 'parent_role_id' in tier_to_remove and tier_to_remove['parent_role_id'] == 0:
                    unlock_server_file(server_id)
                    return await ctx.send('Cannot delete root tier for hierarchy ' + hierarchy_name + '. Delete and recreate the hierarchy.')

        if tier_to_remove is None:
            unlock_server_file(server_id)
            return await ctx.send('Could not find role <@&' + str(Tier.id) + '> ' + hierarchy_name + '.')

        for tier in old_hierarchy:
            if 'role_id' in tier and tier['role_id'] == Tier.id:
                del server_json['roles'][str(Tier.id)]
                role_removed = True
            elif 'parent_role_id' in tier and tier['parent_role_id'] == Tier.id:
                tier['parent_role_id'] = tier_to_remove['parent_role_id']
                new_hierarchy.append(tier)
            else:
                new_hierarchy.append(tier)

        if role_removed:
            new_hierarchy = recursive_hierarchy_update(new_hierarchy, 0, 0)
            server_json['hierarchies'][hierarchy_name]['tiers'] = new_hierarchy
            save_server_file(server_id, server_json)
            unlock_server_file(server_id)
            return await ctx.send('Role <@&' + str(Tier.id) + '> successfully removed for hierarchy ' + hierarchy_name + '.')
        else:
            unlock_server_file(server_id)
            return await ctx.send('Could not remove role <@&' + str(Tier.id) + '> from hierarchy. This should never occur.')
    else:
        unlock_server_file(server_id)
        return await ctx.send('hierarchy_name ' + hierarchy_name + ' does not exist.')

@bot.command()
async def promote(ctx: discord.ext.commands.Context, Member: discord.Member, Tier: discord.Role):
    await logger(ctx, f'{ctx.author.name} <@{ctx.author.id}> promoting {Member.name} <@{Member.id}> to {Tier.name} <@&{Tier.id}>.')

    server_id = ctx.message.guild.id
    server_json = get_server_json(server_id)

    if str(Tier.id) not in server_json['roles']:
        return await ctx.send('Role <@&' + str(Tier.id) + '> does not belong to a hierarchy.')
    hierarchy_name = server_json['roles'][str(Tier.id)]
    hierarchy = server_json['hierarchies'][hierarchy_name]['tiers']

    author_tiers = []
    target_tiers = []
    tier_to_promote_to = None
    for tier_object in hierarchy:
        role = discord.utils.get(ctx.guild.roles, id=tier_object['role_id'])
        parent_role = discord.utils.get(ctx.guild.roles, id=tier_object['parent_role_id'])
        tier_object['role'] = role
        tier_object['parent_role'] = parent_role

        if role in ctx.author.roles and \
                tier_object['promotion_min_depth'] != -1 and \
                tier_object['promotion_max_depth'] != -1:
            author_tiers.append(tier_object)
        if role in Member.roles:
            target_tiers.append(tier_object)
        if role.id == Tier.id:
            tier_to_promote_to = tier_object

    if len(author_tiers) == 0:
        return await ctx.send('You have no roles in hierarchy ' + hierarchy_name + '. You cannot promote or demote.')

    if tier_to_promote_to is None:
        return await ctx.send('Hierarchy ' + hierarchy_name + ' is corrupted. Role exists in role lookup but not in hierarchy tree. You should never see this error.')

    tier_to_promote_from = None
    for tier_object in target_tiers:
        # Try to locate the role that we are going to remove before promoting
        if tier_object['parent_role_id'] == Tier.id:
            if tier_to_promote_from is None:
                # If the role was found and it is the only role, assign it
                tier_to_promote_from = tier_object
            else:
                # If multiple roles share this parent
                return await ctx.send('This member has 2 or more child roles in hierarchy ' + hierarchy_name +
                                      '. You cannot promote a user who has two tiers at the same level.')

    if tier_to_promote_from is None and int(tier_to_promote_to["depth"]) != int(server_json["hierarchies"][hierarchy_name]["maximum_depth"]):
        return await ctx.send(f'Cannot promote to <@&{tier_to_promote_to["role_id"]}> because <@{Member.id}> does not have its child role.')

    # Iterate over author's tiers looking for role that can promote
    for tier_object in author_tiers:
        print(f'Calculating depth {tier_to_promote_to["depth"]} - {tier_object["depth"]}')
        calculated_depth = tier_to_promote_to['depth'] - tier_object['depth']
        if tier_object['promotion_min_depth'] <= calculated_depth <= tier_object['promotion_max_depth']:
            if tier_to_promote_from is not None:
                await Member.remove_roles(tier_to_promote_from['role'])
            await Member.add_roles(tier_to_promote_to['role'])
            return await ctx.send(f"Promoted {Member.mention} to {Tier.mention}.")
        else:
            # Might send multiple times for multiple roles
            await ctx.send(f'Your role <@&{tier_object["role_id"]}> can only promote between {tier_object["promotion_min_depth"]} and {tier_object["promotion_max_depth"]} roles down, inclusively.')
    return

@bot.command()
async def demote(ctx: discord.ext.commands.Context, Member: discord.Member, Tier: discord.Role):
    await logger(ctx, f'{ctx.author.name} <@{ctx.author.id}> demoting {Member.name} <@{Member.id}> to {Tier.name} <@&{Tier.id}>.')

    server_id = ctx.message.guild.id
    server_json = get_server_json(server_id)

    if str(Tier.id) not in server_json['roles']:
        return await ctx.send('Role <@&' + str(Tier.id) + '> does not belong to a hierarchy.')
    hierarchy_name = server_json['roles'][str(Tier.id)]
    hierarchy = server_json['hierarchies'][hierarchy_name]['tiers']

    author_tiers = []
    target_tiers = []
    tier_to_demote_to = None
    for tier_object in hierarchy:
        role = discord.utils.get(ctx.guild.roles, id=tier_object['role_id'])
        parent_role = discord.utils.get(ctx.guild.roles, id=tier_object['parent_role_id'])
        tier_object['role'] = role
        tier_object['parent_role'] = parent_role

        if role in ctx.author.roles and \
                tier_object['demotion_min_depth'] != -1 and \
                tier_object['demotion_max_depth'] != -1:
            author_tiers.append(tier_object)
        if role in Member.roles:
            target_tiers.append(tier_object)
        if role.id == Tier.id:
            tier_to_demote_to = tier_object

    if len(author_tiers) == 0:
        return await ctx.send('You have no roles in hierarchy ' + hierarchy_name + '. You cannot promote or demote.')

    if tier_to_demote_to is None:
        return await ctx.send('Hierarchy ' + hierarchy_name + ' is corrupted. Role exists in role lookup but not in hierarchy tree. You should never see this error.')

    tier_to_demote_from = None
    for tier_object in target_tiers:
        # Try to locate the role that we are going to remove before demoting
        print(f'{tier_object["role_id"]}  == {tier_to_demote_to["parent_role_id"]}')
        if tier_object['role_id'] == tier_to_demote_to['parent_role_id']:
            if tier_to_demote_from is None:
                # If the role was found and it is the only role, assign it
                tier_to_demote_from = tier_object
            else:
                # If multiple roles share this parent
                return await ctx.send('This member has 2 or more child roles in hierarchy ' + hierarchy_name +
                                      '. You cannot demote a user who has two tiers at the same level.')

    if tier_to_demote_from is None:
        return await ctx.send('You cannot demote a user at the lowest level of the hierarchy. Use unassign for this instead.')

    # Iterate over author's tiers looking for role that can demote
    for tier_object in author_tiers:
        print(f'Calculating depth {tier_to_demote_to["depth"]} - {tier_object["depth"]}')
        calculated_depth = tier_to_demote_to['depth'] - tier_object['depth']
        if tier_object['demotion_min_depth'] <= calculated_depth <= tier_object['demotion_max_depth']:
            #if tier_to_demote_from is not None:
            await Member.remove_roles(tier_to_demote_from['role'])
            await Member.add_roles(tier_to_demote_to['role'])
            return await ctx.send(f"Demoted {Member.mention} to {Tier.mention}.")
        else:
            # Might send multiple times for multiple roles
            await ctx.send(f'Your role <@&{tier_object["role_id"]}> can only demote between {tier_object["demotion_min_depth"]} and {tier_object["demotion_max_depth"]} roles down, inclusively.')
    return

bot.run(token)
