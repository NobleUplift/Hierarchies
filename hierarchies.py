import sys, traceback
import discord
from discord.ext import commands
import os.path
from os import path
from pathlib import Path
import json
from discord_token import token
from typing import Union

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

async def logger(ctx, message: str):
    print(message)
    server_id = ctx.message.guild.id
    server_json = get_server_json(server_id)

    if 'log_channel' not in server_json:
        raise Exception('Must use `setlogger` to set log channel.')

    channel = bot.get_channel(server_json['log_channel'])
    if channel is None:
        raise Exception('No logging channel set.')
    return await channel.send(message)

class NoManageRoles(commands.CheckFailure):
    pass

def has_manage_roles():
    async def predicate(ctx):
        if ctx.author and ctx.author.guild_permissions.manage_roles is True:
            return True
        else:
            raise NoManageRoles('You must have the Manage Roles permission to create, delete, and modify hierarchies.')
    return commands.check(predicate)

class BotManagement(commands.Cog):
    """Commands for managing the Hierarchies bot."""

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
        return await ctx.send(f'Set logger to <#{channel.mention}.')

    @commands.command(pass_context=True)
    @has_manage_roles()
    async def unlock(self, ctx: discord.ext.commands.Context):
        """Unlocks the mutex file if the bot crashes during a Hierarchies command."""

        server_id = ctx.message.guild.id
        if path.isfile(str(server_id) + '.lck'):
            unlock_server_file(server_id)
            await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) successfully ran `unlock`.')
            return await ctx.send('Server file unlocked.')
        else:
            await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) unsuccessfully ran `unlock`.')
            return await ctx.send('Server file was not locked.')

class HierarchyManagement(commands.Cog):
    """Commands for managing creating, modifying, and deleting hierarchies."""

    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @commands.command(pass_context=True)
    @has_manage_roles()
    async def list(self, ctx: discord.ext.commands.Context):
        """Lists all Hierarchies."""

        server_id = ctx.message.guild.id
        server_json = get_server_json(server_id)

        if len(server_json['hierarchies']) == 0:
            return await ctx.send('This server has no hierarchies.')

        server_hierarchies = server_json['hierarchies']
        retval = 'Hierarchies: \n'
        for n in server_hierarchies:
            retval += ' • ' + n + "\n"
        # No need to log read-only commands
        print(f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) listed hierarchies.')
        return await ctx.send(retval)

    @commands.command()
    @has_manage_roles()
    async def show(self, ctx: discord.ext.commands.Context, HierarchyName: str):
        """Shows all the roles in a single Hierarchy."""

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
            role = discord.utils.get(ctx.guild.roles, id=tier['role_id'])
            role_id = None
            if role is not None:
                role_id = str(role.id)
            else:
                role_id = '!' + str(tier['role_id'])
            nextline = spaces + '<@&' + role_id + '> '
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
        # No need to log read-only commands
        print(f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) showed hierarchy `{HierarchyName}`.')
        return await ctx.send(retval)

    @commands.command(pass_context=True)
    @has_manage_roles()
    async def create(self, ctx: discord.ext.commands.Context, HierarchyName: str, RootTier: discord.Role):
        """Creates a new Hierarchy."""

        if ' ' in HierarchyName:
            await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) tried to create a hierarchy `{HierarchyName}` with spaces in it.')
            return await ctx.send('Hierarchies name "' + HierarchyName + '" cannot have spaces in it.')

        server_id = ctx.message.guild.id
        lock_server_file(server_id)
        server_json = get_server_json(server_id)
        server_json_hierarchies = server_json['hierarchies']

        if HierarchyName in server_json_hierarchies:
            unlock_server_file(server_id)
            await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) tried to create a hierarchy `{HierarchyName}` that already exists.')
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

        await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) created hierarchy `{HierarchyName}` with root tier {RootTier.mention}.')
        return await ctx.send('Created hierarchy ' + HierarchyName + '.')

    @commands.command(pass_context=True)
    @has_manage_roles()
    async def delete(self, ctx: discord.ext.commands.Context, HierarchyName: str):
        """Deletes an existing Hierarchy."""

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
            await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) successfully deleted hierarchy `{HierarchyName}`.')
            return await ctx.send('Deleted hierarchy ' + HierarchyName + '.')
        else:
            unlock_server_file(server_id)
            await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) tried to delete hierarchy `{HierarchyName}` that does not exist.')
            return await ctx.send('Hierarchy  does not exist.')

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

    def recursive_hierarchy_update(self, old_hierarchy, role_id, depth):
        #print('Calling recursive_hierarchy_update at depth ' + str(depth))
        new_hierarchy = []
        for tier in old_hierarchy:
            #print('Does ' + str(tier['parent_role_id']) + ' equal ' + str(role_id) + '?')
            if 'parent_role_id' in tier and tier['parent_role_id'] == role_id:
                tier['depth'] = depth
                new_hierarchy.append(tier)
                new_hierarchy = new_hierarchy + self.recursive_hierarchy_update(old_hierarchy, tier['role_id'], depth + 1)
        #print(new_hierarchy)
        return new_hierarchy

    @commands.command(pass_context=True)
    @has_manage_roles()
    async def add(self, ctx: discord.ext.commands.Context, Tier: discord.Role, Parent: discord.Role,
            PromotionMinimumDepth: int = -1,
            PromotionMaximumDepth: int = -1,
            DemotionMinimumDepth: int = -1,
            DemotionMaximumDepth: int = -1
        ):
        """Adds a role to a Hierarchy."""

        server_id = ctx.message.guild.id
        lock_server_file(server_id)
        server_json = get_server_json(server_id)

        if str(Tier.id) in server_json['roles']:
            unlock_server_file(server_id)
            await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) tried to add {Tier.mention}, parent role {Parent.mention}, but the role already exists in a hierarchy.')
            return await ctx.send(f'Role already exists in hierarchy `{server_json["roles"][str(Tier.id)]}`.')

        if str(Parent.id) not in server_json['roles']:
            unlock_server_file(server_id)
            await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) tried to add {Tier.mention}, parent role {Parent.mention}, but the parent role does not exist in a hierarchy.')
            return await ctx.send(f'Parent role {Parent.mention} does not exist in a hierarchy.')
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
                new_hierarchy = self.recursive_hierarchy_update(hierarchy, 0, 0)
                server_json['hierarchies'][hierarchy_name]['tiers'] = new_hierarchy
                server_json['hierarchies'][hierarchy_name]['maximum_depth'] = 0
                for tier in server_json['hierarchies'][hierarchy_name]['tiers']:
                    if tier['depth'] > server_json['hierarchies'][hierarchy_name]['maximum_depth']:
                        server_json['hierarchies'][hierarchy_name]['maximum_depth'] = tier['depth']
                save_server_file(server_id, server_json)
                unlock_server_file(server_id)
                await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) added {Tier.mention}, parameters {Parent.mention} {PromotionMinimumDepth} {PromotionMaximumDepth} {DemotionMinimumDepth} {DemotionMaximumDepth}, to hierarchy `{hierarchy_name}`.')
                return await ctx.send(f'Successfully added {Tier.mention}, parent role {Parent.mention}, to hierarchy `{hierarchy_name}`.')
            else:
                unlock_server_file(server_id)
                await logger(ctx, f'**SERVER CORRUPTION!** {ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) tried to add {Tier.mention}, but parent role {Parent.mention} does not exist in hierarchy `{hierarchy_name}`.')
                return await ctx.send(f'**SERVER CORRUPTION!** Parent role {Parent.mention} exists in the server role lookup, but does not exist in hierarchy `{hierarchy_name}`! Please contact the developer.')
        else:
            unlock_server_file(server_id)
            await logger(ctx, f'**SERVER CORRUPTION!** {ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) tried to add {Tier.mention}, parent role {Parent.mention}, but parent role hierarchy `{hierarchy_name}` no longer exists.')
            return await ctx.send(f'**SERVER CORRUPTION!** Parent role {Parent.mention} exists in the server role lookup, but hierarchy `{hierarchy_name}` no longer exists! Please contact the developer.')

    @commands.command(pass_context=True)
    @has_manage_roles()
    async def modify(self, ctx: discord.ext.commands.Context, Tier: discord.Role, Parent: discord.Role,
            PromotionMinimumDepth: int = -1,
            PromotionMaximumDepth: int = -1,
            DemotionMinimumDepth: int = -1,
            DemotionMaximumDepth: int = -1
        ):
        """Modifies a role within a hierarchy."""

        server_id = ctx.message.guild.id
        lock_server_file(server_id)
        server_json = get_server_json(server_id)

        if str(Tier.id) not in server_json['roles']:
            unlock_server_file(server_id)
            await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) tried to modify {Tier.mention}, but the role does not exist in a hierarchy.')
            return await ctx.send(f'Role {Tier.mention} does not exist in a hierarchy.')
        hierarchy_name = server_json['roles'][str(Tier.id)]

        if str(Parent.id) not in server_json['roles']:
            unlock_server_file(server_id)
            await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) cannot change {Tier.mention} to parent role {Parent.mention} because parent role does not exist in a hierarchy.')
            return await ctx.send(f'Cannot change {Tier.mention} to parent role {Parent.mention} because parent role does not exist in a hierarchy.')
        parent_hierarchy_name = server_json['roles'][str(Parent.id)]

        if hierarchy_name != parent_hierarchy_name:
            unlock_server_file(server_id)
            await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) cannot change {Tier.mention} to parent role {Parent.mention} because parent role does not exist in hierarchy {hierarchy_name}.')
            return await ctx.send(f'Cannot change {Tier.mention} to parent role {Parent.mention} when parent role does not exist in hierarchy {hierarchy_name}.')

        if hierarchy_name in server_json['hierarchies']:
            role_modified = False
            hierarchy = server_json['hierarchies'][hierarchy_name]['tiers']

            """new_tier = {
                'role_id': Tier.id,
                'parent_role_id': Parent.id if Parent is not None else 0,
                'depth': 0,
                'promotion_min_depth': PromotionMinimumDepth,
                'promotion_max_depth': PromotionMaximumDepth,
                'demotion_min_depth': DemotionMinimumDepth,
                'demotion_max_depth': DemotionMaximumDepth
            }"""

            for tier in hierarchy:
                if 'role_id' in tier and tier['role_id'] == Tier.id:
                    tier['parent_role_id'] = Parent.id
                    tier['promotion_min_depth'] = PromotionMinimumDepth
                    tier['promotion_max_depth'] = PromotionMaximumDepth
                    tier['demotion_min_depth'] = DemotionMinimumDepth
                    tier['demotion_max_depth'] = DemotionMaximumDepth
                    role_modified = True

            if role_modified:
                new_hierarchy = self.recursive_hierarchy_update(hierarchy, 0, 0)
                server_json['hierarchies'][hierarchy_name]['tiers'] = new_hierarchy
                server_json['hierarchies'][hierarchy_name]['maximum_depth'] = 0
                for tier in server_json['hierarchies'][hierarchy_name]['tiers']:
                    if tier['depth'] > server_json['hierarchies'][hierarchy_name]['maximum_depth']:
                        server_json['hierarchies'][hierarchy_name]['maximum_depth'] = tier['depth']
                save_server_file(server_id, server_json)
                unlock_server_file(server_id)
                await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) modified {Tier.mention}, parameters {Parent.mention} {PromotionMinimumDepth} {PromotionMaximumDepth} {DemotionMinimumDepth} {DemotionMaximumDepth}, in hierarchy `{hierarchy_name}`.')
                return await ctx.send(f'Successfully modified {Tier.mention} in hierarchy `{hierarchy_name}`.')
            else:
                await logger(ctx, f'**SERVER CORRUPTION!** {ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) tried to modify {Tier.mention}, parameters {Parent.mention} {PromotionMinimumDepth} {PromotionMaximumDepth} {DemotionMinimumDepth} {DemotionMaximumDepth}, but role {Tier.mention} does not exist in hierarchy `{hierarchy_name}`.')
                return await ctx.send(f'**SERVER CORRUPTION!** Role {Tier.mention} exists in the server role lookup, but does not exist in hierarchy `{hierarchy_name}`! Please contact the developer.')
        else:
            await logger(ctx, f'**SERVER CORRUPTION!** {ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) tried to modify {Tier.mention}, parameters {Parent.mention} {PromotionMinimumDepth} {PromotionMaximumDepth} {DemotionMinimumDepth} {DemotionMaximumDepth}, but role hierarchy `{hierarchy_name}` no longer exists.')
            return await ctx.send(f'**SERVER CORRUPTION!** Role {Tier.mention} exists in the server role lookup, but hierarchy `{hierarchy_name}` no longer exists! Please contact the developer.')

    @commands.command(pass_context=True)
    @has_manage_roles()
    async def remove(self, ctx: discord.ext.commands.Context, Tier: Union[discord.Role, int]):
        """Removes a role from a hierarchy, linking all former child roles to its parent role. The root role cannot be deleted."""

        server_id = ctx.message.guild.id
        lock_server_file(server_id)
        server_json = get_server_json(server_id)
        role_id = None
        role_mention = None

        if isinstance(Tier, discord.Role):
            role_id = Tier.id
            role_mention = Tier.mention
        else:
            role_id = Tier
            role_mention = f'<@&!{role_id}>'

        if str(role_id) not in server_json['roles']:
            unlock_server_file(server_id)
            await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) attempted to remove {role_mention} when it does not belong to a hierarchy.')
            return await ctx.send(f'Role {role_mention} does not belong to a hierarchy.')
        hierarchy_name = server_json['roles'][str(role_id)]

        if hierarchy_name in server_json['hierarchies']:
            old_hierarchy = server_json['hierarchies'][hierarchy_name]['tiers']
            new_hierarchy = []
            role_removed = False

            #
            # Find tier to remove in hierarchy. If trying to remove the root node, reject this command
            #
            tier_to_remove = None
            for tier in old_hierarchy:
                if 'role_id' in tier and tier['role_id'] == role_id:
                    tier_to_remove = tier
                    if 'parent_role_id' in tier_to_remove and tier_to_remove['parent_role_id'] == 0:
                        unlock_server_file(server_id)
                        await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) attempted to remove the root role {role_mention} from hierarchy `{hierarchy_name}`.')
                        return await ctx.send(f'Cannot delete root tier for hierarchy {hierarchy_name}. Delete and recreate the hierarchy.')

            if tier_to_remove is None:
                unlock_server_file(server_id)
                await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) attempted to remove {role_mention} from hierarchy `{hierarchy_name}` where it does not exist.')
                return await ctx.send(f'Role {role_mention} does not exist in hierarchy `{hierarchy_name}`.')

            for tier in old_hierarchy:
                if 'role_id' in tier and tier['role_id'] == role_id:
                    del server_json['roles'][str(role_id)]
                    role_removed = True
                elif 'parent_role_id' in tier and tier['parent_role_id'] == role_id:
                    tier['parent_role_id'] = tier_to_remove['parent_role_id']
                    new_hierarchy.append(tier)
                else:
                    new_hierarchy.append(tier)

            if role_removed:
                new_hierarchy = self.recursive_hierarchy_update(new_hierarchy, 0, 0)
                server_json['hierarchies'][hierarchy_name]['tiers'] = new_hierarchy
                save_server_file(server_id, server_json)
                unlock_server_file(server_id)
                await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) removed {role_mention} from hierarchy `{hierarchy_name}`.')
                return await ctx.send(f'Successfully removed {role_mention} from hierarchy `{hierarchy_name}`.')
            else:
                unlock_server_file(server_id)
                await logger(ctx, f'**SERVER CORRUPTION!** {ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) tried to remove {role_mention} but it does not exist in hierarchy `{hierarchy_name}`.')
                return await ctx.send(f'**SERVER CORRUPTION!** Role {role_mention} exists in the server role lookup, but does not exist in hierarchy `{hierarchy_name}`! Please contact the developer.')
        else:
            unlock_server_file(server_id)
            await logger(ctx, f'**SERVER CORRUPTION!** {ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) tried to remove {role_mention} but role hierarchy `{hierarchy_name}` no longer exists.')
            return await ctx.send(f'**SERVER CORRUPTION!** Role {role_mention} exists in the server role lookup, but hierarchy `{hierarchy_name}` no longer exists! Please contact the developer.')


class PlayerManagement(commands.Cog):
    """Commands for managing player roles."""

    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @commands.command(pass_context=True)
    async def promote(self, ctx: discord.ext.commands.Context, Member: discord.Member, Tier: discord.Role):
        """Remove a role from a user and give that user the next highest role in the hierarchy."""

        server_id = ctx.message.guild.id
        server_json = get_server_json(server_id)

        if str(Tier.id) not in server_json['roles']:
            await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not promote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because role {Tier.mention} does not belong to a hierarchy.')
            return await ctx.send(f'Role {Tier.mention} does not belong to a hierarchy.')
        hierarchy_name = server_json['roles'][str(Tier.id)]
        hierarchy = server_json['hierarchies'][hierarchy_name]['tiers']

        author_tiers = []
        target_tiers = []
        tier_to_promote_to = None
        # Get Discord roles for every role ID and parent role ID in the hierarchy
        # Store them in the hierarchy because this is a temporary object
        # that will not be saved to file
        for tier_object in hierarchy:
            role = discord.utils.get(ctx.guild.roles, id=tier_object['role_id'])
            if role is None:
                await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not promote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because a deleted role {tier_object["role_id"]} still exists in the hierarchy.')
                return await ctx.send(f'Role {tier_object["role_id"]} was deleted but still exists in the hierarchy.')
            parent_role = discord.utils.get(ctx.guild.roles, id=tier_object['parent_role_id'])
            if int(tier_object['parent_role_id']) is not 0 and parent_role is None:
                await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not promote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because a deleted parent role {tier_object["parent_role_id"]} still exists in the hierarchy.')
                return await ctx.send(f'Parent role {tier_object["parent_role_id"]} was deleted but still exists in the hierarchy.')
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
            await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not promote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because he/she has no roles in hierarchy {hierarchy_name} that are capable of promoting.')
            return await ctx.send(f'You have no roles in hierarchy {hierarchy_name} that are capable of promoting. You cannot promote members.')

        if tier_to_promote_to is None:
            await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not promote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because role exists in role lookup but not in hierarchy tree.')
            return await ctx.send(f'Hierarchy {hierarchy_name} is corrupted. Role exists in role lookup but not in hierarchy tree. You should never see this error.')

        tier_to_promote_from = None
        for tier_object in target_tiers:
            # Try to locate the role that we are going to remove before promoting
            if tier_object['parent_role_id'] == Tier.id:
                if tier_to_promote_from is None:
                    # If the role was found and it is the only role, assign it
                    tier_to_promote_from = tier_object
                else:
                    # If multiple roles share this parent
                    await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not promote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because this member has 2 or more child roles in hierarchy {hierarchy_name}.')
                    return await ctx.send(f'This member has 2 or more child roles in hierarchy {hierarchy_name}. You cannot promote a user who has two tiers at the same level.')

        # Enforce tier_to_promote_from as a requirement when promoting. Only allow ^assign for lowest role
        # TODO: Remove maximum_depth, no longer useful
        if tier_to_promote_from is None: # and int(tier_to_promote_to["depth"]) != int(server_json["hierarchies"][hierarchy_name]["maximum_depth"])
            await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not promote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because {Member.mention} does not have its child role.')
            return await ctx.send(f'Cannot promote to <@&{tier_to_promote_to["role_id"]}> because {Member.mention} does not have its child role.')

        # Iterate over author's tiers looking for role that can promote
        for tier_object in author_tiers:
            print(f'Calculating depth {tier_to_promote_to["depth"]} - {tier_object["depth"]}')
            calculated_depth = tier_to_promote_to['depth'] - tier_object['depth']
            if tier_object['promotion_min_depth'] <= calculated_depth <= tier_object['promotion_max_depth']:
                if tier_to_promote_from is not None:
                    await Member.remove_roles(tier_to_promote_from['role'])
                await Member.add_roles(tier_to_promote_to['role'])
                await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) promoted {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention}.')
                return await ctx.send(f"Promoted {Member.mention} to {Tier.mention}.")
            else:
                # Might send multiple times for multiple roles
                await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not promote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because role <@&{tier_object["role_id"]}> can only promote between {tier_object["promotion_min_depth"]} and {tier_object["promotion_max_depth"]} roles down, inclusively.')
                await ctx.send(f'Your role <@&{tier_object["role_id"]}> can only promote between {tier_object["promotion_min_depth"]} and {tier_object["promotion_max_depth"]} roles down, inclusively.')
        return

    @commands.command(pass_context=True)
    async def assign(self, ctx: discord.ext.commands.Context, Member: discord.Member, Tier: discord.Role):
        """Assign a role to a user in the hierarchy. This should only be used for roles that cannot be promoted or demoted."""

        server_id = ctx.message.guild.id
        server_json = get_server_json(server_id)

        if str(Tier.id) not in server_json['roles']:
            await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not assign {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because role {Tier.mention} does not belong to a hierarchy.')
            return await ctx.send(f'Role {Tier.mention} does not belong to a hierarchy.')
        hierarchy_name = server_json['roles'][str(Tier.id)]
        hierarchy = server_json['hierarchies'][hierarchy_name]['tiers']

        author_tiers = []
        target_tiers = []
        # Get Discord roles for every role ID and parent role ID in the hierarchy
        # Store them in the hierarchy because this is a temporary object
        # that will not be saved to file
        for tier_object in hierarchy:
            role = discord.utils.get(ctx.guild.roles, id=tier_object['role_id'])
            if role is None:
                await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not promote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because a deleted role {tier_object["role_id"]} still exists in the hierarchy.')
                return await ctx.send(f'Role {tier_object["role_id"]} was deleted but still exists in the hierarchy.')
            parent_role = discord.utils.get(ctx.guild.roles, id=tier_object['parent_role_id'])
            if int(tier_object['parent_role_id']) is not 0 and parent_role is None:
                await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not promote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because a deleted parent role {tier_object["parent_role_id"]} still exists in the hierarchy.')
                return await ctx.send(f'Parent role {tier_object["parent_role_id"]} was deleted but still exists in the hierarchy.')
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
            await logger(ctx,f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not assign {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because he/she has no roles in hierarchy {hierarchy_name} that are capable of assigning.')
            return await ctx.send(f'You have no roles in hierarchy {hierarchy_name} that are capable of promoting. You cannot promote members.')

        if tier_to_promote_to is None:
            await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not assign {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because role exists in role lookup but not in hierarchy tree.')
            return await ctx.send(f'Hierarchy {hierarchy_name} is corrupted. Role exists in role lookup but not in hierarchy tree. You should never see this error.')

        # Iterate over author's tiers looking for role that can promote
        for tier_object in author_tiers:
            print(f'Calculating depth {tier_to_promote_to["depth"]} - {tier_object["depth"]}')
            calculated_depth = tier_to_promote_to['depth'] - tier_object['depth']
            if tier_object['promotion_min_depth'] <= calculated_depth <= tier_object['promotion_max_depth']:
                await Member.add_roles(tier_to_promote_to['role'])
                await logger(ctx, f'{ctx.author.name} {ctx.author.mention} assigned {Member.name} {Member.mention} to role {Tier.name} {Tier.mention}.')
                return await ctx.send(f"Assigned {Tier.mention} to {Member.mention}.")
            else:
                # Might send multiple times for multiple roles
                await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not assign {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because role <@&{tier_object["role_id"]}> can only promote between {tier_object["promotion_min_depth"]} and {tier_object["promotion_max_depth"]} roles down, inclusively.')
                await ctx.send( f'Your role <@&{tier_object["role_id"]}> can only assign between {tier_object["promotion_min_depth"]} and {tier_object["promotion_max_depth"]} roles down, inclusively.')
        return

    @commands.command(pass_context=True)
    async def demote(self, ctx: discord.ext.commands.Context, Member: discord.Member, Tier: discord.Role):
        """Remove a role from the user and give that user the next lowest role in the hierarchy."""

        server_id = ctx.message.guild.id
        server_json = get_server_json(server_id)

        if str(Tier.id) not in server_json['roles']:
            await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not demote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because role {Tier.mention} does not belong to a hierarchy.')
            return await ctx.send(f'Role {Tier.mention} does not belong to a hierarchy.')
        hierarchy_name = server_json['roles'][str(Tier.id)]
        hierarchy = server_json['hierarchies'][hierarchy_name]['tiers']

        author_tiers = []
        target_tiers = []
        tier_to_demote_to = None
        # Get Discord roles for every role ID and parent role ID in the hierarchy
        # Store them in the hierarchy because this is a temporary object
        # that will not be saved to file
        for tier_object in hierarchy:
            role = discord.utils.get(ctx.guild.roles, id=tier_object['role_id'])
            if role is None:
                await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not promote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because a deleted role {tier_object["role_id"]} still exists in the hierarchy.')
                return await ctx.send(f'Role {tier_object["role_id"]} was deleted but still exists in the hierarchy.')
            parent_role = discord.utils.get(ctx.guild.roles, id=tier_object['parent_role_id'])
            if int(tier_object['parent_role_id']) is not 0 and parent_role is None:
                await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not promote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because a deleted parent role {tier_object["parent_role_id"]} still exists in the hierarchy.')
                return await ctx.send(f'Parent role {tier_object["parent_role_id"]} was deleted but still exists in the hierarchy.')
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
            await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not demote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because he/she has no roles in hierarchy {hierarchy_name} that are capable of demoting.')
            return await ctx.send(f'You have no roles in hierarchy {hierarchy_name} that are capable of demoting. You cannot demote members.')

        if tier_to_demote_to is None:
            await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not demote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because role exists in role lookup but not in hierarchy tree.')
            return await ctx.send(f'Hierarchy {hierarchy_name} is corrupted. Role exists in role lookup but not in hierarchy tree. You should never see this error.')

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
                    await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not demote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because this member has 2 or more child roles in hierarchy {hierarchy_name}.')
                    return await ctx.send(f'This member has 2 or more child roles in hierarchy {hierarchy_name}. You cannot demote a user who has two tiers at the same level.')

        if tier_to_demote_from is None:
            await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not promote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because {Member.mention} does not have its child role.')
            return await ctx.send(f'You cannot demote a user at the lowest level of the hierarchy. Use unassign for this instead.')

        # Iterate over author's tiers looking for role that can demote
        for tier_object in author_tiers:
            print(f'Calculating depth {tier_to_demote_to["depth"]} - {tier_object["depth"]}')
            calculated_depth = tier_to_demote_to['depth'] - tier_object['depth']
            if tier_object['demotion_min_depth'] <= calculated_depth <= tier_object['demotion_max_depth']:
                #if tier_to_demote_from is not None:
                await Member.remove_roles(tier_to_demote_from['role'])
                await Member.add_roles(tier_to_demote_to['role'])
                await logger(ctx, f'{ctx.author.name} {ctx.author.mention} demoted {Member.name} {Member.mention} to {Tier.name} {Tier.mention}.')
                return await ctx.send(f"Demoted {Member.mention} to {Tier.mention}.")
            else:
                # Might send multiple times for multiple roles
                await logger(ctx,f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not demote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because role <@&{tier_object["role_id"]}> can only demote between {tier_object["demotion_min_depth"]} and {tier_object["demotion_max_depth"]} roles down, inclusively.')
                await ctx.send(f'Your role <@&{tier_object["role_id"]}> can only demote between {tier_object["demotion_min_depth"]} and {tier_object["demotion_max_depth"]} roles down, inclusively.')
        return

    @commands.command(pass_context=True)
    async def unassign(self, ctx: discord.ext.commands.Context, Member: discord.Member, Tier: discord.Role):
        """Unassign a role from a user in the hierarchy. This should only be used for roles that cannot be promoted or demoted."""

        server_id = ctx.message.guild.id
        server_json = get_server_json(server_id)

        if str(Tier.id) not in server_json['roles']:
            await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not demote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because role {Tier.mention} does not belong to a hierarchy.')
            return await ctx.send(f'Role {Tier.mention} does not belong to a hierarchy.')
        hierarchy_name = server_json['roles'][str(Tier.id)]
        hierarchy = server_json['hierarchies'][hierarchy_name]['tiers']

        author_tiers = []
        target_tiers = []
        # Get Discord roles for every role ID and parent role ID in the hierarchy
        # Store them in the hierarchy because this is a temporary object
        # that will not be saved to file
        for tier_object in hierarchy:
            role = discord.utils.get(ctx.guild.roles, id=tier_object['role_id'])
            if role is None:
                await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not promote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because a deleted role {tier_object["role_id"]} still exists in the hierarchy.')
                return await ctx.send(f'Role {tier_object["role_id"]} was deleted but still exists in the hierarchy.')
            parent_role = discord.utils.get(ctx.guild.roles, id=tier_object['parent_role_id'])
            if int(tier_object['parent_role_id']) is not 0 and parent_role is None:
                await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not promote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because a deleted parent role {tier_object["parent_role_id"]} still exists in the hierarchy.')
                return await ctx.send(f'Parent role {tier_object["parent_role_id"]} was deleted but still exists in the hierarchy.')
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
            await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not unassign {Member.mention} ({Member.name}#{Member.discriminator}) from {Tier.mention} because he/she has no roles in hierarchy {hierarchy_name} that are capable of unassigning.')
            return await ctx.send(f'You have no roles in hierarchy {hierarchy_name} that are capable of unassigning. You cannot unassigning members.')

        # Iterate over author's tiers looking for role that can demote
        for tier_object in author_tiers:
            print(f'Calculating depth {tier_to_demote_to["depth"]} - {tier_object["depth"]}')
            calculated_depth = tier_to_demote_to['depth'] - tier_object['depth']
            if tier_object['demotion_min_depth'] <= calculated_depth <= tier_object['demotion_max_depth']:
                # if tier_to_demote_from is not None:
                await Member.remove_roles(Tier)
                await logger(ctx, f'{ctx.author.name} {ctx.author.mention} unassignmed {Member.name} {Member.mention} from role {Tier.name} {Tier.mention}.')
                return await ctx.send(f"Unassigned {Tier.mention} from {Member.mention}.")
            else:
                # Might send multiple times for multiple roles
                await logger(ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not unassign {Member.mention} ({Member.name}#{Member.discriminator}) from {Tier.mention} because role <@&{tier_object["role_id"]}> can only demote between {tier_object["demotion_min_depth"]} and {tier_object["demotion_max_depth"]} roles down, inclusively.')
                await ctx.send( f'Your role <@&{tier_object["role_id"]}> can only unassign between {tier_object["demotion_min_depth"]} and {tier_object["demotion_max_depth"]} roles down, inclusively.')
        return

description = '''
Replacement for the "Manage Roles" permission that allows for multiple hierarchies to be defined in Discord roles.
'''
bot = commands.Bot(command_prefix='^', description=description)

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
    print("ERROR TRIGGERED! CAUGHT BY ON_COMMAND_ERROR")
    print(ctx)
    print(error)

    # This prevents any commands with local handlers being handled here in on_command_error.
    if hasattr(ctx.command, 'on_error'):
        print("Error has on_error attribute, do not process error.")
        return

    # This prevents any cogs with an overwritten cog_command_error being handled here.
    cog = ctx.cog
    if cog:
        if cog._get_overridden_method(cog.cog_command_error) is not None:
            print("Cog has cog_command_error, allow cog to process this error.")
            return

    ignored = (commands.CommandNotFound) # 

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
        if ctx.command.qualified_name == 'tag list':  # Check if the command being invoked is 'tag list'
            await ctx.send('I could not find that member. Please try again.')

    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(error)

    else:
        # All other Errors not returned come here. And we can just print the default TraceBack.
        print('Unknown exception in command {}:'.format(ctx.command), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
        await ctx.send(error)

bot.add_cog(BotManagement(bot))
bot.add_cog(HierarchyManagement(bot))
bot.add_cog(PlayerManagement(bot))
bot.run(token)
