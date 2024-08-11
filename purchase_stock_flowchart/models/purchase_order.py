# -*- coding: utf-8 -*-

from odoo import api, models, fields, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    flowchart = fields.Text('Flowchart', compute='_compute_flowchart')

    @api.depends('state', 'picking_ids.state', 'picking_ids.backorder_id', 'picking_ids.backorder_ids')
    def _compute_flowchart(self):
        for rec in self:
            flowchart = [
                'graph TB',
                rec._get_flowchart_style(),
                rec._get_purchase_picking_flowchart_graph()
            ]
            rec.flowchart = '\n'.join(flowchart)

    def _get_purchase_picking_flowchart_graph(self, more_info=False):
        self.ensure_one()
        flowchart = [
            self._get_flowchart_element(more_info=more_info),
            self._get_flowchart_click()
        ]
        i18n, menu_id = None, None
        if self.picking_ids:
            i18n = dict(self.env['stock.picking'].fields_get(allfields=['state'])['state']['selection'])
            menu_id = self.env.ref('stock.menu_stock_root').id
        for hierarchy in self.picking_ids._get_picking_hierarchy():
            if len(hierarchy) > 1:
                flowchart.append(hierarchy[0]._get_flowchart_sub_graph(i18n, menu_id))
                flowchart.append(f'po{self.id} --> sub{hierarchy[0].id}')
            elif len(hierarchy) == 1:
                flowchart.append(f'po{self.id} --> {hierarchy[0]._get_flowchart_element(i18n)}')
                flowchart.append(hierarchy[0]._get_flowchart_click(menu_id))
        return '\n'.join(flowchart)

    def _get_flowchart_style(self):
        return """
        classDef bg-info-light fill:#17a2b880,color:black,stroke:unset;
        classDef bg-success-light fill:#28a74580,color:black,stroke:unset;
        classDef bg-warning-light fill:#ffac0080,color:black,stroke:unset;
        classDef bg-danger-light fill:#dc354580,color:black,stroke:unset;
        classDef bg-grey-light fill:#d3d3d380,color:black,stroke:unset;
        """

    def _get_flowchart_state_color(self):
        return {
            'draft': 'bg-info-light',
            'sent': 'bg-info-light',
            'to approve': 'bg-info-light',
            'purchase': 'bg-success-light',
            'done': 'bg-success-light',
            'cancel': 'bg-danger-light',
        }

    def _get_flowchart_i18n(self):
        return dict(self.env[self._name].fields_get(allfields=['state'])['state']['selection'])

    def _get_flowchart_element(self, i18n=None, more_info=False):
        self.ensure_one()
        if not i18n:
            i18n = self._get_flowchart_i18n()
        state = self._get_flowchart_state_color().get(self.state)
        if more_info:
            return f'po{self.id}("{self.name} - {_(i18n[self.state])}\n{self.partner_id.display_name}"):::{state}'
        return f'po{self.id}({self.name} - {_(i18n[self.state])}):::{state}'

    def _get_flowchart_click(self, menu_id=None):
        self.ensure_one()
        if not menu_id:
            menu_id = self.env.ref('purchase.menu_purchase_root').id
        return f'click po{self.id} "/web#id={self.id}&model=purchase.order&view_type=form&menu_id={menu_id}" _blank'
