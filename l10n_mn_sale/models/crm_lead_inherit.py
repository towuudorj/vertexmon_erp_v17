# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = 'crm.lead'


    @api.model
    def _compute_default_partner_bank_id(self):
        """ Default partner bank account for sale order """
        bank_id = self.env['res.partner.bank'].search([('acc_number', '=', '5002411886')])
        if bank_id:
            return bank_id[0].id
        else:
            return False

    @api.depends('lead_line_ids.price_subtotal')
    def _compute_amount_total(self):
        for lead in self:
            total = 0
            for line in lead.lead_line_ids:
                total += line.price_subtotal
            lead.amount_total = total
            lead.update({
                        'amount_total': total,
                        'untax_amount': total - (total /1.1*0.10),
                        'tax_amount':total/1.1*0.10,
            })

    code = fields.Char(string='Code', readonly=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].with_context(company_id=self.company_id.id).next_by_code('crm.lead'))
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
    together_sales_id = fields.Many2many('res.users', string='Together sales')
    amount_text = fields.Char(string='Amount text',
         readonly=True,compute='_compute_amount')
    project_id = fields.Many2one('project.project', string='Project', required=True)
    is_sale = fields.Boolean(string='Is sale', default=True, tracking=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', required=True)
    invoice_ids = fields.Many2many('account.move',string='Invoice', compute="_compute_invoice")
    invoice_count = fields.Integer(string='Invoice', compute="_compute_invoice")
    purchase_request_ids = fields.Many2many('purchase.requisition', string='Purchase requisition')
    purchase_request_count = fields.Integer(string='Purchase requisition', 
                                            compute="_compute_purchase_request")    
    purchase_order_ids = fields.Many2many('purchase.order', string='Purchase order')
    purchase_order_count = fields.Integer(string='Purchase order', compute="_compute_purchase_request")
    lead_line_ids = fields.One2many('crm.lead.line', 'lead_id', string='Lead line')
    contract_id = fields.Many2one('sales.contract.register', string='Contract')
    new_status = fields.Selection([('new','New'),
                                    ('price_inquire','Price inquire'),
                                    ('break','Break'),
                                    ('confirm','Confirm'),
                                    ('done','Done'),
                                    ('cancel','Cancel')],string='New status', readonly=True, tracking=True, default='new', copy=False)
    status = fields.Selection([('new','New'),
                                ('send_purchase_confirm','Send purchase confirm'),
                                ('purchase_confirm','Confirm'),
                                ('cancel','Cancel')],string='Status', readonly=True, tracking=True, default='new')
    sales_type = fields.Selection([('direct', 'Direct'),
                                   ('tender', 'Tender'),
                                   ('project', 'Project')],
                                  string='Sales type',
                                  default='direct',
                                  required=True, readonly=True)
    send_date = fields.Date(string='Quotation send date', required=True, default=fields.Date.today())
    amount_total = fields.Float(string='Total amount', compute='_compute_amount_total')
    untax_amount = fields.Float(string='Untax amount', compute='_compute_amount_total')
    tax_amount = fields.Float(string='Tax amount', compute='_compute_amount_total')
    crm_type = fields.Selection([('crm', u'Борлуулалт'),
                                 ('stock',u'Нөөцөнд авах')], string='CRM type', default='crm')
    is_purchase = fields.Boolean(string='Is purchase', default=False, tracking=True)
    cancel_reason = fields.Text(string='Cancel reason')
    break_reason = fields.Text(string='Break reason')
    expire_day = fields.Integer(string='Expire day', default=7)
    supply_date = fields.Date(string='Supply date')
    note = fields.Text(string='Note')
    partner_bank_id = fields.Many2one('res.partner.bank', 
                                   string='Bank Account Number',
                                   domain="[('partner_id.ref_company_ids', 'parent_of', company_id)]",
                                   required=False,
                                   default=_compute_default_partner_bank_id)
    def _compute_amount(self):
        for line in self:
            if line.amount_total:
                line.amount_text = verbose_format(line.amount_total, line.pricelist_id.currency_id)
            else:
                line.amount_text = ''


    def action_insert_project(self):
        project_line_obj = self.env['project.products.line']
        for line in self:
            if line.project_id:
                for lines in line.lead_line_ids:
                    if lines.product_id.id:
                        project_line_id = project_line_obj.search([('product_id','=',lines.product_id.id),('project_id','=',line.project_id.id)])
                        if not project_line_id:
                            project_line_obj.create({
                                'product_id': lines.product_id.id,
                                'name': lines.name,
                                'product_uom': lines.uom_id.id,
                                'project_id': line.project_id.id,
                                'product_qty': lines.qty,
                                'price_unit': lines.sale_price,
                                'cost_price': lines.cost_price,
                                'qty_available': lines.pre_qty,
                                'company_id': line.company_id.id
                            })
                    else:
                        raise UserError(_(u'Бараа үүсээгүй байгаа тул төсөл рүү оруулах боломжгүйг анхаарна уу!'))


    def change_status(self):
        for line in self:
            status = False
            for lines in line.lead_line_ids:
                if lines.cost_price > 0.0:
                    status = True

            if status == True:
                line.new_status = 'price_inquire'

    def action_new(self):
        for line in self:
            line.new_status = 'new'
    
    @api.onchange('partner_id', 'company_id','team_id')
    def _onchange_pricelist_id(self):
        for order in self:
            if not order.partner_id:
                order.pricelist_id = False
                continue
            order = order.with_company(order.company_id)
            order.pricelist_id = order.partner_id.property_product_pricelist
            if order.team_id.project_id.id:
                order.project_id = order.team_id.project_id.id

    def send_purchase_request(self):
        for line in self:
            
            for lines in line.lead_line_ids:
                #if lines.margin_percent >0.0:
                #if lines.request_type == 'send_quotation':
                #    raise UserError(_(u'Үнийн санал төрөлтэй байгаа тул илгээх шаардлагагүй болно!'))
                line.status = 'send_purchase_confirm'
                line.is_purchase == True
                #else:
                #    raise UserError(_(u'Ашиг тооцоологдоогүй байгаа тул бүртгэнэ үү!'))

    
    def action_cancel(self):
        for line in self:
            line.status = 'cancel'
            line.purchase_request_ids.action_cancel()
            for lines in line.lead_line_ids:
                lines.state = 'cancel'

    def create_quotation(self):
        for line in self:
            line.is_purchase == True
        sale_order_id = self.env['sale.order'].create(self._prepare_opportunity_quotation_context())

    def action_confirm(self):
        for line in self:
            if line.lead_line_ids:
                line_type = ''
                count = 0
                quote_count = 0
                for lines in line.lead_line_ids:
                    if lines.sale_price == 0.0:
                         raise UserError(_('Барааны зарах үнэ бүртгээгүй байгаа тул бүртгэнэ үү!'))
                    if lines.cost_price == 0.0 and lines.request_type != 'send_quotation':
                        raise UserError(_('Барааны судалсан үнэ бүртгээгүй байгаа тул бүртгэнэ үү!'))
                    if lines.request_type == 'send_quotation':
                        line_type = 'send_quotation'
                        quote_count +=1
                    count +=1
                if not line.order_ids:
                    if line.crm_type == 'stock':
                        line.new_status = 'confirm'
                    elif line.crm_type == 'crm' and line_type == 'send_quotation' and quote_count == count:
                        line.new_status = 'done'
                        sale_order_id = self.env['sale.order'].create(self._prepare_opportunity_quotation_context())
                        sale_order_id.action_confirm()
                    else:
                        line.new_status = 'confirm'
                else:
                    for lines in line.order_ids:
                        if lines.state in ['sale','done']:
                            raise UserError(_('Борлуулалтын захиалга үүссэн байна!'))
                            
                    if line.crm_type == 'stock':
                        line.new_status = 'confirm'
                    elif line.crm_type == 'crm' and line_type == 'send_quotation' and quote_count == count:
                        line.new_status = 'done'
                        sale_order_id = self.env['sale.order'].create(self._prepare_opportunity_quotation_context())
                        sale_order_id.action_confirm()
                    else:
                        line.new_status = 'confirm'

            else:
                raise UserError(_('Бараа бүртгээгүй байгаа тул бүртгэнэ үү!'))

    def confirm_purchase(self):
        """ This method is used to confirm the purchase request """
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        
        for lead in self:
            if not lead.purchase_request_ids:
                raise UserError(_('Purchase request not found!'))
            lead.purchase_request_ids.quotation_done()
            #purchase_id = lead.purchase_request_ids.purchase_ids.id
            #purchase_obj = 'purchase.order'
            #record_link = f"{base_url}/web#id={purchase_id}&model={purchase_obj}&view_type=form"

            #body_html = f"""
            #    <p>Сайн байна уу {self.name},</p>
            #    <p>Худалдан авалтын захиалга үүссэн тул <a href="{record_link}" target="_blank">батална уу.</a>.</p>
            #    <p>Баяраллаа!</p>
            #"""

            #mail_values = {
            #    'subject': 'Худалдан авалт батлах',
            #    'body_html': body_html,
            #    'email_to': self.env.user.email,
            #    'email_from': 'erp@vertexmon.com',
            #}
            #mail = self.env['mail.mail'].create(mail_values)
            #mail.send()
            lead.new_status = 'done'
            if lead.crm_type == 'crm':
                sale_order_id = self.env['sale.order'].create(self._prepare_opportunity_quotation_context())
                sale_order_id.action_confirm()
            #lead.message_post(body=_('Purchase request confirmed.'))

    
    

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
                        'route_id':line.product_id.route_ids.id,
                        'crm_lead_line_id': line.id,
                        'company_id': self.company_id.id or self.env.company.id,
                        'tax_id': [(6, 0, line.product_id.taxes_id.ids)],
                        }
                line_ids.append((0, 0, datas))
            else:
                raise UserError(_('Бараа бүртгээгүй байгаа тул бүртгэнэ үү!'))

        quotation_context = {
            'opportunity_id': self.id,
            'partner_id': self.partner_id.id,
            'partner_type': self.partner_id.partner_type.id,
            'campaign_id': self.campaign_id.id,
            'medium_id': self.medium_id.id,
            'date_order': self.send_date,
            'origin': self.name,
            'warehouse_id': self.team_id.warehouse_id.id,
            'pricelist_id':self.pricelist_id.id,
            'user_id':self.user_id.id,
            'together_sales_id':[(6,0,self.together_sales_id.ids)],
            'picking_policy': 'direct',
            'source_id': self.source_id.id,
            'company_id': self.company_id.id or self.env.company.id,
            'tag_ids': [(6, 0, self.tag_ids.ids)],
            'team_id': self.team_id.id,
            'company_id': self.company_id.id or self.env.company.id,
            'order_line':line_ids 
            }
        
        if self.team_id:
            quotation_context['team_id'] = self.team_id.id
        if self.user_id:
            quotation_context['user_id'] = self.user_id.id
        return quotation_context
    
    #үүсгэх
    def create_purchase_requisition(self):
        for lead in self:
            context = dict(self._context)
            context.pop("default_type", None)
            line_obj = self.env['purchase.requisition.line']
            for lines in lead.lead_line_ids:
                if lines.request_type != "send_quotation":
                    if lines.purchase_user_id:
                        type_id = self.env['purchase.requisition.type'].search([], limit=1)
                        purchase_requests = self.env['purchase.requisition'].search([('crm_lead_id', '=', lead.id),
                                                                                    ('purchase_user_id', '=', lines.purchase_user_id.id),
                                                                                    ('send_date','=',self.send_date),
                                                                                    ('status', '=', 'new')])
                        print ("loggg",purchase_requests)
                        if not purchase_requests:
                            datas = {
                                'crm_lead_id': lead.id,
                                'user_id': lead.user_id.id,
                                'company_id': lead.company_id.id,
                                'origin': lead.name,
                                'warehouse_id': lead.team_id.warehouse_id.id,
                                'currency_id':lead.company_id.currency_id.id,
                                'state': 'draft',
                                'type_id': type_id.id,
                                'name':self.env['ir.sequence'].with_company(self.company_id).next_by_code('purchase.requisition.blanket.order'),
                                'purchase_user_id':lines.purchase_user_id.id,
                                'send_date': self.send_date,
                            }
                            purchase_request_id = self.env['purchase.requisition'].with_context(context).create(datas)
                            print ("dddddddddd",purchase_request_id)
                            lead.purchase_request_ids = [(4,purchase_request_id.id)]
                            if lines.purchase_user_id.id == purchase_request_id.purchase_user_id.id:
                                if lines.request_type != 'is_quotation':
                                    line_ids = self.env['purchase.requisition.line'].search([('requisition_id', '=', purchase_requests.id), 
                                                                                          ('lead_line_id', '=', lines.id)])
                                    if not line_ids:
                                        line_status = ''
                                        #if lines.request_type == 'is_purchase':
                                        #    line_status = 'approve'
                                        
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
                                if lines.request_type != 'send_quotation':
                                    line_ids = self.env['purchase.requisition.line'].search([('requisition_id', '=', purchase_requests.id), 
                                                                                          ('lead_line_id', '=', lines.id)])
                                    if not line_ids:
                                        line_status = ''
                                        #if lines.request_type == 'is_purchase':
                                        #    line_status = 'approve'
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