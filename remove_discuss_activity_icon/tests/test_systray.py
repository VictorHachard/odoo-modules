from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestSystray(HttpCase):

    def test_assets_registered(self):
        backend = self.env['ir.qweb']._get_asset_bundle('web.assets_backend', css=False)
        self.assertIn(
            '/remove_discuss_activity_icon/static/src/systray.js',
            [f['url'] for f in backend.files],
        )

    def test_systray_icons_removed(self):
        self.start_tour('/odoo', 'remove_discuss_activity_icon_tour', login='admin')

    def test_discuss_app_still_loads(self):
        self.start_tour('/odoo/discuss', 'remove_discuss_activity_icon_tour', login='admin')
