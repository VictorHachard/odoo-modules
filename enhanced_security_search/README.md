# Enhanced Security Custom Search - Odoo 20 Module

*by HVG Solutions*

Adds a group, **Enable Custom Search**, and hides the ad-hoc search controls from
every user who is not in it:

- "Custom Filter..." in the Filters column of the search panel and at the end of
  the search autocomplete,
- "Custom Date..." in the options of a date filter (it opens the same domain
  editor),
- "Add Custom Group" in the Group By column and in the pivot header,
- the pencil that opens the domain editor when a search facet is clicked (the
  group-by sort toggle on a facet keeps working),
- "Save current search" in the Favorites column.

## Scope

This is a user interface simplification, not an access control over data.

The server-side rules it adds are on `ir.filters` create / write / unlink:

- saving, renaming and deleting a favourite really is refused for a user outside
  the group;
- a filter shared with other users (with everyone, or with a list of users) can
  only be changed or deleted by its author or an administrator, while core lets
  every user it is shared with rewrite or delete it.

Superuser mode (`sudo()`) and administrators (`base.group_erp_manager`) are never
restricted. Reading and applying favourites is never restricted.

Applying a domain or a group-by is **not** gated, and cannot be: the web client
sends the domain and the groupby list straight to the read RPC on every screen it
opens, and the server has no way to tell a domain the search view produced from a
domain a user typed. Record rules and model access rights remain the only fence
around the data itself.

## Who holds the group

Every internal user, unless it is taken away from them one by one.

- At install, the post-install hook grants the group to every existing internal
  user, archived ones included.
- Afterwards, the group is linked into `base.default_user_group`, whose implied
  groups Odoo copies into `group_ids` when an internal user is created. The copy
  is a plain membership, so it can be removed from a single user without
  affecting anyone else.

A user record created with an explicit `(6, 0, [...])` on `group_ids` replaces
that default outright and will not have the group. Portal and public users never
get it.

## Uninstall

Uninstalling removes the group (and every membership of it) and the server-side
rules; the search interface goes back to the standard one for everybody.
