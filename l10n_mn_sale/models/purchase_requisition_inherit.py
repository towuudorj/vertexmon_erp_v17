# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, time


PURCHASE_REQUISITION_STATES = [
    ('draft', 'New'),
    ('ongoing', 'Ongoing'),
    ('in_progress', 'Confirmed'),
    ('open', 'Bid Selection'),
    ('done', 'Done'),
    ('cancel', 'Cancelled')
]

class PurchaseReasonRegister(models.Model):
    _name = 'purchase.reason.register'

    
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.user.company_id)
    name = fields.Char(string='Purchase reason register', required=True)

    

class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    def _get_type_id(self):
        return self.env['purchase.requisition.type'].search([], limit=1)

    crm_lead_id = fields.Many2one('crm.lead', string='Lead')
    sale_id = fields.Many2one('sale.order', string='Sale order')
    crm_lead_code = fields.Char(related="crm_lead_id.code",string=u'CRM Код')
    send_date = fields.Date(string='Quotation send date')
    purchase_user_id = fields.Many2one('res.users', string='Purchase user')
    type_id = fields.Many2one('purchase.requisition.type', string="Agreement Type", default=_get_type_id)
    state = fields.Selection(PURCHASE_REQUISITION_STATES,
                              'Status', tracking=True, required=True,
                              copy=False, default='draft')
    status = fields.Selection([('new','New'),
                            ('quotation_st','Quotation start'),
                            ('quotation_ed','Quotation end'),
                            ('done','Done'),
                            ('cancel','Cancel')], string='Status', default='new')


    def quotation_start(self):
        for pr in self:
            pr.status = 'quotation_st'
    
    def qoutation_end(self):
        for pr in self:
            for line in pr.line_ids:
                if line.price_unit > 0.0 and line.line_status == 'approve':
                    pr.status = 'quotation_ed'
                else:
                    raise UserError(_('Үнэ судлуулах хүсэлтэнд үнэ болон үнийн зөвшөөрлийг оруулаагүй байгаа тул оруулна уу!'))

    def quotation_cancel(self):
        for pr in self:
            pr.status = 'cancel'
        
    def quotation_done(self):
        for pr in self:
            pr.status = 'done'
            pr.create_purchase_order()
    



    @api.onchange('currency_id')
    def _onchange_currency_id(self):
        if self.currency_id:
            for line in self.line_ids:
                line.currency_id = self.currency_id.id





    #үүсгэх
    def create_purchase_order(self):
        for pr in self:
            line_ids = self.env['purchase.order.line']
            for lines in pr.line_ids:
                if lines.supplier_id:
                    purchase_order = self.env['purchase.order'].search([('currency_id', '=', lines.currency_id.id),
                                                                            ('partner_id','=', lines.supplier_id.id),
                                                                            ('state', '=', 'draft'),
                                                                            ('requisition_id', '=', pr.id)],limit=1)
                    if not purchase_order:
                        
                        datas = {
                            'user_id': pr.user_id.id,
                            'company_id': pr.company_id.id,
                            'origin': pr.name,
                            'state': 'draft',
                            'sales_partner_id':pr.crm_lead_id.partner_id.id,
                            'date_order': datetime.now(),
                            'partner_type':lines.supplier_id.partner_type.id,
                            'partner_id': lines.supplier_id.id,
                            'currency_id': lines.currency_id.id,
                            'requisition_id': pr.id,
                        }
                        purchase_order_id = self.env['purchase.order'].create(datas)

                        pr.purchase_ids = [(4,purchase_order_id.id)]
                        line_ids = self.env['purchase.order.line'].search([('order_id', '=', purchase_order_id.id), 
                                                                                  ('product_id', '=', lines.product_id.id)])
                        
                        if lines.supplier_id.id == purchase_order_id.partner_id.id:
                            line_ids = self.env['purchase.order.line'].search([('order_id', '=', purchase_order_id.id), 
                                                                                  ('product_id', '=', lines.product_id.id)])
                            if not line_ids:
                                line_data = {
                                            'product_id': lines.product_id.id,
                                            'name': lines.product_description_variants,
                                            'product_qty': lines.product_qty,
                                            'product_uom': lines.product_id.uom_id.id,
                                            'price_unit': lines.price_unit,
                                            'currency_id': pr.currency_id.id,
                                            'date_planned':datetime.now(),
                                            'order_id': purchase_order_id.id,
                                            }
                                line_ids.create(line_data)
                    else:
                        pr.purchase_ids = [(4,purchase_order.id)]
                        if lines.supplier_id.id == purchase_order.partner_id.id:
                            line_ids = self.env['purchase.order.line'].search([('order_id', '=', purchase_order.id), 
                                                                                  ('product_id', '=', lines.product_id.id)])
                            if not line_ids:
                                line_data = {
                                            'product_id': lines.product_id.id,
                                            'name': lines.product_description_variants,
                                            'product_qty': lines.product_qty,
                                            'product_uom': lines.product_id.uom_id.id,
                                            'price_unit': lines.price_unit,
                                            'order_id': purchase_order.id,
                                            'date_planned':datetime.now(),
                                            'currency_id': pr.currency_id.id,
                                            }
                                line_ids.create(line_data)
                #else:
                #    raise UserError(_('Бараа бүртгээгүй байгаа тул бүртгэнэ үү!'))
            #else:
            #    raise UserError(_('Үнэ судлуулах хүсэлт үүссэн байгаа тул анхаарна уу!'))
        return True


    def action_open(self):
        self.write({'state': 'open'})


class PurchaseRequisitionLine(models.Model):
    _inherit = 'purchase.requisition.line'

    line_status = fields.Selection([('approve','Approve'),
                              ('unapproved','Unapproved')],string='Status')
    cancel_reason_id = fields.Many2one('purchase.reason.register', string='Cancel reason')
    supplier_id = fields.Many2one('res.partner', string='Supplier')
    lead_line_id = fields.Many2one('crm.lead.line',string='Lead line')
    sale_line_id = fields.Many2one('sale.order.line', string='Sale line')
    priority = fields.Selection([
        ('normal', 'Normal'),
        ('high', 'High'),
    ], string='Priority', default='normal')
    currency_id = fields.Many2one('res.currency', string='Currency')
    total_amount = fields.Float(string='Total amount', compute='_compute_total_amount')
    

    def _compute_total_amount(self):
        for line in self:
            if line.product_qty and line.price_unit:
                line.total_amount = line.product_qty * line.price_unit
            else:
                line.total_amount = 0.0
    
    def action_approve(self):
        for line in self:
            line.line_status = 'approve'
            if line.price_unit == 0 and line.requisition_id.status == 'quotation_ed':
                raise UserError(_('Бараа нэгж үнэ оруулаагүй байгаа болон үнэ судалж дуусаагүй байгаа тул оруулана уу!'))
            #elif not line.product_id.id:
            #    raise UserError(_('Бараа оруулаагүй байгаа тул оруулана уу!'))
            else:
                for list in line.requisition_id.crm_lead_id.lead_line_ids:
                    if list.product_id.id == line.product_id.id or list.name == line.product_description_variants or list.id == line.lead_line_id.id:
                        list.cost_price = line.price_unit
                        list.currency_id = line.currency_id.id
                        list.product_id = line.product_id.id


            


    def action_unapproved(self):
        for line in self:
            line.line_status = 'unapproved'