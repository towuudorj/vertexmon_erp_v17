# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    code = fields.Char(string='Code', readonly=True,
                        default=lambda self: self.env['ir.sequence'].next_by_code('crm.lead'))
    partner_id = fields.Many2one(
        'res.partner', string='Customer', check_company=True, index=True, tracking=10, required=True,
        help="Linked partner (optional). Usually created when converting the lead. You can find a partner by its Name, TIN, Email or Internal Reference.")
    invoice_policy = fields.Selection(
        [("order", "Ordered quantities"), ("delivery", "Delivered quantities")],
        readonly=True, string="Invoice Policy",
        help="Ordered Quantity: Invoice based on the quantity the customer "
        "ordered.\n"
        "Delivered Quantity: Invoiced based on the quantity the vendor "
        "delivered (time or deliveries).",
    )
    invoice_ids = fields.Many2many('account.move',string='Invoice', compute="_compute_invoice")
    invoice_count = fields.Integer(string='Invoice', compute="_compute_invoice")
    purchase_request_ids = fields.Many2many('purchase.requisition', string='Purchase requisition')
    purchase_request_count = fields.Integer(string='Purchase requisition', 
                                            compute="_compute_purchase_request")    
    purchase_order_ids = fields.Many2many('purchase.order', string='Purchase order')
    purchase_order_count = fields.Integer(string='Purchase order', compute="_compute_purchase_request")
    lead_line_ids = fields.One2many('crm.lead.line', 'lead_id', string='Lead line')
    contract_id = fields.Many2one('sales.contract.register', string='Contract')
    sales_type = fields.Selection([('direct', 'Direct'),
                                   ('tender', 'Tender'),
                                   ('project', 'Project')],
                                  string='Sales type',
                                  default='direct',
                                  required=True, readonly=True)
    send_date = fields.Date(string='Quotation send date', required=True)
    amount_total = fields.Float(string='Total amount', compute='_compute_amount_total')
    crm_type = fields.Selection([('crm', 'CRM'),
                                ('quote', 'Quotation Request')], string='CRM type', default='crm')
    


    def _compute_amount_total(self):
        for lead in self:
            total = 0
            for line in lead.lead_line_ids:
                total += line.sale_price * line.qty
            lead.amount_total = total

    def _prepare_opportunity_quotation_context(self):
        """ Prepares the context for a new quotation (sale.order) by sharing the values of common fields """
        self.ensure_one()
        line_ids = []
        for line in self.lead_line_ids:
            if line.product_id.id:
                datas = {
                        'product_id': line.product_id.id,
                        'name': line.name,
                        'product_uom_qty': line.qty,
                        'product_uom': line.uom_id.id,
                        'price_unit': line.sale_price,
                        'tax_id': [(6, 0, line.product_id.taxes_id.ids)],
                        }
                line_ids.append((0, 0, datas))
            else:
                raise UserError(_('Бараа бүртгээгүй байгаа тул бүртгэнэ үү!'))

        quotation_context = {
            'default_opportunity_id': self.id,
            'default_partner_id': self.partner_id.id,
            'default_partner_type': self.partner_id.partner_type.id,
            'default_campaign_id': self.campaign_id.id,
            'default_medium_id': self.medium_id.id,
            'default_origin': self.name,
            'default_source_id': self.source_id.id,
            'default_company_id': self.company_id.id or self.env.company.id,
            'default_tag_ids': [(6, 0, self.tag_ids.ids)],
            'default_order_line':line_ids 
            }
        
        if self.team_id:
            quotation_context['default_team_id'] = self.team_id.id
        if self.user_id:
            quotation_context['default_user_id'] = self.user_id.id
        return quotation_context
    
    #үүсгэх
    def create_purchase_requisition(self):
        for lead in self:
            context = dict(self._context)
            context.pop("default_type", None)
            line_obj = self.env['purchase.requisition.line']
            for lines in lead.lead_line_ids:
                if lines.purchase_user_id:
                    type_id = self.env['purchase.requisition.type'].search([], limit=1)
                    purchase_requests = self.env['purchase.requisition'].search([('crm_lead_id', '=', lead.id),
                                                                                ('purchase_user_id', '=', lines.purchase_user_id.id),
                                                                                ('send_date','=',self.send_date),
                                                                                ('state', '=', 'draft')])
                    if not purchase_requests:
                        datas = {
                            'crm_lead_id': lead.id,
                            'user_id': lead.user_id.id,
                            'company_id': lead.company_id.id,
                            'origin': lead.name,
                            'state': 'draft',
                            'type_id': type_id.id,
                            'purchase_user_id':lines.purchase_user_id.id,
                            'send_date': self.send_date,
                        }
                        purchase_request_id = self.env['purchase.requisition'].with_context(context).create(datas)
                        lead.purchase_request_ids = [(4,purchase_request_id.id)]
                        if lines.purchase_user_id.id == purchase_request_id.purchase_user_id.id:
                            line_ids = self.env['purchase.requisition.line'].search([('requisition_id', '=', purchase_requests.id), 
                                                                                  ('lead_line_id', '=', lines.id)])
                            if not line_ids:
                                line_status = ''
                                if lines.request_type == 'is_purchase':
                                    line_status = 'approve'
                                
                                line_data = {
                                            'product_id': lines.product_id.id,
                                            'product_description_variants': lines.name,
                                            'product_qty': lines.qty,
                                            'product_uom_id': lines.uom_id.id,
                                            'priority': lines.priority,
                                            'requisition_id': purchase_request_id.id,
                                            'currency_id': purchase_requests.currency_id.id,
                                            'line_status':line_status,
                                            'price_unit':0,
                                            'lead_line_id':lines.id,
                                            }
                                line_id = line_obj.create(line_data)
                                lines.request_line_id = line_id.id
                            else:
                                lines.request_line_id = line_ids.id
                    else:
                        lead.purchase_request_ids = [(4,purchase_requests.id)]
                        if lines.purchase_user_id.id == purchase_requests.purchase_user_id.id:
                            line_ids = self.env['purchase.requisition.line'].search([('requisition_id', '=', purchase_requests.id), 
                                                                                  ('lead_line_id', '=', lines.id)])
                            if not line_ids:
                                line_status = ''
                                if lines.request_type == 'is_purchase':
                                    line_status = 'approve'
                                line_data = {
                                            'product_id': lines.product_id.id,
                                            'product_description_variants': lines.name,
                                            'product_qty': lines.qty,
                                            'priority': lines.priority,
                                            'product_uom_id': lines.uom_id.id,
                                            'requisition_id': purchase_requests.id,
                                            'lead_line_id':lines.id,
                                            'currency_id': purchase_requests.currency_id.id,
                                            'price_unit':0,
                                            }
                                
                                line_id = line_obj.create(line_data)
                                lines.request_line_id = line_id.id
                            else:
                                lines.request_line_id = line_ids.id
                #else:
                #    raise UserError(_('Бараа бүртгээгүй байгаа тул бүртгэнэ үү!'))
            #else:
            #    raise UserError(_('Үнэ судлуулах хүсэлт үүссэн байгаа тул анхаарна уу!'))
        return True
    

    #Тоололт
    def _compute_purchase_request(self):
        purchase_order_obj = self.env['purchase.order']
        for lead in self:
            purchase_requests = self.env['purchase.requisition'].search([('crm_lead_id', '=', lead.id),('state', '!=', 'cancel')])
            purchase_orders = purchase_order_obj.search([('requisition_id', 'in', purchase_requests.ids)])
            lead.purchase_order_ids = purchase_orders
            lead.purchase_order_count = len(purchase_orders)
            lead.purchase_request_ids = purchase_requests
            lead.purchase_request_count = len(purchase_requests)


    def _compute_invoice(self):
        for lead in self:
            sale_orders = lead.order_ids.filtered_domain(self._get_lead_sale_order_domain())
            invoices = sale_orders.order_line.invoice_lines.move_id.filtered(lambda r: r.move_type in ('out_invoice', 'out_refund'))
            lead.invoice_ids = invoices
            lead.invoice_count = len(invoices)

    #үсрэх
    def action_view_purchase_requisition(self, purchases=False):
        if not purchases:
            purchases = self.mapped('purchase_request_ids')
        action = self.env['ir.actions.actions']._for_xml_id('purchase_requisition.action_purchase_requisition')
        if len(purchases) > 1:
            action['domain'] = [('id', 'in', purchases.ids)]
        elif len(purchases) == 1:
            form_view = [(self.env.ref('purchase_requisition.view_purchase_requisition_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = purchases.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        context = {
        }
        if len(self) == 1:
            context.update({
                'default_crm_lead_id': self.id,
            })
        action['context'] = context
        return action


    def action_view_purchase_order(self, purchases=False):
        if not purchases:
            purchases = self.mapped('purchase_order_ids')
        action = self.env['ir.actions.actions']._for_xml_id('purchase.purchase_form_action')
        if len(purchases) > 1:
            action['domain'] = [('id', 'in', purchases.ids)]
        elif len(purchases) == 1:
            form_view = [(self.env.ref('purchase.purchase_order_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = purchases.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        context = {
        }
        if len(self) == 1:
            context.update({
                #'default_requisition_id': self.id,
            })
        action['context'] = context
        return action



    def action_view_invoice(self, invoices=False):
        if not invoices:
            invoices = self.mapped('invoice_ids')
        action = self.env['ir.actions.actions']._for_xml_id('account.action_move_out_invoice_type')
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = invoices.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        context = {
            'default_move_type': 'out_invoice',
        }
        if len(self) == 1:
            context.update({
                'default_partner_id': self.partner_id.id,
                'default_invoice_origin': self.name,
            })
        action['context'] = context
        return action