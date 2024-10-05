# -*- coding: utf-8 -*-

from collections import defaultdict

from odoo import api, models, fields, _
from odoo.models import NewId


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _get_flowchart_sub_graph(self, i18n=None, menu_id=None):
        self.ensure_one()
        if not i18n:
            i18n = dict(self.env['stock.picking'].fields_get(allfields=['state'])['state']['selection'])
        if not menu_id:
            menu_id = self.env.ref('stock.menu_stock_root').id
        click_done = []
        flowchart = [f'subgraph sub{self.id} [" "]', 'direction LR']
        # Add all backorder parent recursively
        backorder = self
        while backorder.backorder_id:
            flowchart.append(f'{backorder.backorder_id._get_flowchart_element(i18n)} --> {backorder._get_flowchart_element(i18n)}')
            if backorder.backorder_id.id not in click_done:
                flowchart.append(backorder.backorder_id._get_flowchart_click(menu_id))
                click_done.append(backorder.backorder_id.id)
            if backorder.id not in click_done:
                flowchart.append(backorder._get_flowchart_click(menu_id))
                click_done.append(backorder.id)
            backorder = backorder.backorder_id
        # Add all backorder child recursively
        backorder = self
        while backorder.backorder_ids:
            for back in backorder.backorder_ids:
                flowchart.append(f'{backorder._get_flowchart_element(i18n)} --> {back._get_flowchart_element(i18n)}')
                if backorder.id not in click_done:
                    flowchart.append(backorder._get_flowchart_click(menu_id))
                    click_done.append(backorder.id)
                if back.id not in click_done:
                    flowchart.append(back._get_flowchart_click(menu_id))
                    click_done.append(back.id)
                backorder = back
        flowchart.append('end')
        return '\n'.join(flowchart)

    def _get_picking_hierarchy(self):
        parent_dict = defaultdict(list)

        # Creating a dictionary with parent picking as key and list of child pickings as value
        for picking in self:
            if picking.backorder_id:
                _id = picking.backorder_id._origin.id if isinstance(picking.backorder_id.id, NewId) else picking.backorder_id.id
                parent_dict[_id].append(picking)

        # Function to recursively get all child pickings
        def get_children(parent_id):
            children = parent_dict.get(parent_id, [])
            all_children = []
            for child in children:
                _id = child._origin.id if isinstance(child.id, NewId) else child.id
                all_children.append(child)
                all_children.extend(get_children(_id))
            return all_children

        # Generate the final list of lists
        picking_hierarchy = []
        for picking in self:
            if not picking.backorder_id:  # Only start with parent pickings
                _id = picking._origin.id if isinstance(picking.id, NewId) else picking.id
                hierarchy = [picking]
                hierarchy.extend(get_children(_id))
                picking_hierarchy.append(hierarchy)

        return picking_hierarchy

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
        state = self._get_flowchart_state_color().get(self.state)
        return f'sp{self.id}({self.name} - {_(i18n[self.state])}):::{state}'

    def _get_flowchart_click(self, menu_id=None):
        self.ensure_one()
        if not menu_id:
            menu_id = self.env.ref('stock.menu_stock_root').id
        _id = self._origin.id if isinstance(self.id, NewId) else self.id
        return f'click sp{self.id} "/web#id={_id}&model=stock.picking&view_type=form&menu_id={menu_id}" _blank'