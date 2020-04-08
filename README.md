# Don't grant "Manage Roles", use Hierarchies
As any Discord owner knows, the "Manage Roles" permission is incredibly dangerous. The way I thought it worked was that if you grant the "Manage Roles" permission to a lower role, members can only assign roles at or below that role. Wrong! A role with the "Manage Roles" permission, regardless of how low that role in the tree is, will grant "Manage Roles" based on *the highest role of the member!*

So, if you only want your moderators to have the ability to add/modify/delete roles at the bottom of your role list, but your moderator role is at the top of your role list, then you've granted almost complete control of your server to your moderators.

Not only that, if you do not explicitly deny the "Manage Permissions" permission on every single channel, *"Manage Roles" implicitly grants the "Manage Permissions" permission.* This means that when you give the "Manage Roles" permission to a user, that user could delete every single channel in your Discord server 

## Introducing: Hierarchies
Because of all the shortfalls of the "Manage Roles" permission, and because I handle multiple hierarchies on several Discord servers, I created this Discord bot to allow the easy creation of hierarchies within the Discord role system. It's very easy to create a Hierarchy, add roles to it, and then immediate start using it to promote or demote members.

```
^create moderators @administrator
^add @moderator @administrator
^promote @NobleUplift @moderator
^promote @NobleUplift @administrator
```

## Explaining Depth
There are four very powerful parameters in the `^add` command that control all of hierarchies, and these are: Promotion Minimum Depth, Promotion Maximum Depth, Demotion Minimum Depth, and Demotion Maximum Depth.

Minimum depth is the number of tiers *below* the tier you are adding that you are allowed to promote or demote members from, inclusively.

Maximum depth is the number of tiers *below* the tier that you are adding that you are allowed to promote or demote members from, inclusively.

For instance, if you add a role with minimum depth 0 and maximum depth 2, then members with that role can promote other members to that same role, or roles that are 2 roles deep into the hierarchy. If there is a role 3 roles removed from the role that you are adding, however, then you cannot promote or demote members to/from that role.

## Commands
| Command | Usage | Description | Examples |
|---|---|---|---|
| `^list` | `^list` | Lists all hierarchies in the server. | `^list` |
| `^show` | `^show <Hierarchy Name>` | Shows all of the tiers in a hierarchy | `^show moderators` |
| `^create` | `^create <Hierarchy Name> <Root Tier>` | Creates a new hierarchy with one role as its root tier. | `^create moderators @administrator` |
| `^delete` | `^delete <Hierarchy Name>` | Deletes a hierarchy, without deleting any Discord server roles. | `^delete` |
| `^add` | `^add <Child Tier> <Parent Tier> [Promotion Minimum Depth] [Promotion Maximum Depth] [Demotion Minimum Depth] [Demotion Maximum Depth]` | Adds a tier (role) to the hierarchy. | `^add @moderator @administrator`<br>`^add @moderator @administrator 0 5 0 5` |
| `^remove` | `^remove <Non-Root Tier>` | Removes a tier (role) from the hierarchy. | `^remove @moderator` |
| `^promote` | `^promote <Member> <Tier>` | Promotes a member from one role to another. Cannot be used to arbitrarily assign roles. You must assign the lowest tier in the hierarchy first and then promote. | `^promote NobleUplift @administrator` |
| `^demote` | `^demote <Member> <Tier>` | Demotes a member from one role to another. Currently, you cannot remove a hierarchy role from a member when at the lowest tier. | `^demote NobleUplift @moderator` |
| `^unlock` | `^unlock` | Unlocks the mutual exclusion on the server JSON file. | `^unlock` |
