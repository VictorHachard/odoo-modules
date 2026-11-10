from lxml import html

from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestBreadcrumbName(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env.ref('base.default_website')
        cls.product = cls.env['product.template'].create({
            'name': 'Breadcrumb Test Product',
            'list_price': 10.0,
            'sale_ok': True,
            'website_published': True,
            'website_id': cls.website.id,
        })

    def _breadcrumb_items(self):
        response = self.url_open(self.product.website_url)
        self.assertEqual(response.status_code, 200)
        tree = html.fromstring(response.content)
        breadcrumb = tree.xpath("//ol[contains(@class, 'o_wsale_breadcrumb')]")
        self.assertEqual(len(breadcrumb), 1)
        return breadcrumb[0], breadcrumb[0].xpath('./li')

    def test_default_breadcrumb(self):
        _breadcrumb, items = self._breadcrumb_items()
        self.assertEqual(items[0].text_content().strip(), 'All products')

    def test_custom_breadcrumb(self):
        self.website.breadcrumb_name = 'Our Catalogue'
        breadcrumb, items = self._breadcrumb_items()
        # The desktop link and the mobile "back" link (no category) both use it.
        self.assertEqual(items[0].text_content().strip(), 'Our Catalogue')
        self.assertEqual(items[-1].text_content().strip(), 'Our Catalogue')
        self.assertNotIn('All products', breadcrumb.text_content())
        # The link itself still points to the shop.
        self.assertTrue(items[0].xpath('./a')[0].get('href').startswith('/shop'))

    def test_custom_breadcrumb_is_escaped(self):
        self.website.breadcrumb_name = '<script>alert(1)</script>'
        response = self.url_open(self.product.website_url)
        self.assertNotIn(b'<script>alert(1)</script>', response.content)
        self.assertIn(b'&lt;script&gt;alert(1)&lt;/script&gt;', response.content)

    def test_breadcrumb_is_website_specific(self):
        other = self.env['website'].create({'name': 'Other Website'})
        other.breadcrumb_name = 'Elsewhere'
        _breadcrumb, items = self._breadcrumb_items()
        self.assertEqual(items[0].text_content().strip(), 'All products')

    def test_settings_write_current_website(self):
        settings = self.env['res.config.settings'].create({
            'website_id': self.website.id,
            'breadcrumb_name': 'From Settings',
        })
        settings.execute()
        self.assertEqual(self.website.breadcrumb_name, 'From Settings')

    def test_settings_view_renders(self):
        arch = self.env['res.config.settings'].get_views([(False, 'form')])['views']['form']['arch']
        self.assertIn('name="breadcrumb_name"', arch)
