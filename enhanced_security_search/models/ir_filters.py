# -*- coding: utf-8 -*-

from odoo import _, api, models
from odoo.exceptions import AccessError

CUSTOM_SEARCH_GROUP = 'enhanced_security_search.group_custom_search'


class IrFilters(models.Model):
    _inherit = 'ir.filters'

    def _enhanced_search_bypass(self):
        """Superuser mode (sudo, the module loader, crons running as root) and
        administrators (`base.group_erp_manager`, who hold full rights on
        `ir.filters` in core) are never restricted by this module."""
        return self.env.su or self.env.user._is_admin()

    def _enhanced_search_check(self):
        """Enforce the custom-search group when a favourite is saved.

        This is the whole server side of the module, and it covers exactly one
        thing: writing to ``ir.filters``. Without it the JS hide would be
        cosmetic even for favourites, since the Favorites column posts straight
        to /web/dataset/call_kw/ir.filters/create_filter.

        It deliberately does NOT gate *applying* a domain or a group-by. Those
        never touch ``ir.filters``: the client sends them to the read RPC, on
        every screen, and nothing distinguishes a domain the search view built
        from one a user typed. Do not read the module as an access control over
        data; the fence there is the record rules and the model access rights.
        """
        if self._enhanced_search_bypass():
            return
        if not self.env.user.has_group(CUSTOM_SEARCH_GROUP):
            raise AccessError(_("You are not allowed to manage custom search filters."))

    def _check_shared_filter(self):
        """A shared filter may only be changed by whoever shared it.

        A filter is shared when it is not private to the current user: either
        it has no user at all (shared with everyone), or it lists other users
        too. Core's employee rule (``base.ir_filters_employee_rule``,
        ``[('user_ids', 'in', [False, user.id])]``) grants write and unlink on
        every such row to every user it is shared with, so any employee could
        rewrite the domain of a filter the whole company relies on (an
        instance-wide favourite, a filter behind a website snippet or a
        dashboard...), or delete it.

        Deliberately keyed on ``create_uid`` rather than forbidding shared rows
        outright: sharing a favourite stays a feature, and its author keeps full
        control of it. What is closed is a shared row somebody else made.
        Reading and applying a shared filter is untouched, and so is creating
        one.
        """
        if self._enhanced_search_bypass():
            return
        user = self.env.user
        if any(filt.user_ids != user and filt.create_uid != user for filt in self):
            raise AccessError(_(
                "This search filter is shared with other users and was created "
                "by someone else. Only its author or an administrator can change "
                "or delete it."
            ))

    @api.model_create_multi
    def create(self, vals_list):
        self._enhanced_search_check()
        return super().create(vals_list)

    def write(self, vals):
        self._enhanced_search_check()
        self._check_shared_filter()
        return super().write(vals)

    def unlink(self):
        self._enhanced_search_check()
        self._check_shared_filter()
        return super().unlink()
