from lxml import html

from odoo.tests import HttpCase, tagged
from odoo.tests.common import JsonRpcException

from odoo.addons.website_sale_stock.tests.common import WebsiteSaleStockCommon


@tagged('post_install', '-at_install')
class TestBackInStockToggle(WebsiteSaleStockCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.notified = cls._create_product(name="Notified Product")
        cls.silent = cls._create_product(name="Silent Product", out_of_stock_back_in_stock_message=False)

    def _cta(self, product):
        response = self.url_open(product.website_url)
        self.assertEqual(response.status_code, 200)
        return html.fromstring(response.content)

    def test_default_is_enabled(self):
        self.assertTrue(self.notified.out_of_stock_back_in_stock_message)
        self.assertTrue(self.notified._can_add_to_stock_notifications())
        self.assertFalse(self.silent._can_add_to_stock_notifications())

    def test_product_page_markup(self):
        tree = self._cta(self.notified)
        self.assertTrue(tree.xpath("//button[@id='stock_notification_button']"))
        self.assertTrue(tree.xpath("//div[@id='stock_notification_wrapper']"))

        tree = self._cta(self.silent)
        self.assertFalse(tree.xpath("//div[@id='out_of_stock_buttons_wrapper']"))
        self.assertFalse(tree.xpath("//button[@id='stock_notification_button']"))
        self.assertFalse(tree.xpath("//div[@id='stock_notification_wrapper']"))
        # The rest of the call-to-action block is untouched.
        self.assertTrue(tree.xpath("//div[@id='add_to_cart_wrap']"))

    def test_subscribe_tour_enabled(self):
        self.start_tour(
            self.notified.website_url, 'website_sale_stock.subscribe_to_stock_notification'
        )
        partner = self.env['mail.thread']._partner_find_from_emails_single(
            ['test@test.test'], no_create=True
        )
        self.assertTrue(self.notified._has_stock_notification(partner, self.website))

    def test_no_button_tour_disabled(self):
        self.start_tour(self.silent.website_url, 'website_sale_stock_notification.disabled')

    def test_subscribe_route_refused_when_disabled(self):
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request('/shop/add/stock_notification', {
                'product_id': self.silent.id,
                'email': 'sneaky@test.test',
            })
        self.assertFalse(self.env['product.stock.notification'].sudo().search([
            ('product_id', '=', self.silent.id),
        ]))

    def test_subscribe_route_accepted_when_enabled(self):
        self.make_jsonrpc_request('/shop/add/stock_notification', {
            'product_id': self.notified.id,
            'email': 'client@test.test',
        })
        self.assertTrue(self.env['product.stock.notification'].sudo().search([
            ('product_id', '=', self.notified.id),
        ]))

    def test_settings_default(self):
        settings = self.env['res.config.settings'].sudo().create({})
        self.assertTrue(settings.default_out_of_stock_back_in_stock_message)

        settings.default_out_of_stock_back_in_stock_message = False
        settings.execute()
        self.assertFalse(
            self.env['res.config.settings'].sudo().create({}).default_out_of_stock_back_in_stock_message
        )
        self.assertFalse(self._create_product(name="New Product").out_of_stock_back_in_stock_message)

        settings = self.env['res.config.settings'].sudo().create({})
        settings.default_out_of_stock_back_in_stock_message = True
        settings.execute()
        self.assertTrue(self._create_product(name="Newer Product").out_of_stock_back_in_stock_message)

    def test_backend_views_render(self):
        product_arch = self.env['product.template'].sudo().get_views([(False, 'form')])['views']['form']['arch']
        self.assertIn('name="out_of_stock_back_in_stock_message"', product_arch)
        admin = self.env.ref('base.user_admin')
        settings_arch = self.env['res.config.settings'].with_user(admin).get_views([(False, 'form')])['views']['form']['arch']
        self.assertIn('name="default_out_of_stock_back_in_stock_message"', settings_arch)
