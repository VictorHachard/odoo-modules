# -*- coding: utf-8 -*-

from odoo import api, fields, models

from odoo.addons.stock_flowchart.tools import mermaid_click, mermaid_label, mermaid_node_id


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    flowchart = fields.Text('Flowchart', compute='_compute_flowchart')

    @api.depends(
        'name', 'state', 'partner_id',
        'picking_ids.name', 'picking_ids.state', 'picking_ids.backorder_id', 'picking_ids.backorder_ids',
    )
    def _compute_flowchart(self):
        i18n = self._get_flowchart_i18n()
        picking_i18n = self.env['stock.picking']._get_flowchart_i18n()
        for rec in self:
            rec.flowchart = '\n'.join([
                'graph TB',
                rec._get_flowchart_style(),
                rec._get_sale_picking_flowchart_graph(i18n=i18n, picking_i18n=picking_i18n),
            ])

    def _get_sale_picking_flowchart_graph(self, more_info=False, i18n=None, picking_i18n=None):
        self.ensure_one()
        node_id = self._get_flowchart_node_id()
        flowchart = [self._get_flowchart_element(i18n=i18n, more_info=more_info)]
        click = self._get_flowchart_click()
        if click:
            flowchart.append(click)
        if self.picking_ids and not picking_i18n:
            picking_i18n = self.env['stock.picking']._get_flowchart_i18n()
        for hierarchy in self.picking_ids._get_picking_hierarchy():
            root = hierarchy[0]
            if len(hierarchy) > 1:
                flowchart.append(root._get_flowchart_sub_graph(picking_i18n))
                flowchart.append(f'{node_id} --> sub{root._get_flowchart_node_id()}')
            else:
                flowchart.append(f'{node_id} --> {root._get_flowchart_element(picking_i18n)}')
                click = root._get_flowchart_click()
                if click:
                    flowchart.append(click)
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
            'sale': 'bg-success-light',
            'cancel': 'bg-danger-light',
        }

    def _get_flowchart_i18n(self):
        return dict(self.env[self._name].fields_get(allfields=['state'])['state']['selection'])

    def _get_flowchart_node_id(self):
        return mermaid_node_id('so', self)

    def _get_flowchart_element(self, i18n=None, more_info=False):
        self.ensure_one()
        if not i18n:
            i18n = self._get_flowchart_i18n()
        state_class = self._get_flowchart_state_color().get(self.state, 'bg-grey-light')
        title = f"{self.name or '/'} - {i18n.get(self.state, self.state or '')}"
        label = mermaid_label(title, self.partner_id.display_name) if more_info else mermaid_label(title)
        return f'{self._get_flowchart_node_id()}({label}):::{state_class}'

    def _get_flowchart_click(self):
        self.ensure_one()
        return mermaid_click('so', self)
