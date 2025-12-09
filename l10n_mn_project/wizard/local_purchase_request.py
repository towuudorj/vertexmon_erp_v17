# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools import format_date, frozendict


class LocalPurchaseRequest(models.TransientModel):
    _name = "local.purchase.request"
    _description = 'Local purchase request'
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    line_ids = fields.One2many('local.purchase.request.line', 'local_parent_id', string='Line data')
    supplier_id = fields.Many2one('res.partner', string='Supplier', required=True)
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    project_id = fields.Many2one('project.project', string='Project', required=True)
    picking_type_id = fields.Many2one('stock.picking.type', string='Stock picking type', required=True, domain="[('code','=','incoming')]")
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(LocalPurchaseRequest, self).default_get(fields_list)
        line_ids = self.env['project.project'].browse(self.env.context['active_ids'])
        line_id = []
        for li in line_ids.products_line:
            if li.purchase_type == 'local':
                line_id.append((0,0,{
                            'product_id':li.product_id.id,
                            'qty':li.product_qty,
                            'uom_id':li.product_uom.id,
                            'line_id':li.id
                            }))
        res['project_id'] = line_ids.id
        res['line_ids'] = line_id
        return res
    
    
    def action_create_purchase(self):
        purchase_obj = self.env['purchase.order']
        purchase_line_obj = self.env['purchase.order.line']
        for line in self:
            purchase_id = purchase_obj.create({
                                'partner_id':line.supplier_id.id,
                                'user_id':self.env.user.id,
                                'state':'draft',
                                'analytic_id':line.project_id.analytic_account_id.id,
                                'picking_type_id':line.picking_type_id.id,
                                'date_order':line.date,
                                'purchase_type':'local'
                                })
            line.project_id.purchase_ids = [(4, purchase_id.id)]
            for lines in line.line_ids:
                if lines.line_id.product_qty >0.0 and lines.line_id.pur_qty >0.0:
                    qty = lines.line_id.product_qty - lines.line_id.pur_qty
                else:
                    qty = lines.qty
                purchase_line_obj.create({
                                        'product_id':lines.product_id.id,
                                        'product_uom':lines.uom_id.id,
                                        'product_qty':qty,
                                        'price_unit':lines.price,
                                        'order_id':purchase_id.id
                                        })
                lines.line_id.pur_qty = lines.line_id.pur_qty + qty


class LocalPurchaseRequestLine(models.TransientModel):
    _name = "local.purchase.request.line"
    _description = 'Local purchase request line'
    
    product_id = fields.Many2one('product.product', string='Product', required=True)
    line_id = fields.Many2one('project.products.line', string='Project line')
    uom_id = fields.Many2one('uom.uom', string='Uom', required=True)
    price = fields.Float(string='Price', required=True)
    qty = fields.Float(string='Qty', required=True)
    local_parent_id = fields.Many2one('local.purchase.request', string='Local purchase request')
    