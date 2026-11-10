# -*- coding: utf-8 -*-

from odoo.tests import TransactionCase, tagged

from odoo.addons.stock_flowchart.tools import mermaid_click, mermaid_escape, mermaid_label, mermaid_node_id


@tagged('post_install', '-at_install')
class TestStockFlowchart(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.env.company.id)], limit=1)
        cls.picking_type = warehouse.out_type_id
        Picking = cls.env['stock.picking']
        # root -> (child_a -> grandchild, child_b)
        cls.root = Picking.create({'name': 'ROOT', 'picking_type_id': cls.picking_type.id})
        cls.child_a = Picking.create({
            'name': 'CHILD-A', 'picking_type_id': cls.picking_type.id, 'backorder_id': cls.root.id,
        })
        cls.child_b = Picking.create({
            'name': 'CHILD-B', 'picking_type_id': cls.picking_type.id, 'backorder_id': cls.root.id,
        })
        cls.grandchild = Picking.create({
            'name': 'GRANDCHILD', 'picking_type_id': cls.picking_type.id, 'backorder_id': cls.child_a.id,
        })
        cls.lonely = Picking.create({'name': 'LONELY', 'picking_type_id': cls.picking_type.id})
        cls.all_pickings = cls.root | cls.child_a | cls.child_b | cls.grandchild | cls.lonely

    def test_mermaid_escape(self):
        self.assertEqual(mermaid_escape('a"b<c>#d\ne'), 'a#quot;b#lt;c#gt;#35;d e')
        self.assertEqual(mermaid_escape(False), '')
        self.assertEqual(mermaid_label('x', False, 'y'), '"x<br>y"')

    def test_node_id_and_click(self):
        self.assertEqual(mermaid_node_id('sp', self.root), f'sp{self.root.id}')
        self.assertEqual(
            mermaid_click('sp', self.root),
            f'click sp{self.root.id} "/odoo/stock.picking/{self.root.id}" _blank',
        )
        new_from_db = self.root.new(origin=self.root)
        self.assertEqual(mermaid_node_id('sp', new_from_db), f'sp{self.root.id}')
        brand_new = self.env['stock.picking'].new({'name': 'NEW'})
        self.assertRegex(mermaid_node_id('sp', brand_new), r'^spnew\d+$')
        self.assertEqual(mermaid_click('sp', brand_new), '')

    def test_hierarchy_groups_backorder_chains(self):
        hierarchy = self.all_pickings._get_picking_hierarchy()
        self.assertEqual(len(hierarchy), 2)
        chains = {chain[0]: chain for chain in hierarchy}
        self.assertEqual(set(chains), {self.root, self.lonely})
        self.assertEqual(
            set(chains[self.root]), {self.root, self.child_a, self.child_b, self.grandchild},
        )
        self.assertEqual(len(chains[self.root]), 4)
        self.assertEqual(chains[self.lonely], [self.lonely])

    def test_hierarchy_keeps_orphans(self):
        """A backorder whose parent is not in the set still gets a chain."""
        hierarchy = (self.child_a | self.grandchild)._get_picking_hierarchy()
        self.assertEqual(hierarchy, [[self.child_a, self.grandchild]])
        self.assertEqual(self.grandchild._get_picking_hierarchy(), [[self.grandchild]])

    def test_hierarchy_empty(self):
        self.assertEqual(self.env['stock.picking']._get_picking_hierarchy(), [])

    def test_sub_graph_has_every_branch(self):
        graph = self.root._get_flowchart_sub_graph()
        lines = graph.splitlines()
        self.assertEqual(lines[0], f'subgraph subsp{self.root.id} [" "]')
        for parent, child in [
            (self.root, self.child_a), (self.root, self.child_b), (self.child_a, self.grandchild),
        ]:
            self.assertIn(f'sp{parent.id} --> sp{child.id}', lines)
        for picking in self.root | self.child_a | self.child_b | self.grandchild:
            self.assertEqual(graph.count(f'click sp{picking.id} '), 1)
            self.assertEqual(graph.count(f'sp{picking.id}("'), 1)
        self.assertNotIn(f'sp{self.lonely.id}', graph)
        self.assertIn('end', lines)

    def test_sub_graph_includes_ancestors(self):
        graph = self.grandchild._get_flowchart_sub_graph()
        self.assertIn(f'sp{self.root.id} --> sp{self.child_a.id}', graph)
        self.assertIn(f'sp{self.child_a.id} --> sp{self.grandchild.id}', graph)

    def test_element_is_escaped(self):
        picking = self.env['stock.picking'].create({
            'name': 'WH/OUT/"1") <img src=x onerror=alert(1)>', 'picking_type_id': self.picking_type.id,
        })
        element = picking._get_flowchart_element()
        state = picking._get_flowchart_i18n()[picking.state]
        self.assertEqual(
            element,
            f'sp{picking.id}("WH/OUT/#quot;1#quot;) #lt;img src=x onerror=alert(1)#gt; - {state}"):::bg-grey-light',
        )
