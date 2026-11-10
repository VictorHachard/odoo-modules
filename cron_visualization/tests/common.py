from contextlib import contextmanager
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.sql_db import db_connect
from odoo.tests import TransactionCase

from ..model.cv_ir_cron_history import CRON_BUS_CHANNEL, CRON_BUS_NOTIFICATION


class CronHistoryCase(TransactionCase):
    """Two throwaway crons and helpers to write their run history."""

    NOTIFICATION = CRON_BUS_NOTIFICATION

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        model = cls.env['ir.model']._get('res.partner')
        cls.cron = cls._make_cron('CV test cron', model)
        cls.other_cron = cls._make_cron('CV other cron', model)
        cls.History = cls.env['cv.ir.cron.history']

    @classmethod
    def _make_cron(cls, name, model, code='pass'):
        return cls.env['ir.cron'].create({
            'name': name,
            'model_id': model.id,
            'state': 'code',
            'code': code,
            'interval_number': 1,
            'interval_type': 'hours',
            'nextcall': fields.Datetime.now() + timedelta(hours=1),
            'active': False,
        })

    def _run(self, cron=None, state='success', duration=1.0, started_ago=None, **vals):
        """Create one history row directly, bypassing the callback."""
        row = self.History.create({
            'ir_cron_id': (cron or self.cron).id,
            'type': 'automatic',
            **vals,
        })
        write = {'state': state, 'duration': duration}
        if started_ago is not None:
            write['started_at'] = fields.Datetime.now() - started_ago
        row.write(write)
        return row

    def _backdate_create(self, rows, delta):
        self.env.flush_all()
        self.env.cr.execute(
            'UPDATE cv_ir_cron_history SET create_date = %s WHERE id IN %s',
            [fields.Datetime.now() - delta, tuple(rows.ids)],
        )
        rows.invalidate_recordset()

    @contextmanager
    def _capture_bus(self):
        sent = []
        BusBus = type(self.env['bus.bus'])
        original = BusBus._sendone

        def spy(bus, target, notification_type, message):
            if target == CRON_BUS_CHANNEL:
                sent.append((notification_type, message))
                return None
            return original(bus, target, notification_type, message)

        with patch.object(BusBus, '_sendone', spy):
            yield sent

    @contextmanager
    def _held_by_another_worker(self, cron):
        """Hold the row lock a cron worker holds on `cron` while running it.

        Taken from a second, real connection, exactly like `_acquire_one_job`
        does it, so the test transaction sees what a sibling worker would
        leave. Only committed crons are visible there: use a data cron.
        """
        cr = db_connect(self.env.cr.dbname).cursor()
        try:
            cr.execute('SELECT id FROM ir_cron WHERE id = %s FOR NO KEY UPDATE', [cron.id])
            self.assertEqual(cr.fetchone(), (cron.id,))
            yield
        finally:
            cr.rollback()
            cr.close()
