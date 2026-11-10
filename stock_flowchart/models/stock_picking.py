# -*- coding: utf-8 -*-

from collections import defaultdict

from odoo import models

from odoo.addons.stock_flowchart.tools import mermaid_click, mermaid_label, mermaid_node_id


def _key(record):
    """Identity of a record that is the same for a record and its onchange copy."""
    return record._origin.id or record.id


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _get_flowchart_node_id(self):
        return mermaid_node_id('sp', self)

    def _get_flowchart_sub_graph(self, i18n=None):
        """Subgraph of the backorder chain of this picking.

        It holds the backorder ancestors of the picking and its whole tree of
        backorders, every branch included.
        """
        self.ensure_one()
        if not i18n:
            i18n = self._get_flowchart_i18n()
        nodes = self.browse()
        edges = []
        child, parent = self, self.backorder_id
        while parent and parent not in nodes:
            edges.insert(0, (parent, child))
            nodes |= parent
            child, parent = parent, parent.backorder_id
        nodes |= self
        stack = [self]
        while stack:
            picking = stack.pop()
            for backorder in picking.backorder_ids:
                if backorder in nodes:
                    continue
                edges.append((picking, backorder))
                nodes |= backorder
                stack.append(backorder)

        flowchart = [f'subgraph sub{self._get_flowchart_node_id()} [" "]', 'direction LR']
        flowchart += [picking._get_flowchart_element(i18n) for picking in nodes]
        flowchart += [
            f'{parent._get_flowchart_node_id()} --> {child._get_flowchart_node_id()}'
            for parent, child in edges
        ]
        flowchart.append('end')
        flowchart += [click for click in (picking._get_flowchart_click() for picking in nodes) if click]
        return '\n'.join(flowchart)

    def _get_picking_hierarchy(self):
        """Group the pickings of ``self`` by backorder chain.

        Return one list per chain: its first picking, then its backorders, depth
        first. A picking whose backorder parent is not in ``self`` starts a chain
        of its own, so that no picking of ``self`` is left out.
        """
        keys = {_key(picking) for picking in self}
        children = defaultdict(list)
        roots = []
        for picking in self:
            parent = picking.backorder_id
            if parent and _key(parent) in keys and _key(parent) != _key(picking):
                children[_key(parent)].append(picking)
            else:
                roots.append(picking)

        def walk(picking, seen):
            seen.add(_key(picking))
            result = [picking]
            for child in children[_key(picking)]:
                if _key(child) not in seen:
                    result += walk(child, seen)
            return result

        return [walk(root, set()) for root in roots]

    def _get_flowchart_state_color(self):
        return {
            'draft': 'bg-grey-light',
            'waiting': 'bg-info-light',
            'confirmed': 'bg-warning-light',
            'assigned': 'bg-info-light',
            'done': 'bg-success-light',
            'cancel': 'bg-danger-light',
        }

    def _get_flowchart_i18n(self):
        return dict(self.env[self._name].fields_get(allfields=['state'])['state']['selection'])

    def _get_flowchart_element(self, i18n=None):
        self.ensure_one()
        if not i18n:
            i18n = self._get_flowchart_i18n()
        state_class = self._get_flowchart_state_color().get(self.state, 'bg-grey-light')
        label = mermaid_label(f"{self.name or '/'} - {i18n.get(self.state, self.state or '')}")
        return f'{self._get_flowchart_node_id()}({label}):::{state_class}'

    def _get_flowchart_click(self):
        self.ensure_one()
        return mermaid_click('sp', self)
