# -*- coding: utf-8 -*-
import datetime
import logging

from odoo import fields, models, api
from odoo.tools import SQL


_logger = logging.getLogger(__name__)

# Bus notification pushed to the cron kanban dashboard whenever a run starts or
# finishes; the kanban controller subscribes to it and reloads on demand, which
# replaces the old fixed-interval polling.
#
# It goes to a dedicated channel that the dashboard adds on mount and drops on
# unmount, NOT to the Settings group channel: every member of that group is
# subscribed to it by the framework on every page, so a few thousand runs a day
# were fanned out over the websocket to every logged-in administrator, who threw
# them away unless the kanban happened to be open. The channel is a plain string,
# which any client can ask for, so `ir.websocket` strips it for anyone outside
# `base.group_system` (see model/ir_websocket.py).
CRON_BUS_NOTIFICATION = 'cron_history_update'
CRON_BUS_CHANNEL = 'cron_visualization.dashboard'

# Default retention of the run history, in days. Overridable with the system
# parameter below; a missing, invalid or non-positive value falls back to the
# default, so the table can never be left to grow without bound by mistake.
DEFAULT_RETENTION_DAYS = 90
RETENTION_PARAM = 'cron_visualization.history_retention_days'

# Rows deleted per pass of the autovacuum.
GC_BATCH_SIZE = 10000


class CvIrCronHistory(models.Model):
    _name = 'cv.ir.cron.history'
    _description = 'Cron History'
    _rec_name = 'ir_cron_id'
    _order = 'id desc'

    ir_cron_id = fields.Many2one('ir.cron', string='Cron', required=True, ondelete='cascade', index=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user, readonly=True)
    type = fields.Selection([('manual', 'Manual'), ('automatic', 'Automatic')], string='Type', readonly=True)
    state = fields.Selection([('success', 'Success'), ('fail', 'Failed'), ('interruption', 'Interruption'), ('running', 'Running')],
                             string='State', readonly=True, default='running', index=True,
                             help="  * Success: The cron finished successfully.\n"
                                  "  * Failed: The cron finished with an error.\n"
                                  "  * Interruption: The cron was interrupted (server restart, ...).\n"
                                  "  * Running: The cron is currently running.")

    started_at = fields.Datetime(string='Started At', readonly=True, default=fields.Datetime.now)
    ended_at = fields.Datetime(string='Ended At', readonly=True)
    duration = fields.Float(string='Duration (minutes)', readonly=True, aggregator="avg", help='Duration in minutes')

    error = fields.Text(string='Error', readonly=True, help='Error message if the cron failed.')

    @api.depends('ir_cron_id', 'ir_cron_id.name')
    def _compute_display_name(self):
        for history in self:
            history.display_name = history.ir_cron_id.name or ''

    def _notify_dashboard(self):
        """ Push a lightweight notification so every open kanban dashboard
        reloads. Only the dashboards listening on CRON_BUS_CHANNEL receive it;
        we only send ids, the client refetches. """
        self.env['bus.bus']._sendone(CRON_BUS_CHANNEL, CRON_BUS_NOTIFICATION, {
            'cron_ids': self.ir_cron_id.ids,
        })

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._notify_dashboard()
        return records

    def _close_stale_running(self):
        """ Flag as interrupted the rows left in 'running' by a worker that died.

        A run is alive exactly as long as the worker executing it holds the row
        lock on its ``ir_cron`` record: `_acquire_one_job` takes it with
        ``FOR NO KEY UPDATE`` (in the cron worker, and in the HTTP request for
        "Run Manually") and keeps it until the job transaction is over, which is
        after `_callback` has closed the history row. So a 'running' row whose
        cron we can lock ourselves (``SKIP LOCKED``, never waiting) belongs to a
        worker that is gone: killed by ``limit_time_real``, OOM, a restart...

        This replaces an age threshold (24h), which both left the spinner of a
        killed run lit for a day and declared a legitimate long batch dead.
        A cron locked by anything else (a user saving it, say) is simply skipped
        until the next pass: calling a live run dead is the worse mistake.
        """
        History = self.sudo()
        running = History.search([('state', '=', 'running')])
        if not running:
            return History
        self.env.cr.execute(SQL(
            "SELECT id FROM ir_cron WHERE id IN %s FOR NO KEY UPDATE SKIP LOCKED",
            tuple(running.ir_cron_id.ids),
        ))
        idle_cron_ids = {cron_id for (cron_id,) in self.env.cr.fetchall()}
        stale = running.filtered(lambda h: h.ir_cron_id.id in idle_cron_ids)
        if stale:
            stale.write({'state': 'interruption', 'ended_at': fields.Datetime.now()})
            stale._notify_dashboard()
            _logger.info('Cron Visualization: %s cron run(s) marked as interrupted', len(stale))
        return stale

    def _register_hook(self):
        # super() is a no-op today, but omitting it breaks any future co-inheritor.
        super()._register_hook()
        self._close_stale_running()

    @api.model
    def _get_retention_days(self):
        value = self.env['ir.config_parameter'].sudo().get_param(RETENTION_PARAM)
        if not value:
            return DEFAULT_RETENTION_DAYS
        try:
            days = int(value)
        except (TypeError, ValueError):
            _logger.warning('Cron Visualization: invalid %s %r, using %s days',
                            RETENTION_PARAM, value, DEFAULT_RETENTION_DAYS)
            return DEFAULT_RETENTION_DAYS
        return days if days > 0 else DEFAULT_RETENTION_DAYS

    def resume(self):
        """ Put a reused row back to 'running' at the top of a new iteration.

        `_run_job` calls `_callback` once per batch of a cron using the progress
        API, and every iteration closes the row so a loop that gives up on its
        time budget leaves nothing stuck. This is the other side of that: without
        it the row stayed 'success' for the rest of the run.
        """
        self.ensure_one()
        if self.state != 'running':
            self.write({'state': 'running', 'ended_at': False})
            self._notify_dashboard()

    def finish(self, success, error=False):
        self.ensure_one()
        now = fields.Datetime.now()
        update = {
            'state': 'success' if success else 'fail',
            'ended_at': now,
            'duration': (now - self.started_at).total_seconds() / 60,
        }
        if error:
            update['error'] = error
        self.write(update)
        self._notify_dashboard()

    def _cv_finish(self, success, error=False):
        """ `finish` on each row of ``self``, none included. """
        for history in self:
            history.finish(success, error)

    @api.autovacuum
    def _gc_history(self):
        """ Delete the history older than the retention period, in bounded passes.

        The retention is 90 days unless the system parameter
        ``cron_visualization.history_retention_days`` says otherwise.

        One unbounded DELETE was fine at steady state and not at all fine the
        first time it ran over a backlog (a cell down for a week, a database
        restored from an old dump): a single long statement holding the lock
        while the cron worker inserts into the same table. The 18
        ``ir.autovacuum`` calls each method once (it has no requeue of a
        ``(done, remaining)`` result), so the passes are looped over here,
        committed one by one like the autovacuum commits between methods.

        The same pass closes the runs left hanging by a killed worker: a registry
        reload is not guaranteed to ever happen on a long-lived instance, and a
        row stuck in 'running' pins `cv_is_running` and its progress bar forever.
        """
        self._close_stale_running()
        done, remaining = self._gc_history_batch()
        while remaining:
            self.env.cr.commit()
            batch_done, remaining = self._gc_history_batch()
            done += batch_done
        return done

    def _gc_history_batch(self):
        """ One pass of `_gc_history`: ``(deleted, remaining)``, ``remaining``
        being 0 when nothing expired is left, 1 otherwise. """
        cutoff = fields.Datetime.now() - datetime.timedelta(days=self._get_retention_days())
        domain = [('create_date', '<', cutoff)]
        expired = self.sudo().search(domain, limit=GC_BATCH_SIZE)
        done = len(expired)
        expired.unlink()
        remaining = self.sudo().search_count(domain, limit=1) if done == GC_BATCH_SIZE else 0
        return done, remaining
