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

class PlayerManagement(commands.Cog):
    """Commands for managing player roles."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            print('Creating the object')
            cls._instance = super(PlayerManagement, cls).__new__(cls)
            # Put any initialization here.
        return cls._instance
    
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @commands.command(pass_context=True)
    async def promote(self, ctx: discord.ext.commands.Context, Member: discord.Member, Tier: discord.Role):
        """Remove a role from a user and give that user the next highest role in the hierarchy."""

        server_id = ctx.message.guild.id
        server_json = get_server_json(server_id)

        if str(Tier.id) not in server_json['roles']:
            await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not promote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because role {Tier.mention} does not belong to a hierarchy.')
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
                await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not promote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because a deleted role {tier_object["role_id"]} still exists in the hierarchy.')
                return await ctx.send(f'Role {tier_object["role_id"]} was deleted but still exists in the hierarchy.')
            parent_role = discord.utils.get(ctx.guild.roles, id=tier_object['parent_role_id'])
            if int(tier_object['parent_role_id']) != 0 and parent_role is None:
                await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not promote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because a deleted parent role {tier_object["parent_role_id"]} still exists in the hierarchy.')
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
            await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not promote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because he/she has no roles in hierarchy {hierarchy_name} that are capable of promoting.')
            return await ctx.send(f'You have no roles in hierarchy {hierarchy_name} that are capable of promoting. You cannot promote members.')

        if tier_to_promote_to is None:
            await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not promote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because role exists in role lookup but not in hierarchy tree.')
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
                    await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not promote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because this member has 2 or more child roles in hierarchy {hierarchy_name}.')
                    return await ctx.send(f'This member has 2 or more child roles in hierarchy {hierarchy_name}. You cannot promote a user who has two tiers at the same level.')

        # Enforce tier_to_promote_from as a requirement when promoting. Only allow ^assign for lowest role
        # TODO: Remove maximum_depth, no longer useful
        if tier_to_promote_from is None: # and int(tier_to_promote_to["depth"]) != int(server_json["hierarchies"][hierarchy_name]["maximum_depth"])
            await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not promote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because {Member.mention} does not have its child role.')
            return await ctx.send(f'Cannot promote to <@&{tier_to_promote_to["role_id"]}> because {Member.mention} does not have its child role.')

        # Iterate over author's tiers looking for role that can promote
        for tier_object in author_tiers:
            print(f'Calculating depth {tier_to_promote_to["depth"]} - {tier_object["depth"]}')
            calculated_depth = tier_to_promote_to['depth'] - tier_object['depth']
            if tier_object['promotion_min_depth'] <= calculated_depth <= tier_object['promotion_max_depth']:
                if tier_to_promote_from is not None:
                    await Member.remove_roles(tier_to_promote_from['role'])

                await Member.add_roles(tier_to_promote_to['role'])

                await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) promoted {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention}.')
                return await ctx.send(f"Promoted {Member.mention} to {Tier.mention}.")
            else:
                # Might send multiple times for multiple roles
                await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not promote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because role <@&{tier_object["role_id"]}> can only promote between {tier_object["promotion_min_depth"]} and {tier_object["promotion_max_depth"]} roles down, inclusively.')
                await ctx.send(f'Your role <@&{tier_object["role_id"]}> can only promote between {tier_object["promotion_min_depth"]} and {tier_object["promotion_max_depth"]} roles down, inclusively.')
        return

    @commands.command(pass_context=True)
    async def assign(self, ctx: discord.ext.commands.Context, Member: discord.Member, Tier: discord.Role):
        """Assign a role to a user in the hierarchy. This should only be used for roles that cannot be promoted or demoted."""

        server_id = ctx.message.guild.id
        server_json = get_server_json(server_id)

        if str(Tier.id) not in server_json['roles']:
            await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not assign {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because role {Tier.mention} does not belong to a hierarchy.')
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
                await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not promote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because a deleted role {tier_object["role_id"]} still exists in the hierarchy.')
                return await ctx.send(f'Role {tier_object["role_id"]} was deleted but still exists in the hierarchy.')
            parent_role = discord.utils.get(ctx.guild.roles, id=tier_object['parent_role_id'])
            if int(tier_object['parent_role_id']) != 0 and parent_role is None:
                await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not promote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because a deleted parent role {tier_object["parent_role_id"]} still exists in the hierarchy.')
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
            await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not assign {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because he/she has no roles in hierarchy {hierarchy_name} that are capable of assigning.')
            return await ctx.send(f'You have no roles in hierarchy {hierarchy_name} that are capable of promoting. You cannot promote members.')

        if tier_to_promote_to is None:
            await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not assign {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because role exists in role lookup but not in hierarchy tree.')
            return await ctx.send(f'Hierarchy {hierarchy_name} is corrupted. Role exists in role lookup but not in hierarchy tree. You should never see this error.')

        # Iterate over author's tiers looking for role that can promote
        for tier_object in author_tiers:
            print(f'Calculating depth {tier_to_promote_to["depth"]} - {tier_object["depth"]}')
            calculated_depth = tier_to_promote_to['depth'] - tier_object['depth']
            if tier_object['promotion_min_depth'] <= calculated_depth <= tier_object['promotion_max_depth']:
                await Member.add_roles(tier_to_promote_to['role'])
                await logger(self.bot, ctx, f'{ctx.author.name} {ctx.author.mention} assigned {Member.name} {Member.mention} to role {Tier.name} {Tier.mention}.')
                return await ctx.send(f"Assigned {Tier.mention} to {Member.mention}.")
            else:
                # Might send multiple times for multiple roles
                await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not assign {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because role <@&{tier_object["role_id"]}> can only promote between {tier_object["promotion_min_depth"]} and {tier_object["promotion_max_depth"]} roles down, inclusively.')
                await ctx.send(f'Your role <@&{tier_object["role_id"]}> can only assign between {tier_object["promotion_min_depth"]} and {tier_object["promotion_max_depth"]} roles down, inclusively.')
        return

    @commands.command(pass_context=True)
    async def demote(self, ctx: discord.ext.commands.Context, Member: discord.Member, Tier: discord.Role):
        """Remove a role from the user and give that user the next lowest role in the hierarchy."""

        server_id = ctx.message.guild.id
        server_json = get_server_json(server_id)

        if str(Tier.id) not in server_json['roles']:
            await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not demote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because role {Tier.mention} does not belong to a hierarchy.')
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
                await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not promote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because a deleted role {tier_object["role_id"]} still exists in the hierarchy.')
                return await ctx.send(f'Role {tier_object["role_id"]} was deleted but still exists in the hierarchy.')
            parent_role = discord.utils.get(ctx.guild.roles, id=tier_object['parent_role_id'])
            if int(tier_object['parent_role_id']) != 0 and parent_role is None:
                await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not promote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because a deleted parent role {tier_object["parent_role_id"]} still exists in the hierarchy.')
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
            await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not demote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because he/she has no roles in hierarchy {hierarchy_name} that are capable of demoting.')
            return await ctx.send(f'You have no roles in hierarchy {hierarchy_name} that are capable of demoting. You cannot demote members.')

        if tier_to_demote_to is None:
            await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not demote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because role exists in role lookup but not in hierarchy tree.')
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
                    await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not demote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because this member has 2 or more child roles in hierarchy {hierarchy_name}.')
                    return await ctx.send(f'This member has 2 or more child roles in hierarchy {hierarchy_name}. You cannot demote a user who has two tiers at the same level.')

        if tier_to_demote_from is None:
            await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not promote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because {Member.mention} does not have its child role.')
            return await ctx.send(f'You cannot demote a user at the lowest level of the hierarchy. Use unassign for this instead.')

        # Iterate over author's tiers looking for role that can demote
        for tier_object in author_tiers:
            print(f'Calculating depth {tier_to_demote_to["depth"]} - {tier_object["depth"]}')
            calculated_depth = tier_to_demote_to['depth'] - tier_object['depth']
            if tier_object['demotion_min_depth'] <= calculated_depth <= tier_object['demotion_max_depth']:
                #if tier_to_demote_from is not None:
                await Member.remove_roles(tier_to_demote_from['role'])
                await Member.add_roles(tier_to_demote_to['role'])
                await logger(self.bot, ctx, f'{ctx.author.name} {ctx.author.mention} demoted {Member.name} {Member.mention} to {Tier.name} {Tier.mention}.')
                return await ctx.send(f"Demoted {Member.mention} to {Tier.mention}.")
            else:
                # Might send multiple times for multiple roles
                await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not demote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because role <@&{tier_object["role_id"]}> can only demote between {tier_object["demotion_min_depth"]} and {tier_object["demotion_max_depth"]} roles down, inclusively.')
                await ctx.send(f'Your role <@&{tier_object["role_id"]}> can only demote between {tier_object["demotion_min_depth"]} and {tier_object["demotion_max_depth"]} roles down, inclusively.')
        return

    @commands.command(pass_context=True)
    async def unassign(self, ctx: discord.ext.commands.Context, Member: discord.Member, Tier: discord.Role):
        """Unassign a role from a user in the hierarchy. This should only be used for roles that cannot be promoted or demoted."""

        server_id = ctx.message.guild.id
        server_json = get_server_json(server_id)

        if str(Tier.id) not in server_json['roles']:
            await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not demote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because role {Tier.mention} does not belong to a hierarchy.')
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
                await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not promote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because a deleted role {tier_object["role_id"]} still exists in the hierarchy.')
                return await ctx.send(f'Role {tier_object["role_id"]} was deleted but still exists in the hierarchy.')
            parent_role = discord.utils.get(ctx.guild.roles, id=tier_object['parent_role_id'])
            if int(tier_object['parent_role_id']) != 0 and parent_role is None:
                await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not promote {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because a deleted parent role {tier_object["parent_role_id"]} still exists in the hierarchy.')
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
            await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not unassign {Member.mention} ({Member.name}#{Member.discriminator}) from {Tier.mention} because he/she has no roles in hierarchy {hierarchy_name} that are capable of unassigning.')
            return await ctx.send(f'You have no roles in hierarchy {hierarchy_name} that are capable of unassigning. You cannot unassigning members.')

        # Iterate over author's tiers looking for role that can demote
        for tier_object in author_tiers:
            print(f'Calculating depth {tier_to_demote_to["depth"]} - {tier_object["depth"]}')
            calculated_depth = tier_to_demote_to['depth'] - tier_object['depth']
            if tier_object['demotion_min_depth'] <= calculated_depth <= tier_object['demotion_max_depth']:
                # if tier_to_demote_from is not None:
                await Member.remove_roles(Tier)
                await logger(self.bot, ctx, f'{ctx.author.name} {ctx.author.mention} unassigned {Member.name} {Member.mention} from role {Tier.name} {Tier.mention}.')
                return await ctx.send(f"Unassigned {Tier.mention} from {Member.mention}.")
            else:
                # Might send multiple times for multiple roles
                await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not unassign {Member.mention} ({Member.name}#{Member.discriminator}) from {Tier.mention} because role <@&{tier_object["role_id"]}> can only demote between {tier_object["demotion_min_depth"]} and {tier_object["demotion_max_depth"]} roles down, inclusively.')
                await ctx.send( f'Your role <@&{tier_object["role_id"]}> can only unassign between {tier_object["demotion_min_depth"]} and {tier_object["demotion_max_depth"]} roles down, inclusively.')
        return
