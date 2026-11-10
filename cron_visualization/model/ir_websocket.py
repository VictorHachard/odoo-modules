# -*- coding: utf-8 -*-
from odoo import models

from .cv_ir_cron_history import CRON_BUS_CHANNEL


class IrWebsocket(models.AbstractModel):
    _inherit = 'ir.websocket'

    def _build_bus_channel_list(self, channels):
        """ Keep the dashboard channel for Settings users only.

        `_prepare_subscribe_data` passes the client's channel list through
        untouched, so any client (an employee, a portal user, or the public
        user of an anonymous websocket) could ask for a plain string channel by
        name. The dashboard channel carries cron ids, which is what the
        `base.group_system` ACL on `cv.ir.cron.history` and on `ir.cron` gates:
        strip it here so subscribing to it is not a way around that ACL.
        """
        # sudo on the membership test, not on the channel: reading which
        # groups you are in is not a privileged read, and in recent Odoo versions the
        # unsudoed call goes through res.groups, whose menu_access reaches
        # ir.ui.menu. Every restriction that model carries then applies, and
        # the bus subscription of a whole screen died on an AccessError about
        # menus while asking a question about groups.
        # Other overrides (mail, ...) may already have swapped some names for
        # recordsets, and comparing one to a string is what the ORM warns
        # about: hence the isinstance guard on both tests.
        asked = any(c == CRON_BUS_CHANNEL for c in channels if isinstance(c, str))
        if asked and not self.env.user.sudo().has_group('base.group_system'):
            channels = [c for c in channels if not isinstance(c, str) or c != CRON_BUS_CHANNEL]
        return super()._build_bus_channel_list(channels)
