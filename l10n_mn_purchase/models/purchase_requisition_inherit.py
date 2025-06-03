# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, time

from odoo import api, fields, models, _
from odoo.exceptions import UserError
    
class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'


    vendor_id = fields.Many2one('res.partner', string="Vendor", domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", required=False)



class PurchaseRequisitionLine(models.Model):
    _inherit = "purchase.requisition.line"

    product_id = fields.Many2one('product.product', string='Product', domain=[('purchase_ok', '=', True)], required=False)



    def _prepare_purchase_order_line(self, name, product_qty=0.0, price_unit=0.0, taxes_ids=False):
        self.ensure_one()
        if self.line_status == 'approve':
            requisition = self.requisition_id
            if self.product_description_variants:
                name += '\n' + self.product_description_variants
            if requisition.schedule_date:
                date_planned = datetime.combine(requisition.schedule_date, time.min)
            else:
                date_planned = datetime.now()
            return {
                'name': name,
                'product_id': self.product_id.id,
                'product_uom': self.product_id.uom_po_id.id,
                'product_qty': self.product_qty,
                'price_unit': price_unit,
                'taxes_id': [(6, 0, taxes_ids)],
                'date_planned': date_planned,
                'analytic_distribution': self.analytic_distribution,
            }