# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tools import float_compare


class CrmLeadLine(models.Model):
    _inherit = 'crm.lead.line'

    project_planned_qty = fields.Float(
        string='Project planned qty', compute='_compute_project_planned_qty',
        digits='Product Unit of Measure',
        help='Same warehouse projects planned (not yet delivered) quantity of this product.')

    project_planned_info = fields.Char(compute='_compute_project_planned_info')

    def _get_project_planned(self):
        """Return {project: remaining qty} of the projects that plan this product from
        the same warehouse but have not delivered it yet."""
        self.ensure_one()
        lead = self.lead_id
        warehouse = lead.warehouse_id or lead.team_id.warehouse_id
        if not self.product_id or not warehouse:
            return {}
        domain = [
            ('product_id', '=', self.product_id.id),
            ('project_id.warehouse_id', '=', warehouse.id),
            ('project_id.state', 'in', ('planned', 'confirm', 'process')),
        ]
        lead_id = lead._origin.id
        if lead_id:
            # the project made from this lead already counts these lines
            domain.append(('project_id.crm_ids', 'not in', [lead_id]))
        result = {}
        for pline in self.env['project.products.line'].sudo().search(domain):
            remaining = pline.product_qty - pline.qty_delivered
            if remaining > 0:
                result[pline.project_id] = result.get(pline.project_id, 0.0) + remaining
        return result

    @api.depends('product_id', 'lead_id.warehouse_id', 'lead_id.team_id.warehouse_id')
    def _compute_project_planned_qty(self):
        for line in self:
            line.project_planned_qty = sum(line._get_project_planned().values())

    @api.depends('product_id', 'qty', 'pre_qty', 'lead_id.warehouse_id', 'lead_id.team_id.warehouse_id')
    def _compute_project_planned_info(self):
        """Shown as a notification (project_planned_qty widget) when the planned quantity
        of projects takes the forecasted stock."""
        for line in self:
            line.project_planned_info = False
            planned = line._get_project_planned()
            total = sum(planned.values())
            if not total:
                continue
            free = line.pre_qty - total
            if line.qty and float_compare(line.qty, free, precision_digits=2) <= 0:
                continue
            line.project_planned_info = _(
                '"%(product)s": %(planned)s planned in projects (%(projects)s), not delivered yet. '
                'Forecasted: %(forecast)s, free after projects: %(free)s',
                product=line.product_id.display_name, planned=total,
                projects=', '.join(project.display_name for project in planned),
                forecast=line.pre_qty, free=free)
