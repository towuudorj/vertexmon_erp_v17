# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CrmLeadLine(models.Model):
    _name = 'crm.lead.line'
    _description = 'Crm lead line'

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.user.company_id)
    product_id = fields.Many2one('product.product', string='Product')
    name = fields.Text(string='Reference', required=True)
    uom_id = fields.Many2one('uom.uom', string='Uom')
    is_price_request = fields.Boolean(string='Is price request')
    cost_price = fields.Float(string='Cost price')
    sale_price = fields.Float(string='Sale price')
    qty = fields.Float(string='Quantity')
    price_subtotal = fields.Float(string='Price subtotal')
    lead_id = fields.Many2one('crm.lead', string='Lead')
    request_line_id = fields.Many2one('purchase.requisition.line', string='Request line')
    currency_id = fields.Many2one('res.currency', string='Currency')
    purchase_user_id = fields.Many2one('res.users', string='Purchase user', domain="[('is_purchase_manager','=',True)]")
    request_type = fields.Selection([('is_quotation', 'Is quotation'),
                                      ('is_purchase', 'Purchase'),
                                      ('send_quotation', 'Send quotation')],
                                     string='Request type', default='send_quotation')
    priority = fields.Selection([
        ('normal', 'Normal'),
        ('high', 'High'),
    ], string='Priority', default='normal')

    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.name
            self.uom_id = self.product_id.uom_id.id
            self.sale_price = self.product_id.list_price
            

    @api.onchange('qty','sale_price')
    def _onchange_qty(self):
        if self.qty and self.sale_price:
            self.price_subtotal = self.sale_price * self.qty
        

