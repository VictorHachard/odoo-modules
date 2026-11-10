from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestListStyleAssets(HttpCase):

    def test_stylesheet_in_backend_bundle(self):
        bundle = self.env['ir.qweb']._get_asset_bundle('web.assets_backend', js=False)
        self.assertIn(
            '/tree_style_border_center/static/src/style.scss',
            [f['url'] for f in bundle.files],
        )

    def test_stylesheet_compiles(self):
        bundle = self.env['ir.qweb']._get_asset_bundle('web.assets_backend', js=False)
        css = bundle.preprocess_css()
        self.assertFalse(bundle.css_errors, '\n'.join(bundle.css_errors))
        self.assertIn('.o_list_renderer .o_list_table thead .o_list_number_th', css)
        self.assertNotIn('$table-border-color', css)

    def test_backend_loads(self):
        self.browser_js('/odoo', "console.log('test successful')", 'odoo.isReady', login='admin')
