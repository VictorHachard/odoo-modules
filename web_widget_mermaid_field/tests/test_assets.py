# -*- coding: utf-8 -*-

from odoo.tests import HttpCase, tagged

MODULE = 'web_widget_mermaid_field'


@tagged('post_install', '-at_install')
class TestMermaidAssets(HttpCase):

    def _bundle_paths(self, bundle):
        Asset = self.env['ir.asset']
        return [path.lstrip('/') for path, *_rest in Asset._get_asset_paths(bundle, Asset._get_asset_params())]

    def test_widget_in_backend_bundle(self):
        paths = self._bundle_paths('web.assets_backend')
        self.assertIn(f'{MODULE}/static/src/js/web_widget_mermaid.js', paths)
        self.assertIn(f'{MODULE}/static/src/xml/mermaid_field.xml', paths)
        # The library is only loaded lazily, when a widget is shown.
        self.assertNotIn(f'{MODULE}/static/src/js/mermaid_10_9_1.js', paths)

    def test_lazy_library_bundle_is_served(self):
        """The bundle the widget loads resolves to a script defining ``mermaid``."""
        self.assertEqual(
            self._bundle_paths(f'{MODULE}.mermaid_lib'), [f'{MODULE}/static/src/js/mermaid_10_9_1.js'],
        )
        self.authenticate('admin', 'admin')
        response = self.url_open(f'/web/bundle/{MODULE}.mermaid_lib')
        response.raise_for_status()
        scripts = [asset['src'] for asset in response.json() if asset.get('type') == 'script']
        self.assertEqual(len(scripts), 1)
        script = self.url_open(scripts[0])
        script.raise_for_status()
        self.assertIn('mermaid', script.text)
