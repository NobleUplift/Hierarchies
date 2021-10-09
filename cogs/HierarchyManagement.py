import discord
# pip install -U discord.py
from discord.ext import commands
# pip install -U discord-py-slash-command
from discord_slash import SlashCommand, SlashContext, cog_ext
from discord_slash.utils.manage_commands import create_option
from discord.ext.commands import Cog, command, has_permissions, MissingPermissions
from typing import Union
from cogs.CoreManagement import Core, ApplicationCommandOptionType


class HierarchyManagement(Cog):
    """Commands for managing creating, modifying, and deleting hierarchies."""
    _instance = None

    def __new__(cls, bot):
        if cls._instance is None:
            cls._instance = super(HierarchyManagement, cls).__new__(cls)
            # Put any initialization here.
        return cls._instance

    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @cog_ext.cog_slash(name="list", description="List all hierarchies.")
    async def _list(self, ctx: SlashContext):
        await self.list(ctx=ctx)

    @command(pass_context=True)
    @has_permissions(manage_roles=True)
    async def list(self, ctx: discord.ext.commands.Context):
        """Lists all hierarchies."""

        server_id = ctx.message.guild.id
        server_json = Core.get_server_json(server_id)

        if len(server_json['hierarchies']) == 0:
            return await ctx.send('This server has no hierarchies.')

        # TODO: Paginate this result in case
        server_hierarchies = server_json['hierarchies']
        retval = 'Hierarchies: \n'
        for n in server_hierarchies:
            retval += ' • ' + n + "\n"
        # No need to log read-only commands
        print(f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) listed hierarchies.')
        return await ctx.send(retval)

    @cog_ext.cog_slash(name="show", description="Shows all the roles in a single hierarchy.",
        options=[
            create_option(name="HierarchyName", description="The name of the hierarchy to show.", option_type=ApplicationCommandOptionType.STRING, required=True)
        ]
    )
    async def _show(self, ctx: SlashContext, *, HierarchyName: str):
        await self.show(ctx=ctx, HierarchyName=HierarchyName)

    @command(pass_context=True)
    @has_permissions(manage_roles=True)
    async def show(self, ctx: discord.ext.commands.Context, HierarchyName: str):
        """Shows all the roles in a single hierarchy."""

        server_id = ctx.message.guild.id
        server_json = Core.get_server_json(server_id)

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

    @cog_ext.cog_slash(name="create", description="Creates a new hierarchy.",
        options=[
           create_option(name="HierarchyName", description="The name of the hierarchy to show.", option_type=ApplicationCommandOptionType.STRING, required=True),
           create_option(name="RootTier", description="The role that will exist at the top of the hierarchy.", option_type=ApplicationCommandOptionType.ROLE, required=True)
        ]
    )
    async def _create(self, ctx: SlashContext, *, HierarchyName: str, RootTier: discord.Role):
        await self.create(ctx=ctx, HierarchyName=HierarchyName, RootTier=RootTier)

    @command(pass_context=True)
    @has_permissions(manage_roles=True)
    async def create(self, ctx: discord.ext.commands.Context, HierarchyName: str, RootTier: discord.Role):
        """Creates a new hierarchy."""

        if ' ' in HierarchyName:
            await Core.logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) tried to create a hierarchy `{HierarchyName}` with spaces in it.')
            return await ctx.send('Hierarchies name "' + HierarchyName + '" cannot have spaces in it.')

        if len(HierarchyName) > 32:
            await Core.logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) tried to create a hierarchy `{HierarchyName}` with more than 32 characters.')
            return await ctx.send('Hierarchies name "' + HierarchyName + '" cannot exceed 32 characters.')

        server_id = ctx.message.guild.id
        Core.lock_server_file(server_id)
        server_json = Core.get_server_json(server_id)
        server_json_hierarchies = server_json['hierarchies']

        if HierarchyName in server_json_hierarchies:
            Core.unlock_server_file(server_id)
            await Core.logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) tried to create a hierarchy `{HierarchyName}` that already exists.')
            return await ctx.send('Hierarchy "' + HierarchyName + '" already exists.')

        if str(RootTier.id) in server_json['roles']:
            Core.unlock_server_file(server_id)
            await Core.logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) tried to add root tier {RootTier.mention} but the role already exists in a hierarchy.')
            return await ctx.send(f'Role already exists in hierarchy `{server_json["roles"][str(RootTier.id)]}`.')

        server_json_hierarchies[HierarchyName] = {
            'tiers': [{
                'role_id': RootTier.id,
                'parent_role_id': 0,
                'depth': 0,
                'promotion_min_depth': 0,
                'promotion_max_depth': 500,
                'demotion_min_depth': 0,
                'demotion_max_depth': 500
            }],
            'maximum_depth': 0
        }
        server_json['roles'][str(RootTier.id)] = HierarchyName

        Core.save_server_file(server_id, server_json)
        Core.unlock_server_file(server_id)

        await Core.logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) created hierarchy `{HierarchyName}` with root tier {RootTier.mention}.')
        return await ctx.send('Created hierarchy ' + HierarchyName + '.')

    """

    DELETE

    """
    @cog_ext.cog_slash(name="delete", description="Deletes an existing Hierarchy.",
        options=[
            create_option(name="HierarchyName", description="The name of the hierarchy to delete.", option_type=ApplicationCommandOptionType.STRING, required=True)
        ]
    )
    async def _delete(self, ctx: SlashContext, *, HierarchyName: str):
        await self.delete(ctx=ctx, HierarchyName=HierarchyName)

    @command(pass_context=True)
    @has_permissions(manage_roles=True)
    async def delete(self, ctx: discord.ext.commands.Context, HierarchyName: str):
        """Deletes an existing Hierarchy."""

        server_id = ctx.message.guild.id
        Core.lock_server_file(server_id)
        server_json = Core.get_server_json(server_id)
        server_json_hierarchies = server_json['hierarchies']

        if HierarchyName in server_json_hierarchies:
            del server_json_hierarchies[HierarchyName]

            for key in dict(server_json['roles']):
                if server_json['roles'][key] == HierarchyName:
                    del server_json['roles'][key]

            Core.save_server_file(server_id, server_json)
            Core.unlock_server_file(server_id)
            await Core.logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) successfully deleted hierarchy `{HierarchyName}`.')
            return await ctx.send('Deleted hierarchy ' + HierarchyName + '.')
        else:
            Core.unlock_server_file(server_id)
            await Core.logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) tried to delete hierarchy `{HierarchyName}` that does not exist.')
            return await ctx.send('Hierarchy  does not exist.')
            
    # createrole
    # modifyrole
    # deleterole
    
    # linkrole - Link a lower depth parent to higher depth parent

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

    """

    ADD

    """
    @cog_ext.cog_slash(name="add", description="Adds an existing role to a hierarchy.",
        options=[
            create_option(name="Tier", description="The role to add to this hierarchy.", option_type=ApplicationCommandOptionType.ROLE, required=True),
            create_option(name="Parent", description="The parent role that this role will be nested under.", option_type=ApplicationCommandOptionType.ROLE, required=True),
            create_option(name="PromotionMinimumDepth", description="The minimum depth that this role can promote. -1 to disable, 0 to promote others to the same tier.", option_type=ApplicationCommandOptionType.INTEGER, required=False),
            create_option(name="PromotionMaximumDepth", description="The maximum depth that this role can promote. -1 to disable.", option_type=ApplicationCommandOptionType.INTEGER, required=False),
            create_option(name="DemotionMinimumDepth", description="The minimum depth that this role can demote. -1 to disable, 0 to demote others of the same tier.", option_type=ApplicationCommandOptionType.INTEGER, required=False),
            create_option(name="DemotionMaximumDepth", description="The maximum depth that this role can promote. -1 to disable.", option_type=ApplicationCommandOptionType.INTEGER, required=False),
            create_option(name="AllowPromoteDemote", description="True/False: Allow this role to be promoted to/demoted from.", option_type=ApplicationCommandOptionType.BOOLEAN, required=False),
            create_option(name="AllowAssignUnassign", description="True/False: Allow this role to be assigned to/unassigned from.", option_type=ApplicationCommandOptionType.BOOLEAN, required=False),
        ]
    )
    async def _add(self, ctx: SlashContext, *,
            Tier: discord.Role,
            Parent: discord.Role,
            PromotionMinimumDepth: int = -1,
            PromotionMaximumDepth: int = -1,
            DemotionMinimumDepth: int = -1,
            DemotionMaximumDepth: int = -1,
            AllowPromoteDemote: bool = True,
            AllowAssignUnassign: bool = True,
        ):
        await self.add(ctx=ctx, Tier=Tier, Parent=Parent, PromotionMinimumDepth=PromotionMinimumDepth, PromotionMaximumDepth=PromotionMaximumDepth, DemotionMinimumDepth=DemotionMinimumDepth, DemotionMaximumDepth=DemotionMaximumDepth, AllowPromoteDemote=AllowPromoteDemote, AllowAssignUnassign=AllowAssignUnassign,)

    @command(pass_context=True)
    @has_permissions(manage_roles=True)
    async def add(self, ctx: discord.ext.commands.Context, Tier: discord.Role, Parent: discord.Role,
            PromotionMinimumDepth: int = -1,
            PromotionMaximumDepth: int = -1,
            DemotionMinimumDepth: int = -1,
            DemotionMaximumDepth: int = -1,
            AllowPromoteDemote: bool = True,
            AllowAssignUnassign: bool = True,
        ):
        """Adds an existing role to a hierarchy."""

        server_id = ctx.message.guild.id
        Core.lock_server_file(server_id)
        server_json = Core.get_server_json(server_id)

        if str(Tier.id) in server_json['roles']:
            Core.unlock_server_file(server_id)
            await Core.logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) tried to add {Tier.mention}, parent role {Parent.mention}, but the role already exists in a hierarchy.')
            return await ctx.send(f'Role already exists in hierarchy `{server_json["roles"][str(Tier.id)]}`.')

        if str(Parent.id) not in server_json['roles']:
            Core.unlock_server_file(server_id)
            await Core.logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) tried to add {Tier.mention}, parent role {Parent.mention}, but the parent role does not exist in a hierarchy.')
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
                'demotion_max_depth': DemotionMaximumDepth,
                'allow_promote_demote': AllowPromoteDemote,
                'allow_assign_unassign': AllowAssignUnassign,
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
                Core.save_server_file(server_id, server_json)
                Core.unlock_server_file(server_id)
                await Core.logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) added {Tier.mention}, parameters {Parent.mention} {PromotionMinimumDepth} {PromotionMaximumDepth} {DemotionMinimumDepth} {DemotionMaximumDepth}, to hierarchy `{hierarchy_name}`.')
                return await ctx.send(f'Successfully added {Tier.mention}, parent role {Parent.mention}, to hierarchy `{hierarchy_name}`.')
            else:
                Core.unlock_server_file(server_id)
                await Core.logger(self.bot, ctx, f'**SERVER CORRUPTION!** {ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) tried to add {Tier.mention}, but parent role {Parent.mention} does not exist in hierarchy `{hierarchy_name}`.')
                return await ctx.send(f'**SERVER CORRUPTION!** Parent role {Parent.mention} exists in the server role lookup, but does not exist in hierarchy `{hierarchy_name}`! Please contact the developer.')
        else:
            Core.unlock_server_file(server_id)
            await Core.logger(self.bot, ctx, f'**SERVER CORRUPTION!** {ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) tried to add {Tier.mention}, parent role {Parent.mention}, but parent role hierarchy `{hierarchy_name}` no longer exists.')
            return await ctx.send(f'**SERVER CORRUPTION!** Parent role {Parent.mention} exists in the server role lookup, but hierarchy `{hierarchy_name}` no longer exists! Please contact the developer.')

    """

    MODIFY

    """
    @cog_ext.cog_slash(name="modify", description="Adds an existing role to a hierarchy.",
        options=[
            create_option(name="Tier", description="The role to add to this hierarchy.", option_type=ApplicationCommandOptionType.ROLE, required=True),
            create_option(name="Parent", description="The parent role that this role will be nested under.", option_type=ApplicationCommandOptionType.ROLE, required=True),
            create_option(name="PromotionMinimumDepth", description="The minimum depth that this role can promote. -1 to disable, 0 to promote others to the same tier.", option_type=ApplicationCommandOptionType.INTEGER, required=False),
            create_option(name="PromotionMaximumDepth", description="The maximum depth that this role can promote. -1 to disable.", option_type=ApplicationCommandOptionType.INTEGER, required=False),
            create_option(name="DemotionMinimumDepth", description="The minimum depth that this role can demote. -1 to disable, 0 to demote others of the same tier.", option_type=ApplicationCommandOptionType.INTEGER, required=False),
            create_option(name="DemotionMaximumDepth", description="The maximum depth that this role can promote. -1 to disable.", option_type=ApplicationCommandOptionType.INTEGER, required=False),
            create_option(name="AllowPromoteDemote", description="True/False: Allow this role to be promoted to/demoted from.", option_type=ApplicationCommandOptionType.BOOLEAN, required=False),
            create_option(name="AllowAssignUnassign", description="True/False: Allow this role to be assigned to/unassigned from.", option_type=ApplicationCommandOptionType.BOOLEAN, required=False),
        ]
    )
    async def _modify(self, ctx: SlashContext, *,
            Tier: discord.Role,
            Parent: discord.Role,
            PromotionMinimumDepth: int = -1,
            PromotionMaximumDepth: int = -1,
            DemotionMinimumDepth: int = -1,
            DemotionMaximumDepth: int = -1,
            AllowPromoteDemote: bool = True,
            AllowAssignUnassign: bool = True,
        ):
        await self.modify(ctx=ctx, Tier=Tier, Parent=Parent, PromotionMinimumDepth=PromotionMinimumDepth, PromotionMaximumDepth=PromotionMaximumDepth, DemotionMinimumDepth=DemotionMinimumDepth, DemotionMaximumDepth=DemotionMaximumDepth, AllowPromoteDemote=AllowPromoteDemote, AllowAssignUnassign=AllowAssignUnassign,)

    @command(pass_context=True)
    @has_permissions(manage_roles=True)
    async def modify(self, ctx: discord.ext.commands.Context, Tier: discord.Role, Parent: discord.Role,
            PromotionMinimumDepth: int = -1,
            PromotionMaximumDepth: int = -1,
            DemotionMinimumDepth: int = -1,
            DemotionMaximumDepth: int = -1,
            AllowPromoteDemote: bool = True,
            AllowAssignUnassign: bool = True,
        ):
        """Modifies a role within a hierarchy."""

        server_id = ctx.message.guild.id
        Core.lock_server_file(server_id)
        server_json = Core.get_server_json(server_id)

        if str(Tier.id) not in server_json['roles']:
            Core.unlock_server_file(server_id)
            await Core.logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) tried to modify {Tier.mention}, but the role does not exist in a hierarchy.')
            return await ctx.send(f'Role {Tier.mention} does not exist in a hierarchy.')
        hierarchy_name = server_json['roles'][str(Tier.id)]

        if str(Parent.id) not in server_json['roles']:
            Core.unlock_server_file(server_id)
            await Core.logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) cannot change {Tier.mention} to parent role {Parent.mention} because parent role does not exist in a hierarchy.')
            return await ctx.send(f'Cannot change {Tier.mention} to parent role {Parent.mention} because parent role does not exist in a hierarchy.')
        parent_hierarchy_name = server_json['roles'][str(Parent.id)]

        if hierarchy_name != parent_hierarchy_name:
            Core.unlock_server_file(server_id)
            await Core.logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) cannot change {Tier.mention} to parent role {Parent.mention} because parent role does not exist in hierarchy {hierarchy_name}.')
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
                    if 'parent_role_id' in tier and tier['parent_role_id'] == 0:
                        Core.unlock_server_file(server_id)
                        await Core.logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) cannot change {Tier.mention} to parent role {Parent.mention} because {Tier.mention} is the root tier of hierarchy {hierarchy_name}.')
                        return await ctx.send(f'Cannot change {Tier.mention} to parent role {Parent.mention} because {Tier.mention} is the root tier of hierarchy {hierarchy_name}.')
                    
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
                Core.save_server_file(server_id, server_json)
                Core.unlock_server_file(server_id)
                await Core.logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) modified {Tier.mention}, parameters {Parent.mention} {PromotionMinimumDepth} {PromotionMaximumDepth} {DemotionMinimumDepth} {DemotionMaximumDepth}, in hierarchy `{hierarchy_name}`.')
                return await ctx.send(f'Successfully modified {Tier.mention} in hierarchy `{hierarchy_name}`.')
            else:
                Core.unlock_server_file(server_id)
                await Core.logger(self.bot, ctx, f'**SERVER CORRUPTION!** {ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) tried to modify {Tier.mention}, parameters {Parent.mention} {PromotionMinimumDepth} {PromotionMaximumDepth} {DemotionMinimumDepth} {DemotionMaximumDepth}, but role {Tier.mention} does not exist in hierarchy `{hierarchy_name}`.')
                return await ctx.send(f'**SERVER CORRUPTION!** Role {Tier.mention} exists in the server role lookup, but does not exist in hierarchy `{hierarchy_name}`! Please contact the developer.')
        else:
            Core.unlock_server_file(server_id)
            await Core.logger(self.bot, ctx, f'**SERVER CORRUPTION!** {ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) tried to modify {Tier.mention}, parameters {Parent.mention} {PromotionMinimumDepth} {PromotionMaximumDepth} {DemotionMinimumDepth} {DemotionMaximumDepth}, but role hierarchy `{hierarchy_name}` no longer exists.')
            return await ctx.send(f'**SERVER CORRUPTION!** Role {Tier.mention} exists in the server role lookup, but hierarchy `{hierarchy_name}` no longer exists! Please contact the developer.')

    """

    DELETE

    """

    @cog_ext.cog_slash(name="remove", description="Removes a role from a hierarchy, linking all former child roles to its parent role. The root role cannot be deleted.",
        options=[
           create_option(name="Tier", description="The role to remove from its Hierarchy.", option_type=ApplicationCommandOptionType.STRING, required=True)
        ]
    )
    async def _remove(self, ctx: SlashContext, *, Tier: Union[discord.Role, int]):
        await self.remove(ctx=ctx, Tier=Tier)

    @command(pass_context=True)
    @has_permissions(manage_roles=True)
    async def remove(self, ctx: discord.ext.commands.Context, Tier: Union[discord.Role, int]):
        """Removes a role from a hierarchy, linking all former child roles to its parent role. The root role cannot be deleted."""

        server_id = ctx.message.guild.id
        Core.lock_server_file(server_id)
        server_json = Core.get_server_json(server_id)
        role_id = None
        role_mention = None

        if isinstance(Tier, discord.Role):
            role_id = Tier.id
            role_mention = Tier.mention
        else:
            role_id = Tier
            role_mention = f'<@&!{role_id}>'

        if str(role_id) not in server_json['roles']:
            Core.unlock_server_file(server_id)
            await Core.logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) attempted to remove {role_mention} when it does not belong to a hierarchy.')
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
                        Core.unlock_server_file(server_id)
                        await Core.logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) attempted to remove the root role {role_mention} from hierarchy `{hierarchy_name}`.')
                        return await ctx.send(f'Cannot delete root tier for hierarchy {hierarchy_name}. Delete and recreate the hierarchy.')

            if tier_to_remove is None:
                Core.unlock_server_file(server_id)
                await Core.logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) attempted to remove {role_mention} from hierarchy `{hierarchy_name}` where it does not exist.')
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
                Core.save_server_file(server_id, server_json)
                Core.unlock_server_file(server_id)
                await Core.logger(self.bot, ctx, f'{ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) removed {role_mention} from hierarchy `{hierarchy_name}`.')
                return await ctx.send(f'Successfully removed {role_mention} from hierarchy `{hierarchy_name}`.')
            else:
                Core.unlock_server_file(server_id)
                await Core.logger(self.bot, ctx, f'**SERVER CORRUPTION!** {ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) tried to remove {role_mention} but it does not exist in hierarchy `{hierarchy_name}`.')
                return await ctx.send(f'**SERVER CORRUPTION!** Role {role_mention} exists in the server role lookup, but does not exist in hierarchy `{hierarchy_name}`! Please contact the developer.')
        else:
            Core.unlock_server_file(server_id)
            await Core.logger(self.bot, ctx, f'**SERVER CORRUPTION!** {ctx.author.mention} ({ctx.author.name}#{ctx.author.discriminator}) tried to remove {role_mention} but role hierarchy `{hierarchy_name}` no longer exists.')
            return await ctx.send(f'**SERVER CORRUPTION!** Role {role_mention} exists in the server role lookup, but hierarchy `{hierarchy_name}` no longer exists! Please contact the developer.')