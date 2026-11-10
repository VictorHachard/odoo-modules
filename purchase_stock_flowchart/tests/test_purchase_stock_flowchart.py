# -*- coding: utf-8 -*-

from odoo.tests import Form, HttpCase, TransactionCase, new_test_user, tagged

# Opens the "Stock Flowchart" tab and waits for Mermaid to draw the chart.
CHECK_FLOWCHART_JS = """
const deadline = Date.now() + 30000;
(function check() {
    const tab = document.querySelector('.o_notebook_headers [name="stock_flowchart"]');
    const error = document.querySelector('.o_form_field_mermaid_error');
    const nodes = document.querySelectorAll('.o_form_field_mermaid svg .node');
    if (error) {
        console.error('Mermaid error: ' + error.textContent);
    } else if (nodes.length >= %(nodes)d) {
        console.log('test successful');
    } else if (Date.now() > deadline) {
        console.error('The flowchart was not drawn');
    } else {
        if (tab && !tab.classList.contains('active')) {
            tab.click();
        }
        setTimeout(check, 200);
    }
})();
"""


class PurchaseStockFlowchartCommon:

    @classmethod
    def _setup_purchase(cls):
        cls.partner = cls.env['res.partner'].create({'name': 'Vendor "Quote" <b>'})
        cls.product = cls.env['product.product'].create({'name': 'Flowchart Product', 'type': 'consu'})
        cls.order = cls._create_order(2)
        cls.picking = cls.order.picking_ids
        cls.picking.move_ids.quantity = 1
        cls.picking.with_context(skip_backorder=True).button_validate()
        cls.backorder = cls.order.picking_ids - cls.picking

    @classmethod
    def _create_order(cls, qty):
        order = cls.env['purchase.order'].create({
            'partner_id': cls.partner.id,
            'order_line': [(0, 0, {'product_id': cls.product.id, 'product_qty': qty})],
        })
        order.button_confirm()
        return order


@tagged('post_install', '-at_install')
class TestPurchaseStockFlowchart(PurchaseStockFlowchartCommon, TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_purchase()

    def test_flowchart_without_picking(self):
        order = self.env['purchase.order'].create({'partner_id': self.partner.id})
        lines = order.flowchart.splitlines()
        self.assertEqual(lines[0], 'graph TB')
        self.assertIn(f'click po{order.id} "/odoo/purchase.order/{order.id}" _blank', lines)
        self.assertNotIn('-->', order.flowchart)
        self.assertTrue(any(line.startswith(f'po{order.id}("') for line in lines))

    def test_flowchart_with_single_picking(self):
        order = self._create_order(1)
        picking = order.picking_ids
        self.assertEqual(len(picking), 1)
        flowchart = order.flowchart
        self.assertIn(f'po{order.id} --> sp{picking.id}("', flowchart)
        self.assertIn(f'click sp{picking.id} "/odoo/stock.picking/{picking.id}" _blank', flowchart)
        self.assertNotIn('subgraph', flowchart)

    def test_flowchart_with_backorder(self):
        self.assertEqual(self.backorder.backorder_id, self.picking)
        flowchart = self.order.flowchart
        self.assertIn(f'subgraph subsp{self.picking.id} [" "]', flowchart)
        self.assertIn(f'po{self.order.id} --> subsp{self.picking.id}', flowchart)
        self.assertIn(f'sp{self.picking.id} --> sp{self.backorder.id}', flowchart)
        self.assertIn(f'po{self.order.id}("', flowchart)
        self.assertIn('):::bg-success-light', flowchart)

    def test_state_label_is_translated_selection(self):
        state = dict(self.env['purchase.order'].fields_get(allfields=['state'])['state']['selection'])['purchase']
        self.assertIn(f'{self.order.name} - {state}', self.order.flowchart)

    def test_more_info_escapes_partner(self):
        graph = self.order._get_purchase_picking_flowchart_graph(more_info=True)
        self.assertIn('<br>Vendor #quot;Quote#quot; #lt;b#gt;"', graph)
        self.assertNotIn('<b>', graph)

    def test_new_record(self):
        """The onchange copy of an order must not leak NewId reprs in the chart."""
        order = self.env['purchase.order'].new({'partner_id': self.partner.id})
        self.assertNotIn('NewId', order.flowchart)
        self.assertNotIn('click', order.flowchart)
        form = Form(self.order)
        self.assertNotIn('NewId', form.flowchart or '')

    def test_purchase_user_can_read_flowchart(self):
        user = new_test_user(self.env, 'flow_buyer', groups='purchase.group_purchase_user')
        flowchart = self.order.with_user(user).flowchart
        self.assertIn(f'sp{self.backorder.id}', flowchart)


@tagged('post_install', '-at_install')
class TestPurchaseStockFlowchartBrowser(PurchaseStockFlowchartCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_purchase()

    def test_flowchart_is_drawn(self):
        self.browser_js(
            f'/odoo/purchase.order/{self.order.id}',
            CHECK_FLOWCHART_JS % {'nodes': 3},
            'odoo.isReady === true',
            login='admin',
        )
