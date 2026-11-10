# -*- coding: utf-8 -*-
import itertools
import threading

from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.http import request

# Per-thread bookkeeping of the history row of the run currently executing on
# this cron worker. A run may invoke `_callback` several times (progress API);
# keying on (database, cron_id, run_id) lets every iteration of the same run
# reuse the same history row instead of creating one per iteration. A cron
# worker processes a single job at a time, so one mono-slot per thread is
# enough; the database is part of the key because a cron thread serves every
# database of the server in turn, and the same cron id exists in each of them.
#
# Odoo 18 puts nothing in the context that identifies a run (there is no
# `cron_end_time`), so `_run_job` stamps the thread with a fresh `run_id` for
# the duration of the run. A `_callback` outside of `_run_job` has none and
# always opens a row of its own.
_cron_run = threading.local()
_run_ids = itertools.count(1)


class IrCron(models.Model):
    _inherit = 'ir.cron'

    # History is intentionally not stored on the cron itself: the run records
    # live on cv.ir.cron.history and are committed from the cron worker.
    cv_ir_cron_history_ids = fields.One2many('cv.ir.cron.history', 'ir_cron_id', string='Cron History')
    cv_history_count = fields.Integer(string='History Count', compute='_compute_history_count')

    # `cv_` prefixed like the two fields above: these live on core's `ir.cron`,
    # whose `_inherits` parent is `ir.actions.server`, and a bare `history` or
    # `is_running` is exactly the name a future Odoo version or another cron
    # addon will want. They are all non-stored computes, so the prefix costs
    # nothing today and a collision on a delegated model would cost a migration.
    cv_next_execution_timer = fields.Float(string='Next Execution Timer', compute='_compute_cv_next_execution_timer', help='Time remaining before the next execution')

    cv_is_running = fields.Boolean(string='Is Running', compute='_compute_cv_is_running', search='_search_cv_is_running', help='Is the cron currently running')
    cv_progress_estimated = fields.Char(string='Progress Estimated', compute='_compute_cv_progress_estimated', help='Current progress of the cron (progress;duration;type)')
    cv_history = fields.Char(string='History', compute='_compute_cv_history', help='History of the last 10 runs (state;duration)')

    def _compute_cv_next_execution_timer(self):
        now = fields.Datetime.now()
        for cron in self:
            if cron.nextcall:
                cron.cv_next_execution_timer = (cron.nextcall - now).total_seconds() / 60
            else:
                cron.cv_next_execution_timer = False

    def _compute_history_count(self):
        counts = dict(self.env['cv.ir.cron.history']._read_group(
            [('ir_cron_id', 'in', self.ids)],
            groupby=['ir_cron_id'],
            aggregates=['__count'],
        ))
        for cron in self:
            cron.cv_history_count = counts.get(cron, 0)

    def open_history(self):
        """ Keep in sync with cv_ir_cron_history_action. """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cron History'),
            'res_model': 'cv.ir.cron.history',
            'view_mode': 'list,pivot,graph,calendar,form',
            'domain': [('ir_cron_id', '=', self.id)],
            'context': {'graph_groupbys': ['started_at:day', 'state']},
            'help': _('<p class="o_view_nocontent_smiling_face">No history found!</p>'),
        }

    def _compute_cv_is_running(self):
        """ A cron is running when it has at least one history row in state 'running'. """
        running = self.env['cv.ir.cron.history']._read_group(
            [('ir_cron_id', 'in', self.ids), ('state', '=', 'running')],
            groupby=['ir_cron_id'],
        )
        running_ids = {cron.id for (cron,) in running}
        for cron in self:
            cron.cv_is_running = cron.id in running_ids

    def _search_cv_is_running(self, operator, value):
        # Odoo 18 hands a boolean search over as-is ("=", "!=" with a bool),
        # "in"/"not in" being accepted too for a list of values.
        if operator in ('=', '!='):
            keep = (operator == '=') == bool(value)
        elif operator in ('in', 'not in'):
            keep = (operator == 'in') == (True in value)
        else:
            raise UserError(_('Operation not supported on "Is Running": %s', operator))
        running = self.env['cv.ir.cron.history']._read_group(
            [('state', '=', 'running')],
            groupby=['ir_cron_id'],
        )
        running_ids = [cron.id for (cron,) in running]
        return [('id', 'in' if keep else 'not in', running_ids)]

    def _compute_cv_progress_estimated(self):
        """ Estimate the progress of currently running executions from the
        average duration of the last 10 successful runs.

        One "progress;elapsed_minutes;type" entry per running row, comma
        separated. ``progress`` is a percentage capped at 99 (the run is not
        over until it is), or empty when there is no successful run to
        estimate from. """
        now = fields.Datetime.now()
        self.env['cv.ir.cron.history'].flush_model(['ir_cron_id', 'state', 'duration', 'started_at', 'type'])
        for cron in self:
            if not cron.cv_is_running:
                cron.cv_progress_estimated = False
                continue
            self.env.cr.execute("""
                SELECT AVG(duration) FROM (
                    SELECT duration FROM cv_ir_cron_history
                    WHERE state = 'success' AND ir_cron_id = %s
                    ORDER BY id DESC LIMIT 10
                ) AS recent_success;
            """, (cron.id,))
            average_duration = self.env.cr.fetchone()[0]

            self.env.cr.execute("""
                SELECT started_at, type FROM cv_ir_cron_history
                WHERE state = 'running' AND ir_cron_id = %s
                ORDER BY started_at;
            """, (cron.id,))
            running_rows = self.env.cr.fetchall()
            if not running_rows:
                cron.cv_progress_estimated = False
                continue

            progress_estimated = []
            for started_at, htype in running_rows:
                duration = max(0.0, (now - started_at).total_seconds() / 60)
                if average_duration and average_duration > 0:
                    progress = min(99, round(duration / average_duration * 100, 2))
                else:
                    # No successful run to compare with (first run, or every
                    # previous one failed): there is no estimate to give. An
                    # empty progress tells the widget to draw an indeterminate
                    # bar instead of claiming the run is 99% done from its
                    # first second.
                    progress = ''
                progress_estimated.append('{};{};{}'.format(progress, duration, htype or ''))
            cron.cv_progress_estimated = ','.join(progress_estimated) or False

    def _compute_cv_history(self):
        """ The last 10 runs of each cron, oldest first, as "state;duration".

        Deliberately one windowed query instead of a walk over
        `cv_ir_cron_history_ids`: reading that one2many materialises *every*
        history row of every cron in the recordset (`One2many.read` runs an
        unbounded `search_fetch`), and the kanban lists every cron and recomputes
        this on each bus-driven reload. With 90 days of retention over the
        five-minute crons of a cell that is six figures of rows per refresh.
        """
        self.cv_history = ''
        cron_ids = tuple(self.ids)
        if not cron_ids:
            return
        self.env['cv.ir.cron.history'].flush_model(['ir_cron_id', 'state', 'duration'])
        self.env.cr.execute("""
            SELECT ir_cron_id, state, duration
              FROM (
                SELECT ir_cron_id, state, duration,
                       ROW_NUMBER() OVER (PARTITION BY ir_cron_id ORDER BY id DESC) AS run_rank
                  FROM cv_ir_cron_history
                 WHERE ir_cron_id IN %s
              ) AS ranked
             WHERE run_rank <= 10
             ORDER BY ir_cron_id, run_rank DESC;
        """, (cron_ids,))
        runs = {}
        for cron_id, state, duration in self.env.cr.fetchall():
            # Running and interrupted rows have no duration: send an empty
            # value rather than the string "None".
            runs.setdefault(cron_id, []).append('{};{}'.format(state, '' if duration is None else duration))
        for cron in self:
            cron.cv_history = ','.join(runs.get(cron.id, []))


    @classmethod
    def _run_job(cls, job):
        """ Mark the thread as running one job for the whole batch loop.

        The Odoo 18 ``_run_job`` calls ``_callback`` up to
        ``MAX_BATCH_PER_CRON_JOB`` times on the same job when it uses the
        progress API; the run id set here is what tells `_callback` that those
        calls are one run.
        """
        previous = getattr(_cron_run, 'run_id', None)
        _cron_run.run_id = next(_run_ids)
        try:
            return super()._run_job(job)
        finally:
            _cron_run.run_id = previous

    def _callback(self, cron_name, server_action_id):
        """ Wrap the scheduled execution to record a history row.

        In Odoo 18 only the scheduler goes through ``_callback``: "Run
        Manually" is recorded by `method_direct_trigger` below. The run type is
        still derived from the presence of an HTTP request, so a ``_callback``
        that some other module calls from a request is recorded as manual.

        A run using the progress API makes ``_run_job`` call ``_callback``
        several times; all iterations of the same run (identified by the run
        id `_run_job` puts on the thread) reuse a single history row rather
        than creating one per iteration. Each iteration closes the row (so the
        loop stopping after its last batch, or the worker dying, never leaves a
        row stuck in 'running'), and the next one puts it back to 'running'.
        Without that reset the row read 'success' from the end of the first
        batch onwards and the spinner, the progress bar and the "Running"
        filter all went dark on exactly the long batch crons this dashboard
        exists to watch.
        """
        self.ensure_one()
        History = self.env['cv.ir.cron.history'].sudo()
        run_id = getattr(_cron_run, 'run_id', None)
        run_key = (self.env.cr.dbname, self.env.context.get('cron_id'), run_id)

        history = History
        if run_id is not None and getattr(_cron_run, 'key', None) == run_key:
            history = History.browse(getattr(_cron_run, 'history_id', None)).exists()
            if history.ir_cron_id != self:
                history = History
        if history:
            history.resume()
        else:
            history = History.create({
                'ir_cron_id': self.id,
                # `_run_job` builds its environment on the cron's Scheduler User,
                # so `self.env.user` is never the operator of a request. The
                # session user is on the request.
                'user_id': request.env.user.id if request else self.env.user.id,
                'type': 'manual' if request else 'automatic',
            })
            if run_id is not None:
                _cron_run.key = run_key
                _cron_run.history_id = history.id
        # Commit so the 'running' row (and its bus notification) is visible
        # immediately and survives a rollback of the server action below.
        self.env.cr.commit()

        try:
            super()._callback(cron_name, server_action_id)
        except Exception as e:
            # super() already rolled the cursor back; record the failure.
            history.finish(False, str(e) or repr(e))
            self.env.cr.commit()
            raise
        else:
            # The 18 `_callback` does not commit itself (`_run_job` does, right
            # after): commit the server action together with the
            # running -> success transition and its bus notification.
            history.finish(True)
            self.env.cr.commit()

    def method_direct_trigger(self):
        """ Record the "Run Manually" runs.

        Odoo 18 runs them right in the HTTP transaction, without
        ``_process_job`` nor ``_callback``, so the history row lives in
        transactions of its own: one that shows it 'running' while the action
        runs, one that closes it, which a failing action rolling the request
        back cannot undo. The checks of core come first so that a refused
        trigger (no access, cron already running) records nothing.

        The request transaction keeps the lock `_try_lock` takes on the cron
        until it ends, which keeps `_close_stale_running` off the row in the
        meantime. Inserting a row that references the locked cron does not
        wait on that lock (``FOR KEY SHARE`` against ``FOR NO KEY UPDATE``).
        """
        self.ensure_one()
        self.browse().check_access('write')
        self._try_lock()
        operator_id = self.env.uid
        history_id = self._cv_history_out_of_band(lambda History: History.create({
            'ir_cron_id': self.id,
            'user_id': operator_id,
            'type': 'manual',
        }).id)
        try:
            result = super().method_direct_trigger()
        except Exception as e:
            error = str(e) or repr(e)
            self._cv_history_out_of_band(lambda History: History.browse(history_id).exists()._cv_finish(False, error))
            raise
        self._cv_history_out_of_band(lambda History: History.browse(history_id).exists()._cv_finish(True))
        return result

    def _cv_history_out_of_band(self, callback):
        """ Call ``callback(History)`` in a transaction of its own, committed
        on return, ``History`` being the superuser history model. """
        with self.env.registry.cursor() as cr:
            return callback(self.env(cr=cr, su=True)['cv.ir.cron.history'])
