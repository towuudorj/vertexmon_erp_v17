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
    _description = 'Purchase reason register'

    
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


    purchase_date = fields.Date(string='Purchase date')
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
    total_amount = fields.Float(string='Total amount', compute='_compute_total_amount')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    price_change = fields.Boolean(string='Price change')
    currency_date = fields.Date(string='Currency date')
    currency_rate = fields.Float(string='Currency rate')
    supplier_day = fields.Char(string='Supplier day')
    supplier_date = fields.Date(string='Supplier date')
    edit_info_desc = fields.Text(string='Мэдээлэл шинэчлэх дээр тайлбар')
    
    
    


    @api.depends('line_ids.subtotal', 'line_ids.price_unit')
    def _compute_total_amount(self):
        for pr in self:
            total = 0.0
            for line in pr.line_ids:
                #qty = float(line.product_qty or 0.0)
                #price = float(line.price_unit or 0.0)
                total += line.subtotal
            pr.total_amount = total

    def quotation_edit_request(self):
        for line in self:
            if line.edit_info_desc == False:
                raise UserError(_('Мэдээлэл шинэчлэх тайлбарыг оруулна уу!'))
            for lines in line.line_ids:
                lines.line_status = 'unapproved'
            for pur in line.purchase_ids:
                if pur.state != 'draft':
                    pur.button_cancel()
                    pur.button_draft()

            
            line.crm_lead_id.new_status = 'new'
            for lines in line.crm_lead_id.order_ids:
                lines.action_cancel()
                lines.action_draft()
            line.status = 'quotation_st'
            line.price_change == True

    


    


    def quotation_start(self):
        for pr in self:
            pr.status = 'quotation_st'
            pr.name = self.env['ir.sequence'].with_company(self.company_id).next_by_code('purchase.requisition.blanket.order')
    
    def qoutation_end(self):
        team_obj = self.env['crm.team']
        for pr in self:
            for line in pr.line_ids:
                for lines in pr.purchase_ids.order_line:
                    if lines.product_id.id == line.product_id.id:
                        lines.price_unit = line.price_unit
                        lines.purchase_date = line.purchase_date

                if line.price_unit > 0.0 and line.currency_id.id != False and line.is_free_pro == False:
                    if line.supplier_id.id != False:
                        line.action_approve()
                        pr.status = 'quotation_ed'
                        pr.crm_lead_id.change_status()

                    else:
                        raise UserError(_('Үнэ судлуулах хүсэлтэнд нийлүүлэгчийг оруулаагүй байгаа тул оруулна уу!'))
                else:
                    if line.price_unit == 0.0 and line.currency_id.id != False and line.is_free_pro == False:
                        raise UserError(_('Үнэ судлуулах хүсэлтэнд үнэ, валют болон үнийн зөвшөөрлийг оруулаагүй байгаа тул оруулна уу!'))
            if pr.price_change == False:
                crm_manager = self.user_id
                if crm_manager:
                    # Send email notification
                    po_url = f'/web#id={self.id}&model=purchase.requisition&view_type=form'
                    self.env['mail.mail'].create({
                        'email_to': ','.join(crm_manager.mapped('email')),
                        'subject': f'Таны Сэжим {self.crm_lead_id.code} -ын үнэ судлагдав.',
                        'body_html': f'Үнийн судалгааны мэдээлэл харах холбоос <a href="{po_url}">{self.name}</a> дээр дарна уу',
                    }).send()
            else:
                crm_manager = self.user_id
                if crm_manager:
                    # Send email notification
                    po_url = f'/web#id={self.id}&model=purchase.requisition&view_type=form'
                    self.env['mail.mail'].create({
                        'email_to': ','.join(crm_manager.mapped('email')),
                        'subject': f'Таны Сэжим {self.crm_lead_id.code} -ын үнэ шинэчлэгдсэн байна.',
                        'body_html': f'Шинэчилсэн үнийн судалгааны мэдээлэл харах холбоос <a href="{po_url}">{self.name}</a> дээр дарна уу',
                    }).send()

    def quotation_cancel(self):
        for pr in self:
            pr.status = 'cancel'
        
    def quotation_done(self):
        for pr in self:
            pr.status = 'done'
            pr.create_purchase_order()
    
    @api.onchange('purchase_date')
    def _onchange_purchase_date(self):
        if self.purchase_date:
            for line in self.line_ids:
                line.purchase_date = self.purchase_date

    @api.onchange('vendor_id')
    def _onchange_vendor_id(self):
        if self.vendor_id:
            for line in self.line_ids:
                line.supplier_id = self.vendor_id.id

    @api.onchange('currency_id')
    def _onchange_currency_id(self):
        if self.currency_id:
            for line in self.line_ids:
                line.currency_id = self.currency_id.id
            if self.currency_date:
                rate = self.env['res.currency.rate'].search([('currency_id','=',self.currency_id.id),('name','=',self.currency_date),('company_id','=',self.company_id.id)])
                if rate.inverse_company_rate > 0.0:
                    self.currency_rate = rate.inverse_company_rate
                else:
                    raise UserError(_('Сонгосон огнооны ханш оруулаагүй байгаа тул оруулана уу!'))
            else:
                raise UserError(_('Ханш татах огноог оруулна уу!'))





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
                    if lines.product_id.id == False:
                        raise UserError(_('Бараа сонгоогүй байгаа тул сонгоно уу!'))
                    if not purchase_order:
                        picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'incoming'),
                                                                                 ('warehouse_id', '=', pr.warehouse_id.id)], limit=1)
                        datas = {
                            'user_id': pr.user_id.id,
                            'company_id': pr.company_id.id,
                            'origin': pr.name,
                            'crm_code':pr.crm_lead_code,
                            'picking_type_id':picking_type_id.id,
                            'state': 'draft',
                            'analytic_id': pr.crm_lead_id.project_id.analytic_account_id.id,
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
                                                                            ('price_unit', '=', lines.price_unit),
                                                                                  ('product_id', '=', lines.product_id.id),
                                                                                  ('name','=',lines.product_description_variants)])
                        
                        if lines.supplier_id.id == purchase_order_id.partner_id.id:
                            line_ids = self.env['purchase.order.line'].search([('order_id', '=', purchase_order_id.id), 
                                                                                 ('price_unit', '=', lines.price_unit),
                                                                                  ('product_id', '=', lines.product_id.id),
                                                                                  ('name','=',lines.product_description_variants)])
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
                                                                                ('price_unit', '=', lines.price_unit),
                                                                                  ('product_id', '=', lines.product_id.id),
                                                                                  ('name','=',lines.product_description_variants)])
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
                else:
                    raise UserError(_('Supplier сонгоогүй байгаа тул сонгоно уу!'))
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
    subtotal = fields.Float(string='Total amount', compute='_compute_subtotal_amount')
    is_free_pro = fields.Boolean(string='Is product free')
    purchase_date = fields.Date(string='Purchase date')
    
    @api.depends('subtotal', 'product_qty', 'price_unit')
    def _compute_subtotal_amount(self):
        for line in self:
            qty = line.product_qty or 0.0
            price = line.price_unit or 0.0
            line.subtotal = qty * price

    @api.onchange('product_qty', 'price_unit')
    def _onchange_price_unit(self):
        for line in self:
            qty = float(line.product_qty or 0.0)
            price = float(line.price_unit or 0.0)

            if qty < 0:
                # Prefer returning a warning to avoid breaking UI in some clients:
                return {
                    'warning': {
                        'title': _("Invalid quantity"),
                        'message': _("Тоо 0-с их байх ёстой!"),
                    },
                    # optionally reset the wrong value
                    'value': {'product_qty': 0.0, 'total_amount': 0.0},
                }

            line.subtotal = qty * price


    def write(self, vals):
        if 'price_unit' in vals:
            self.requisition_id.message_post(
                    body=_(u'%s барааны хуучин үнэ %s шинэ үнэ %s') % (
                        self.product_description_variants, self.price_unit, vals['price_unit']))
            if self.requisition_id.crm_lead_id:
                self.requisition_id.crm_lead_id.message_post(
                        body=_(u'%s барааны судалсан үнэ %s') % (self.product_description_variants, vals['price_unit']))

        res = super(PurchaseRequisitionLine, self).write(vals)
        if 'price_unit' in vals:
            if vals['price_unit'] <= 0.0 and any(
                    requisition.state not in ['draft', 'cancel', 'done'] and
                    requisition.is_quantity_copy == 'none' for requisition in self.mapped('requisition_id')):
                raise UserError(_('You cannot confirm the blanket order without price.'))
            # If the price is updated, we have to update the related SupplierInfo
            self.supplier_info_ids.write({'price': vals['price_unit']})
            
        return res

    
    
    def action_approve(self):
        for line in self:
            line.line_status = 'approve'
            if line.price_unit == 0 and line.currency_id.id == False and line.is_free_pro == False:
                raise UserError(_('Бараа нэгж үнэ эсвэл валют оруулаагүй байгаа болон үнэ судалж дуусаагүй байгаа тул оруулана уу!'))
            #elif not line.product_id.id:
            #    raise UserError(_('Бараа оруулаагүй байгаа тул оруулана уу!'))
            else:
                for list in line.requisition_id.crm_lead_id.lead_line_ids:
                    if list.product_id.id == line.product_id.id or list.name == line.product_description_variants or list.id == line.lead_line_id.id:
                        list.cost_price = line.price_unit
                        list.currency_id = line.currency_id.id
                        list.product_id = line.product_id.id
                        list.purchase_date = line.purchase_date


            


    def action_unapproved(self):
        for line in self:
            line.line_status = 'unapproved'