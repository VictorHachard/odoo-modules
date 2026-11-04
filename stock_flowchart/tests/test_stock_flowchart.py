# -*- coding: utf-8 -*-

from odoo.tests import TransactionCase, tagged

from odoo.addons.stock_flowchart.tools import mermaid_escape, mermaid_label


@tagged('post_install', '-at_install')
class TestStockFlowchart(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.env.company.id)], limit=1)
        picking_type = warehouse.out_type_id
        Picking = cls.env['stock.picking']
        # root -> (child_a -> grandchild, child_b)
        cls.root = Picking.create({'name': 'ROOT', 'picking_type_id': picking_type.id})
        cls.child_a = Picking.create({
            'name': 'CHILD-A', 'picking_type_id': picking_type.id, 'backorder_id': cls.root.id,
        })
        cls.child_b = Picking.create({
            'name': 'CHILD-B', 'picking_type_id': picking_type.id, 'backorder_id': cls.root.id,
        })
        cls.grandchild = Picking.create({
            'name': 'GRANDCHILD', 'picking_type_id': picking_type.id, 'backorder_id': cls.child_a.id,
        })

    def test_mermaid_escape(self):
        self.assertEqual(mermaid_escape('a"b<c>#d&e\nf'), 'a#quot;b#lt;c#gt;#35;d#amp;e f')
        self.assertEqual(mermaid_escape(False), '')
        self.assertEqual(mermaid_label('x', False, 'y'), '"x<br>y"')

    def test_element_name_escaped(self):
        self.root.name = 'WH/OUT ("x") [y] <b>&'
        element = self.root._get_flowchart_element()
        self.assertTrue(element.startswith(f'sp{self.root.id}("WH/OUT (#quot;x#quot;) [y] #lt;b#gt;#amp; - '))
        self.assertNotIn('<b>', element)

    def test_sub_graph_has_every_branch(self):
        lines = self.root._get_flowchart_sub_graph().splitlines()
        edges = {line.split('(')[0] + ' --> ' + line.split(' --> ')[1].split('(')[0] for line in lines if ' --> ' in line}
        self.assertEqual(edges, {
            f'sp{self.root.id} --> sp{self.child_a.id}',
            f'sp{self.root.id} --> sp{self.child_b.id}',
            f'sp{self.child_a.id} --> sp{self.grandchild.id}',
        })
        for picking in self.root | self.child_a | self.child_b | self.grandchild:
            self.assertEqual(sum(line.startswith(f'click sp{picking.id} ') for line in lines), 1)
        self.assertEqual(lines[-1], 'end')
