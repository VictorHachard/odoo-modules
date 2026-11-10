# -*- coding: utf-8 -*-
import base64
import io
import zipfile

from odoo.tests import TransactionCase


class IERCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Tag = cls.env['res.partner.category']
        cls.parent_tag = cls.Tag.create({'name': 'IER Parent'})
        cls.tags = cls.Tag.create([
            {'name': 'IER Alpha', 'color': 1, 'parent_id': cls.parent_tag.id},
            {'name': 'IER Beta', 'color': 2},
        ])
        cls.tag_export = cls.env['ir.exports'].create({
            'name': 'IER tags',
            'resource': 'res.partner.category',
            'export_fields': [(0, 0, {'name': name}) for name in ('id', 'name', 'color', 'parent_id/id')],
        })
        cls.template = cls.env['ier.template'].create({
            'name': 'IER test template',
            'lines': [(0, 0, {
                'sequence': 1,
                'ir_exports_id': cls.tag_export.id,
                'mode': 'easy',
                'filter_domain': "[('name', 'ilike', 'IER ')]",
            })],
        })
        cls.line = cls.template.lines

    @staticmethod
    def _read_zip(content):
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            return {name: archive.read(name).decode() for name in archive.namelist()}

    def _make_wizard(self, content, **values):
        return self.env['ier.import.wizard'].create({
            'zip_file': base64.b64encode(content).decode(),
            'zip_file_name': 'test.zip',
            **values,
        })
