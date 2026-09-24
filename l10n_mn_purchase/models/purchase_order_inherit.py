# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    partner_type = fields.Many2one('partner.type.register', string='Partner type')
    currency_rate = fields.Float(string='Currency rate', digits=(12, 6), compute="_compute_currency_rate")
    sales_partner_id = fields.Many2one('res.partner', string='Sales Partners')
    purchase_type = fields.Selection([('local', 'Local'),
                                        ('foreign' , 'Foreign')], string='Purchase type',
                                        default='local', required=True)
    is_expense = fields.Boolean(string='Is Expense', default=False)
    destininatio_id = fields.Char(string='Destination')
    analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    dispatch_date = fields.Date(string='Dispatch date')
    freight_type_id = fields.Many2one('freight.type.register', string='Freight type')
    freight_partner_id = fields.Many2one('res.partner', string='Freight partner')
    crm_code = fields.Char(string=u'CRM Код')
    freight_status = fields.Selection([('order','Order done'),
                                       ('payment','Waiting Payment'),
                                       ('manufacturer','Manufacturer'),
                                       ('freight','Freight'),
                                       ('customs','Customs'),
                                       ('stock','Stock')], string='Freight status')
    invoice_status_forced = fields.Boolean(default=False)
    payment_amount = fields.Float(string=u'Төлбөрийн үлдэгдэл', compute='_compute_payment_amount', store=True)
    is_direct_issue = fields.Boolean(string='Шууд зарлагадах', default=False)

    @api.depends('invoice_ids', 'invoice_ids.state', 'invoice_ids.amount_residual_signed', 'amount_total')
    def _compute_payment_amount(self):
        for order in self:
            bills = order.invoice_ids.filtered(lambda m: m.state == 'posted')
            if bills:
                order.payment_amount = sum(bills.mapped('amount_residual_signed'))
            else:
                order.payment_amount = order.amount_total


    def _prepare_invoice(self):
        """Prepare the dict of values to create the new invoice for a purchase order.
        """
        self.ensure_one()
        move_type = self._context.get('default_move_type', 'in_invoice')

        partner_invoice = self.env['res.partner'].browse(self.partner_id.address_get(['invoice'])['invoice'])
        partner_bank_id = self.partner_id.commercial_partner_id.bank_ids.filtered_domain(['|', ('company_id', '=', False), ('company_id', '=', self.company_id.id)])[:1]

        invoice_vals = {
            'ref': self.partner_ref or '',
            'move_type': move_type,
            'narration': self.notes,
            'currency_id': self.currency_id.id,
            'invoice_user_id': self.user_id and self.user_id.id or self.env.user.id,
            'partner_id': partner_invoice.id,
            'invoice_date':self.effective_date,
            'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id._get_fiscal_position(partner_invoice)).id,
            'payment_reference': self.partner_ref or '',
            'partner_bank_id': partner_bank_id.id,
            'invoice_origin': self.name,
            'partner_type_id':self.partner_type.id,
            'invoice_payment_term_id': self.payment_term_id.id,
            'invoice_line_ids': [],
            'company_id': self.company_id.id,
        }
        return invoice_vals


    def button_request(self):
        self.ensure_one()
        self.state = 'sent'

    def button_confirm(self):
        for order in self:
            if order.state not in ['draft', 'sent']:
                continue
            order.order_line._validate_analytic_distribution()
            order._add_supplier_to_product()
            # Deal with double validation process
            if order._approval_allowed():
                order.button_approve()
                #order.write({'date_approve': self.date_order})
            else:
                order.write({'state': 'to approve'})
            if order.analytic_id:
                project_id = self.env['project.project'].search([('analytic_account_id','=',order.analytic_id.id)])
                crm_manager = order.requisition_id.crm_lead_id.user_id
                manager_employee = crm_manager.employee_id
                manager_mail = False
                if manager_employee:
                    manager_mail = manager_employee.work_email
                if not manager_mail:
                    manager_mail = crm_manager.partner_id.email
                if manager_mail:
                    # Send email notification
                    purchase_url = f'/web#id={order.id}&model=purchase.order&view_type=form'
                    self.env['mail.mail'].create({
                        'email_to': manager_mail,
                        'subject': f'Худалдан авалтын захиалга: {order.name} батлагдсан байна.',
                        'body_html': f'Дэлгэрэнгүй мэдээллийг харна уу. <a href="{purchase_url}">{order.name}</a>'+
                        f'- Төслийн нэр: {project_id.name} \n Төслийн менежер: {project_id.user_id.name}, Нийлүүлэгч: {order.partner_id.name}',
                    }).send()
                if order.is_direct_issue and project_id:
                    order._create_project_issue_picking(project_id)
            if order.partner_id not in order.message_partner_ids:
                order.message_subscribe([order.partner_id.id])
        return True

    def _create_project_issue_picking(self, project_id):
        self.ensure_one()
        picking_type = project_id.picking_type_id
        if not picking_type:
            return
        project_price_map = {pline.product_id.id: pline.price_unit for pline in project_id.products_line}
        move_vals = [(0, 0, {
            'product_id': line.product_id.id,
            'name': line.name,
            'product_uom_qty': line.product_qty,
            'product_uom': line.product_uom.id,
            'location_id': picking_type.default_location_src_id.id,
            'location_dest_id': picking_type.default_location_dest_id.id,
            'company_id': self.company_id.id,
            'sale_prices': project_price_map.get(line.product_id.id, line.price_unit),
            'price_subtotal': project_price_map.get(line.product_id.id, line.price_unit) * line.product_qty,
        }) for line in self.order_line if line.product_id]
        if not move_vals:
            return
        picking = self.env['stock.picking'].create({
            'partner_id': project_id.partner_id.id,
            'picking_type_id': picking_type.id,
            'location_id': picking_type.default_location_src_id.id,
            'location_dest_id': picking_type.default_location_dest_id.id,
            'scheduled_date': self.date_order,
            'origin': self.name,
            'analytic_id': project_id.analytic_account_id.id,
            'company_id': self.company_id.id,
            'move_ids': move_vals,
        })
        picking.message_post(body=f'Дотоод худалдан авалтын Шууд зарлага: {self.name}')
        picking.action_confirm()
        project_id.picking_ids = [(4, picking.id)]
        products = self.order_line.product_id
        for pline in project_id.products_line.filtered(lambda l: l.product_id in products):
            pline.picking_ids = [(4, picking.id)]
        buyer = self.user_id
        if buyer.email:
            picking_url = f'/web#id={picking.id}&model=stock.picking&view_type=form'
            self.env['mail.mail'].create({
                'email_to': buyer.email,
                'subject': f'Төслийн зарлагын баримт үүслээ: {picking.name}',
                'body_html': f'{self.name} захиалгатай холбоотой төслийн зарлагын баримт үүссэн байна. '
                f'<a href="{picking_url}">{picking.name}</a>'
                f'<ul><li>Төсөл: {project_id.name}</li></ul>',
            }).send()
        return picking


    @api.onchange('currency_id')
    def _compute_currency_rate(self):
        if self.currency_id != self.company_id.currency_id:
            currency_rate = self.env['res.currency']._get_conversion_rate(
                    from_currency=self.company_id.currency_id,
                    to_currency=self.currency_id,
                    company=self.company_id,
                    date=self.date_approve,
                )
            self.currency_rate = 1/currency_rate
        else:
            self.currency_rate = 1.0



    @api.onchange('requisition_id')
    def _onchange_requisition_id(self):
        if not self.requisition_id:
            return

        self = self.with_company(self.company_id)
        requisition = self.requisition_id
        partner = False
        if self.partner_id:
            partner = self.partner_id
        else:
            for line in requisition.line_ids:
                if line.supplier_id and line.line_status == 'approve':
                    partner = line.supplier_id

                elif not line.supplier_id and line.line_status == 'approve':
                    raise UserError(_('Please select a supplier for the purchase order.'))
        payment_term = partner.property_supplier_payment_term_id

        FiscalPosition = self.env['account.fiscal.position']
        fpos = FiscalPosition.with_company(self.company_id)._get_fiscal_position(partner)

        self.partner_id = partner.id
        self.fiscal_position_id = fpos.id
        self.payment_term_id = payment_term.id
        self.company_id = requisition.company_id.id
        self.currency_id = requisition.currency_id.id
        self.sales_partner_id = requisition.crm_lead_id.partner_id.id
        if not self.origin or requisition.name not in self.origin.split(', '):
            if self.origin:
                if requisition.name:
                    self.origin = self.origin + ', ' + requisition.name
            else:
                self.origin = requisition.name
        self.notes = requisition.description
        self.date_order = fields.Datetime.now()

        if requisition.type_id.line_copy != 'copy':
            return

        # Create PO lines if necessary
        order_lines = []
        for line in requisition.line_ids:
            # Compute name
            product_lang = line.product_id.with_context(
                lang=partner.lang or self.env.user.lang,
                partner_id=partner.id
            )
            name = product_lang.display_name
            if product_lang.description_purchase:
                name += '\n' + product_lang.description_purchase

            # Compute taxes
            taxes_ids = fpos.map_tax(line.product_id.supplier_taxes_id.filtered(lambda tax: tax.company_id == requisition.company_id)).ids

            # Compute quantity and price_unit
            if line.product_uom_id != line.product_id.uom_po_id:
                product_qty = line.product_uom_id._compute_quantity(line.product_qty, line.product_id.uom_po_id)
                price_unit = line.product_uom_id._compute_price(line.price_unit, line.product_id.uom_po_id)
            else:
                product_qty = line.product_qty
                price_unit = line.price_unit

            if requisition.type_id.quantity_copy != 'copy':
                product_qty = 0

            # Create PO line
            order_line_values = line._prepare_purchase_order_line(
                name=name, product_qty=product_qty, price_unit=price_unit,
                taxes_ids=taxes_ids)
            order_lines.append((0, 0, order_line_values))
        self.order_line = order_lines


    @api.onchange('partner_id', 'company_id')
    def onchange_partner_id(self):
        # Ensures all properties and fiscal positions
        # are taken with the company of the order
        # if not defined, with_company doesn't change anything.
        self = self.with_company(self.company_id)
        default_currency = self._context.get("default_currency_id")
        if not self.partner_id:
            self.fiscal_position_id = False
            self.currency_id = default_currency or self.env.company.currency_id.id
        else:
            self.fiscal_position_id = self.env['account.fiscal.position']._get_fiscal_position(self.partner_id)
            self.payment_term_id = self.partner_id.property_supplier_payment_term_id.id
            if self.partner_id.partner_group == '006':
                self.currency_id =  self.partner_id.property_purchase_currency_id.id
            else:
                self.currency_id = self.env.company.currency_id.id
            self.partner_type = self.partner_id.partner_type
            if self.partner_id.buyer_id:
                self.user_id = self.partner_id.buyer_id
        return {}

    @api.depends('order_line.price_total')
    def _amount_all(self):
        for order in self:
            order_lines = order.order_line.filtered(lambda x: not x.display_type and not x.is_downpayment)
            if order.company_id.tax_calculation_rounding_method == 'round_globally':
                tax_results = self.env['account.tax']._compute_taxes([
                    line._convert_to_tax_base_line_dict()
                    for line in order_lines
                ])
                totals = tax_results['totals']
                amount_untaxed = totals.get(order.currency_id, {}).get('amount_untaxed', 0.0)
                amount_tax = totals.get(order.currency_id, {}).get('amount_tax', 0.0)
            else:
                amount_untaxed = sum(order_lines.mapped('price_subtotal'))
                amount_tax = sum(order_lines.mapped('price_tax'))
            order.amount_untaxed = amount_untaxed
            order.amount_tax = amount_tax
            order.amount_total = order.amount_untaxed + order.amount_tax

    @api.depends_context('lang')
    @api.depends('order_line.taxes_id', 'order_line.price_subtotal', 'amount_total', 'amount_untaxed')
    def _compute_tax_totals(self):
        for order in self:
            order_lines = order.order_line.filtered(lambda x: not x.display_type and not x.is_downpayment)
            order.tax_totals = self.env['account.tax']._prepare_tax_totals(
                [x._convert_to_tax_base_line_dict() for x in order_lines],
                order.currency_id or order.company_id.currency_id,
            )

    @api.depends('state', 'order_line.qty_to_invoice', 'order_line')
    def _get_invoiced(self):
        for obj in self:
            if obj.invoice_status_forced:
                return
            acc_move_ids = self.env['account.move'].search([('invoice_origin', '=', obj.name),
                                                            ('state', '!=', 'cancel'),
                                                            ('partner_id', '=', obj.partner_id.id),
                                                            ('company_id', '=', obj.company_id.id),
                                                            ('payment_types', '!=', 'penalty')])
            if acc_move_ids:
                total_invoice_created_amount = sum(l.price_unit * l.quantity for l in acc_move_ids.mapped('invoice_line_ids'))
                total_invoice_amount = sum((line.price_unit * line.product_qty) for line in obj.order_line.filtered(lambda x: not x.is_downpayment))
                if round(total_invoice_amount, 2) == round(total_invoice_created_amount, 2):
                    obj.invoice_status = 'invoiced'
                else:
                    super(PurchaseOrder, self)._get_invoiced()
            else:
                super(PurchaseOrder, self)._get_invoiced()

    def force_invoice_state(self):
        self.invoice_status_forced = True
        if self.invoice_status == 'to invoice':
            self.invoice_status = 'invoiced'
            self.message_post(body=u'Нэхэмжлэлийн төлвийг хүчээр баталлаа.')
        elif self.invoice_status == 'invoiced':
            self.invoice_status = 'to invoice'
            self.message_post(body=u'Нэхэмжлэлийн төлвийг хүчээр цуцаллаа.')


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    sales_partner_id = fields.Many2one('res.partner', string='Sales Partners')
    country_origin = fields.Many2one('res.country', string='Country of Origin')
    analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    month = fields.Selection([('01','1'),
                                ('02','2'),
                                ('03','3'),
                                ('04','4'),
                                ('05','5'),
                                ('06','6'),
                                ('07','7'),
                                ('08','8'),
                                ('09','9'),
                                ('10','10'),
                                ('11','11'),
                                ('12','12')],string=u'Сар')
    pre_qty = fields.Float(string='Pre quantity')
    is_downpayment = fields.Boolean(string='Is Down payment')


    def _prepare_account_move_line(self, move=False):
        res = super(PurchaseOrderLine, self)._prepare_account_move_line(move)
        res.update({'month': self.month})
        if self.is_downpayment:
            res['quantity'] = 1
        return res

    def unlink(self):
        to_delete_invoice_lines = self.env['account.move.line']
        to_delete_invoices = self.env['account.move']
        for obj in self:
            if obj.invoice_lines:
                to_delete_invoice_lines |= obj.invoice_lines
                to_delete_invoices |= obj.invoice_lines.mapped('move_id')
        res = super(PurchaseOrderLine, self).unlink()
        if to_delete_invoice_lines:
            to_delete_invoice_lines.unlink()
        to_delete_invoices = to_delete_invoices.filtered(lambda x: not x.invoice_line_ids)
        if to_delete_invoices:
            to_delete_invoices.unlink()
        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_except_purchase_or_done(self):
        for line in self:
            if line.order_id.state in ['purchase', 'done'] and not line.is_downpayment:
                state_description = {state_desc[0]: state_desc[1] for state_desc in self._fields['state']._description_selection(self.env)}
                raise UserError(_('Cannot delete a purchase order line which is in state %r.', state_description.get(line.state)))

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'


    def unlink(self):
        purchase_order_line = self.env['purchase.order.line']
        for obj in self:
            if obj.purchase_line_id and obj.purchase_line_id.is_downpayment:
                purchase_order_line |= obj.purchase_line_id.sudo()
        res = super(AccountMoveLine, self).unlink()
        if purchase_order_line:
            purchase_order_line.sudo().unlink()
        return res