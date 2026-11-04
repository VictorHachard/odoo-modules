# -*- coding: utf-8 -*-

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestFlowchart(TransactionCase):

    def test_names_escaped(self):
        partner = self.env['res.partner'].create({'name': 'Evil "Corp") <img src=x onerror=alert(1)> & co'})
        order = self.env['sale.order'].create({'partner_id': partner.id})
        order.name = 'ORD"1") --> X[<b>'
        element = order._get_flowchart_element(more_info=True)
        self.assertTrue(element.startswith(f'so{order.id}("ORD#quot;1#quot;) --#gt; X[#lt;b#gt; - '), element)
        self.assertIn('<br>Evil #quot;Corp#quot;) #lt;img src=x onerror=alert(1)#gt; #amp; co"):::', element)
        self.assertNotIn('<img', element)
        order.invalidate_recordset(['flowchart'])
        self.assertNotIn('<b>', order.flowchart)
        self.assertIn('ORD#quot;1#quot;', order._get_sale_picking_flowchart_graph())
