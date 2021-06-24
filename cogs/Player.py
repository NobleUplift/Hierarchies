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
from custom.Custom import CustomManagement

class PlayerManagement(commands.Cog):
    """Commands for managing player roles."""
    _instance = None

    def __new__(cls, bot):
        if cls._instance is None:
            cls._instance = super(PlayerManagement, cls).__new__(cls)
            # Put any initialization here.
        return cls._instance
    
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    async def _core_promote_assign(self, command: str, ctx: discord.ext.commands.Context, Member: discord.Member, Tier: discord.Role):
        """Core method used in promote/assign commands."""

        server_id = ctx.message.guild.id
        server_json = get_server_json(server_id)

        if str(Tier.id) not in server_json['roles']:
            await logger(self.bot, ctx,
                         f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not {command} {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because role {Tier.mention} does not belong to a hierarchy.')
            return await ctx.send(f'Role {Tier.mention} does not belong to a hierarchy.')
        hierarchy_name = server_json['roles'][str(Tier.id)]
        hierarchy = server_json['hierarchies'][hierarchy_name]['tiers']

        author_tiers = []
        target_tiers = []
        tier_source = None
        tier_target = None
        # Get Discord roles for every role ID and parent role ID in the hierarchy
        # Store them in the hierarchy because this is a temporary object
        # that will not be saved to file
        for tier_object in hierarchy:
            role = discord.utils.get(ctx.guild.roles, id=tier_object['role_id'])
            if role is None:
                await logger(self.bot, ctx,
                             f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not {command} {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because a deleted role {tier_object["role_id"]} still exists in the hierarchy.')
                return await ctx.send(f'Role {tier_object["role_id"]} was deleted but still exists in the hierarchy.')
            parent_role = discord.utils.get(ctx.guild.roles, id=tier_object['parent_role_id'])
            if int(tier_object['parent_role_id']) != 0 and parent_role is None:
                await logger(self.bot, ctx,
                             f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not {command} {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because a deleted parent role {tier_object["parent_role_id"]} still exists in the hierarchy.')
                return await ctx.send(
                    f'Parent role {tier_object["parent_role_id"]} was deleted but still exists in the hierarchy.')
            tier_object['role'] = role
            tier_object['parent_role'] = parent_role

            if role in ctx.author.roles and \
                    tier_object['promotion_min_depth'] != -1 and \
                    tier_object['promotion_max_depth'] != -1:
                author_tiers.append(tier_object)
            if role in Member.roles:
                target_tiers.append(tier_object)
            if role.id == Tier.id:
                tier_target = tier_object

        if len(author_tiers) == 0:
            await logger(self.bot, ctx,
                         f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not {command} {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because he/she has no roles in hierarchy {hierarchy_name} that are capable of promoting.')
            return await ctx.send(
                f'You have no roles in hierarchy {hierarchy_name} that are capable of promoting. You cannot {command} members.')

        if tier_target is None:
            await logger(self.bot, ctx,
                         f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not {command} {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because role exists in role lookup but not in hierarchy tree.')
            return await ctx.send(
                f'Hierarchy {hierarchy_name} is corrupted. Role exists in role lookup but not in hierarchy tree. You should never see this error.')

        if command == 'promote':
            for tier_object in target_tiers:
                # Try to locate the role that we are going to remove before promoting
                if tier_object['parent_role_id'] == Tier.id:
                    if tier_source is None:
                        # If the role was found and it is the only role, assign it
                        tier_source = tier_object
                    else:
                        # If multiple roles share this parent
                        await logger(self.bot, ctx,
                                     f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not {command} {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because this member has 2 or more child roles in hierarchy {hierarchy_name}.')
                        return await ctx.send(
                            f'This member has 2 or more child roles in hierarchy {hierarchy_name}. You cannot {command} a user who has two tiers at the same level.')

            # Enforce tier_source as a requirement when promoting. Only allow ^assign for lowest role
            # TODO: Remove maximum_depth, no longer useful
            if tier_source is None:  # and int(tier_target["depth"]) != int(server_json["hierarchies"][hierarchy_name]["maximum_depth"])
                await logger(self.bot, ctx,
                             f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not {command} {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because {Member.mention} does not have its child role.')
                return await ctx.send(
                    f'Cannot {command} to <@&{tier_target["role_id"]}> because {Member.mention} does not have its child role.')

        # Iterate over author's tiers looking for role that can promote
        for tier_object in author_tiers:
            print(f'Calculating depth {tier_target["depth"]} - {tier_object["depth"]}')
            calculated_depth = tier_target['depth'] - tier_object['depth']
            if tier_object['promotion_min_depth'] <= calculated_depth <= tier_object['promotion_max_depth']:

                async def role_change_function(Member, Tier, NewTier):
                    if tier_source is not None:
                        await Member.remove_roles(tier_source['role'])
                    await Member.add_roles(NewTier)

                custom_cog = CustomManagement(self.bot)
                custom_method = getattr(custom_cog, command + '_hooks')
                if callable(custom_method):
                    await custom_method(ctx, Member, tier_source['role'], tier_target['role'], hierarchy_name, role_change_function)
                else:
                    await role_change_function(Member, tier_source['role'], tier_target['role'])

                await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) {"promoted" if command == "promote" else "assigned"} {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention}.')
                return await ctx.send(f'{"Promoted" if command == "promote" else "Assigned"} {Member.mention} to {Tier.mention}.')
            else:
                # Might send multiple times for multiple roles
                await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not {command} {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because role <@&{tier_object["role_id"]}> can only {command} between {tier_object["promotion_min_depth"]} and {tier_object["promotion_max_depth"]} roles down, inclusively.')
                await ctx.send(f'Your role <@&{tier_object["role_id"]}> can only {command} between {tier_object["promotion_min_depth"]} and {tier_object["promotion_max_depth"]} roles down, inclusively.')
        return

    @commands.command(pass_context=True)
    async def promote(self, ctx: discord.ext.commands.Context, Member: discord.Member, Tier: discord.Role):
        """Remove a role from a user and give that user the next highest role in the hierarchy."""
        return await self._core_promote_assign(self, 'promote', ctx, Member, Tier)

    @commands.command(pass_context=True)
    async def assign(self, ctx: discord.ext.commands.Context, Member: discord.Member, Tier: discord.Role):
        """Assign a role to a user in the hierarchy. This should only be used for roles that cannot be promoted or demoted."""
        return await self._core_promote_assign(self, 'assign', ctx, Member, Tier)

    async def _core_demote_unassign(self, command: str, ctx: discord.ext.commands.Context, Member: discord.Member, Tier: discord.Role):
        """Core method used in promote/assign commands."""

        server_id = ctx.message.guild.id
        server_json = get_server_json(server_id)

        if str(Tier.id) not in server_json['roles']:
            await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not {command} {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because role {Tier.mention} does not belong to a hierarchy.')
            return await ctx.send(f'Role {Tier.mention} does not belong to a hierarchy.')
        hierarchy_name = server_json['roles'][str(Tier.id)]
        hierarchy = server_json['hierarchies'][hierarchy_name]['tiers']

        author_tiers = []
        target_tiers = []
        tier_source = None
        tier_target = None
        # Get Discord roles for every role ID and parent role ID in the hierarchy
        # Store them in the hierarchy because this is a temporary object
        # that will not be saved to file
        for tier_object in hierarchy:
            role = discord.utils.get(ctx.guild.roles, id=tier_object['role_id'])
            if role is None:
                await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not {command} {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because a deleted role {tier_object["role_id"]} still exists in the hierarchy.')
                return await ctx.send(f'Role {tier_object["role_id"]} was deleted but still exists in the hierarchy.')
            parent_role = discord.utils.get(ctx.guild.roles, id=tier_object['parent_role_id'])
            if int(tier_object['parent_role_id']) != 0 and parent_role is None:
                await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not {command} {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because a deleted parent role {tier_object["parent_role_id"]} still exists in the hierarchy.')
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
                tier_target = tier_object

        if len(author_tiers) == 0:
            await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not {command} {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because he/she has no roles in hierarchy {hierarchy_name} that are capable of demoting.')
            return await ctx.send(f'You have no roles in hierarchy {hierarchy_name} that are capable of demoting. You cannot {command} members.')

        if command == 'demote':
            if tier_target is None:
                await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not {command} {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because role exists in role lookup but not in hierarchy tree.')
                return await ctx.send(f'Hierarchy {hierarchy_name} is corrupted. Role exists in role lookup but not in hierarchy tree. You should never see this error.')

            tier_source = None
            for tier_object in target_tiers:
                # Try to locate the role that we are going to remove before demoting
                print(f'{tier_object["role_id"]}  == {tier_target["parent_role_id"]}')
                if tier_object['role_id'] == tier_target['parent_role_id']:
                    if tier_source is None:
                        # If the role was found and it is the only role, assign it
                        tier_source = tier_object
                    else:
                        # If multiple roles share this parent
                        await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not {command} {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because this member has 2 or more child roles in hierarchy {hierarchy_name}.')
                        return await ctx.send(f'This member has 2 or more child roles in hierarchy {hierarchy_name}. You cannot {command} a user who has two tiers at the same level.')

            if tier_source is None:
                await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not {command} {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because {Member.mention} does not have its child role.')
                return await ctx.send(f'You cannot {command} a user at the lowest level of the hierarchy. Use unassign for this instead.')
        elif command == 'unassign':
            tier_source = tier_target
            tier_target = None
        else:
            raise Exception("This error should be impossible.")

        # Iterate over author's tiers looking for role that can demote
        for tier_object in author_tiers:
            print(f'Calculating depth {tier_target["depth"]} - {tier_object["depth"]}')
            calculated_depth = tier_target['depth'] - tier_object['depth']
            if tier_object['demotion_min_depth'] <= calculated_depth <= tier_object['demotion_max_depth']:

                async def role_change_function(Member, Tier, NewTier):
                    await Member.remove_roles(Tier)
                    if tier_target is not None:
                        await Member.add_roles(NewTier)

                custom_cog = CustomManagement(self.bot)
                custom_method = getattr(custom_cog, command + '_hooks')
                if callable(custom_method):
                    await custom_method(ctx, Member, tier_source['role'], tier_target['role'], hierarchy_name, role_change_function)
                else:
                    await role_change_function(Member, tier_source['role'], tier_target['role'])

                await logger(self.bot, ctx, f'{ctx.author.name} {ctx.author.mention} {"demoted" if command == "demote" else "unassigned"} {Member.name} {Member.mention} to {Tier.name} {Tier.mention}.')
                return await ctx.send(f'{"Demoted" if command == "demote" else "Unassigned"} {Member.mention} to {Tier.mention}.')
            else:
                # Might send multiple times for multiple roles
                await logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) could not {command} {Member.mention} ({Member.name}#{Member.discriminator}) to {Tier.mention} because role <@&{tier_object["role_id"]}> can only {command} between {tier_object["demotion_min_depth"]} and {tier_object["demotion_max_depth"]} roles down, inclusively.')
                await ctx.send(f'Your role <@&{tier_object["role_id"]}> can only {command} between {tier_object["demotion_min_depth"]} and {tier_object["demotion_max_depth"]} roles down, inclusively.')
        return

    @commands.command(pass_context=True)
    async def demote(self, ctx: discord.ext.commands.Context, Member: discord.Member, Tier: discord.Role):
        """Remove a role from the user and give that user the next lowest role in the hierarchy."""
        return await self._core_demote_unassign('demote', ctx, Member, Tier)

    @commands.command(pass_context=True)
    async def unassign(self, ctx: discord.ext.commands.Context, Member: discord.Member, Tier: discord.Role):
        """Unassign a role from a user in the hierarchy. This should only be used for roles that cannot be promoted or demoted."""
        return await self._core_demote_unassign('unassign', ctx, Member, Tier)
