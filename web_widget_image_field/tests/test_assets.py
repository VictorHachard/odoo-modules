# -*- coding: utf-8 -*-

from odoo.tests import TransactionCase, tagged

MODULE = 'web_widget_image_field'


@tagged('post_install', '-at_install')
class TestImageFieldAssets(TransactionCase):

    def test_widget_in_backend_bundle(self):
        Asset = self.env['ir.asset']
        paths = [path.lstrip('/') for path, *_rest in Asset._get_asset_paths('web.assets_backend', Asset._get_asset_params())]
        self.assertIn(f'{MODULE}/static/src/many2one_image_field/many2one_image_field.js', paths)
        self.assertIn(f'{MODULE}/static/src/many2one_image_field/many2one_image_field.xml', paths)
