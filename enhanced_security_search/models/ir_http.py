# -*- coding: utf-8 -*-

from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        # The search bar, its Favorites column and the pivot header each probe
        # this group on mount. Answered from the page, `user.hasGroup` never
        # opens a call_kw for it.
        info = super().session_info()
        if self.env.user._is_internal():
            info.setdefault('groups', {})['enhanced_security_search.group_custom_search'] = (
                self.env.user.has_group('enhanced_security_search.group_custom_search')
            )
        return info
