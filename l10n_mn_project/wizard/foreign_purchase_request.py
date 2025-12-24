# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools import format_date, frozendict


class ForeignPurchaseRequest(models.TransientModel):
    _name = "foreign.purchase.request"
    _description = 'Foreign purchase request'
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    project_id = fields.Many2one('project.project', string='Project', required=True)
    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    line_ids = fields.One2many('foreign.purchase.request.line', 'foreign_parent_id', string='Line data')
    
    @api.model
    def default_get(self, fields_list):
        res = super(ForeignPurchaseRequest, self).default_get(fields_list)
        line_ids = self.env['project.project'].browse(self.env.context['active_ids'])
        line_id = []
        for li in line_ids.products_line:
            if li.purchase_type == 'foreign':
                if li.product_qty > 0.0 and li.qty_available >0.0:
                    if li.product_qty > li.qty_available:
                        qty = li.product_qty - li.qty_available
                    else:
                        qty = 0
                else:
                    qty = li.product_qty
                line_id.append((0,0,{
                            'product_id':li.product_id.id,
                            'desc':li.name,
                            'qty':qty,
                            'uom_id':li.product_uom.id,
                            'purchase_user_id':li.purchase_manager_id.id,
                            'line_id':li.id
                            }))
        res['project_id'] = line_ids.id
        res['line_ids'] = line_id
        res['partner_id'] = line_ids.partner_id.id
        return res
    
    
    def action_create_crm(self):
        crm_obj = self.env['crm.lead']
        crm_line_obj = self.env['crm.lead.line']
        for line in self:
            crm_id = crm_obj.create({
                            'project_id':line.project_id.id,
                            'partner_id':line.partner_id.id,
                            'send_date':line.date,
                            'crm_type':'stock',
                            'user_id':self.env.user.id,
                            'new_status':'new',
                            'name':'%s'%line.partner_id.name,
                            'pricelist_id':line.partner_id.property_product_pricelist.id,
                            'type':'opportunity',
                            })
            line.project_id.crm_ids = [(4, crm_id.id)]
            for lines in line.line_ids:
                if lines.line_id.product_qty > 0.0 and  lines.line_id.pur_qty > 0.0:
                    qty = lines.line_id.product_qty - lines.line_id.pur_qty
                else:
                    qty = lines.qty
                crm_line_obj.create({
                                    'product_id':lines.product_id.id,
                                    'name':lines.desc,
                                    'uom_id':lines.uom_id.id,
                                    'lead_id':crm_id.id,
                                    'qty':qty,
                                    'request_type':'is_purchase',
                                    'purchase_user_id':lines.purchase_user_id.id
                                    })
                lines.line_id.pur_qty = lines.line_id.pur_qty + qty
    

class ForeignPurchaseRequestLine(models.TransientModel):
    _name = 'foreign.purchase.request.line'
    _description = 'Foreign purchase request line'
    
    product_id = fields.Many2one('product.product', string='Product')
    line_id = fields.Many2one('project.products.line', string='Project line')
    desc = fields.Char(string='Desc')
    qty = fields.Float(string='Qty', required=True)
    uom_id = fields.Many2one('uom.uom', string='Uom', required=True)
    purchase_user_id = fields.Many2one('res.users', string='Purchase user', required=True, domain="[('is_purchase_manager','=',True)]") 
    foreign_parent_id = fields.Many2one('foreign.purchase.request', string='Foreign')
    
    
    