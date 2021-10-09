# Don't grant "Manage Roles", use Hierarchies
As any Discord owner knows, the "Manage Roles" permission is incredibly dangerous. The way I thought it worked was that if you grant the "Manage Roles" permission to a lower role, members can only assign roles at or below that role. Wrong! A role with the "Manage Roles" permission, regardless of how low that role in the tree is, will grant "Manage Roles" based on *the highest role of the member!*

So, if you only want your moderators to have the ability to add/modify/delete roles at the bottom of your role list, but your moderator role is at the top of your role list, then you've granted almost complete control of your server to your moderators.

Not only that, if you do not explicitly deny the "Manage Permissions" permission on every single channel, *"Manage Roles" implicitly grants the "Manage Permissions" permission.* This means that when you give the "Manage Roles" permission to a user, **that user could delete every single channel in your Discord server!**

## Introducing: Hierarchies
Because of all the shortfalls of the "Manage Roles" permission, and because I handle multiple hierarchies on several Discord servers, I created this Discord bot to allow the easy creation of hierarchies within the Discord role system. It's very easy to create a Hierarchy, add roles to it, and then immediately start using it to promote or demote members.

```
### Create the hierarchy
^create staff @administrator
^add @high-moderator @administrator 1 2 1 2
^add @moderator @high-moderator
^add @low-moderator @moderator
### Assign a member to the hierarchy and promote him
^assign @NobleUplift#1038 @low-moderator
^promote @NobleUplift#1038 @moderator
^promote @NobleUplift#1038 @high-moderator
### High Moderators can only demote between 1 level below  to 2 levels below
### Therefore, this demotion will fail
^demote @NobleUplift#1038 @moderator
```

## Explaining Depth
There are four very powerful parameters in the `^add` command that control all of hierarchies, and these are: Promotion Minimum Depth, Promotion Maximum Depth, Demotion Minimum Depth, and Demotion Maximum Depth.

Minimum depth is the number of tiers *below* the tier you are adding that you are allowed to promote or demote members from, inclusively.

Maximum depth is the number of tiers *below* the tier that you are adding that you are allowed to promote or demote members from, inclusively.

For instance, if you add a role with minimum depth 0 and maximum depth 2, then members with that role can promote other members to that same role, or roles that are 2 roles deep into the hierarchy. If there is a role 3 roles down from the role that you are adding, however, then you cannot promote or demote members to/from that role.

## Commands
| Command Usage | Description | Examples |
|---|---|---|
| `^list` | Lists all hierarchies in the server. | `^list` |
| `^show <Hierarchy Name>` | Shows all of the tiers in a hierarchy | `^show staff` |
| `^create <Hierarchy Name> <Root Tier>` | Creates a new hierarchy with one role as its root tier. | `^create staff @administrator` |
| `^delete <Hierarchy Name>` | Deletes a hierarchy, without deleting any Discord server roles. | `^delete staff` |
| `^add <Child Tier> <Parent Tier> [Promotion Minimum Depth] [Promotion Maximum Depth] [Demotion Minimum Depth] [Demotion Maximum Depth]` | Adds a tier (role) to the hierarchy. | `^add @high-moderator @administrator`<br>`^add @high-moderator @administrator 0 5 0 5` |
| `^modify <Child Tier> <Parent Tier> [Promotion Minimum Depth] [Promotion Maximum Depth] [Demotion Minimum Depth] [Demotion Maximum Depth]` | Modifies a tier (role) in the hierarchy. | `^modify @high-moderator @administrator`<br>`^add @high-moderator @administrator 1 5 1 5` |
| `^remove <Non-Root Tier>` | Removes a tier (role) from the hierarchy. Automatically rebuilds the tree afterwards. | `^remove @moderator` |
| `^promote <Member> <Tier>` | Promotes a member from one role to another. Cannot be used to arbitrarily assign roles. You must assign the lowest tier in the hierarchy first and then promote. | `^promote @NobleUplift#1038 @administrator` |
| `^demote <Member> <Tier>` | Demotes a member from one role to another. Member must have the role that the member is being demoted from. | `^demote @NobleUplift#1038 @high-moderator` |
| `^assign <Member> <Tier>` | Adds a role directly to a member without removing roles. Follows the same depth logic as `^promote`. | `^assign @NobleUplift#1038 @low-moderator` |
| `^unassign <Member> <Tier>` | Removes a single role from a member. Follows the same depth logic as `^demote`. | `^unassign @NobleUplift#1038 @low-moderator` |
| `^unlock` | Removes the mutual exclusion lock on the server JSON file. | `^unlock` |
