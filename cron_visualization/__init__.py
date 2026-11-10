# -*- coding: utf-8 -*-
from . import model


def _uninstall_hook(env):
    """Give the Scheduled Actions menu its views back.

    The module adds `kanban` to the view modes of `base.ir_cron_act`, a record
    owned by `base`, which uninstalling this module does not restore: the menu
    kept offering a kanban switch that no longer leads to the dashboard.
    """
    action = env.ref('base.ir_cron_act', raise_if_not_found=False)
    if action and 'kanban' in (action.view_mode or '').split(','):
        action.view_mode = ','.join(mode for mode in action.view_mode.split(',') if mode != 'kanban')
