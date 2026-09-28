# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tools import float_is_zero
from odoo.exceptions import UserError
from odoo import Command


class PurchaseCreateInvoiceWizard(models.TransientModel):
    _name = "purchase.create.invoice"
    _description = "Create invoice from purchase wizard"

    @api.model
    def default_get(self, fields_list):
        results = super(PurchaseCreateInvoiceWizard, self).default_get(fields_list)
        if 'purchase_order_id' in fields_list and 'purchase_order_id' not in results:
            purchase_id = self._context.get('active_id', False)
            purchase_id = self.env['purchase.order'].browse(purchase_id)
            results['purchase_order_id'] = purchase_id.id
            results['currency_id'] = purchase_id.currency_id.id if purchase_id and purchase_id.currency_id else False
        return results

    purchase_order_id = fields.Many2one('purchase.order', required=True)
    payment_method = fields.Selection(
        selection=[
            ('remaining', 'Remaining amount'),
            ('fixed', 'Fixed amount'),
            ('term', "Payment term")
        ],
        string="Create Invoice",
        default='remaining',
        required=True)
    payment_term_id = fields.Many2one('account.payment.term', string="Payment Term")
    invoice_created_amount = fields.Float(
        string="Invoice created amount",
        compute="_compute_invoice_create_amounts",
        help="The amount invoice created = Purchase Order Total - Down Payments.")
    amount_to_invoice_create = fields.Float(
        string="Amount to invoice create",
        compute="_compute_invoice_create_amounts",
        help="The amount to invoice create = Purchase Order Total - Down Payments.")
    payment_type = fields.Selection([('down_payment', 'Down payment'),
                                     ('progress_payment', 'Progress payment'),
                                     ('final_payment', 'Final payment'),
                                     ('barter', 'Barter transaction'),
                                     ('guarantee_collateral', 'Guarantee and collateral'),
                                     ('penalty', 'Penalty')],
                                    default=False,
                                    string='Payment type')
    line_ids = fields.One2many('purchase.create.invoice.line', 'wizard_id', string='Invoice list',
                               compute='_compute_lines', inverse='_inverse_lines', store=True)
    currency_id = fields.Many2one(string='Currency', comodel_name='res.currency', required=True)
    amount = fields.Float(
        string="Down Payment Amount",
        help="The percentage of amount to be invoiced in advance.")
    display_draft_invoice_warning = fields.Boolean(compute='_compute_display_draft_invoice_warning')

    @api.onchange('payment_type', 'line_ids')
    def _compute_invoice_create_amounts(self):
        for obj in self:
            acc_move_ids = self.env['account.move'].search([('invoice_origin', '=', obj.purchase_order_id.name),
                                                            ('state', '!=', 'cancel'),
                                                            ('partner_id', '=', obj.purchase_order_id.partner_id.id),
                                                            ('company_id', '=', obj.purchase_order_id.company_id.id),
                                                            ('payment_types', '!=', 'penalty')])
            if acc_move_ids:
                total_invoice_created_amount = sum(l.price_unit * l.quantity for l in acc_move_ids.mapped('invoice_line_ids'))
                obj.invoice_created_amount = total_invoice_created_amount
                obj.amount_to_invoice_create = sum((line.price_unit * line.product_qty) for line in obj.purchase_order_id.order_line.filtered(lambda x: not x.is_downpayment)) - total_invoice_created_amount
            else:
                obj.invoice_created_amount = 0
                obj.amount_to_invoice_create = sum((line.price_unit * line.product_qty) for line in obj.purchase_order_id.order_line.filtered(lambda x: not x.is_downpayment))

    @api.onchange('payment_term_id', 'payment_method')
    def _compute_lines(self):
        for obj in self:
            line_obj = self.env['purchase.create.invoice.line']
            all_line = line_obj
            account_move_obj = self.env['account.move']
            acc_move_id = account_move_obj.search([('invoice_origin', '=', obj.purchase_order_id.name),
                                                   ('state', '!=', 'cancel'),
                                                   ('partner_id', '=', obj.purchase_order_id.partner_id.id),
                                                   ('company_id', '=', obj.purchase_order_id.company_id.id)])
            if obj.amount_to_invoice_create != 0:
                if obj.payment_term_id and obj.payment_method == 'term':
                    for lines in obj.payment_term_id.line_ids:
                        if lines.value == 'percent':
                            amount = float(obj.amount_to_invoice_create / 100) * lines.value_amount
                            is_create = False
                            invoice_id = False
                            for inv in acc_move_id:
                                if sum(l.price_unit * l.quantity for l in inv.invoice_line_ids) == amount and inv.payment_percent == lines.value_amount:
                                    is_create = True
                                    invoice_id = inv
                                    acc_move_id -= inv
                            line = line_obj.create({
                                'company_id': obj.purchase_order_id.company_id.id,
                                'invoice_amount': amount,
                                'percent': lines.value_amount,
                                'is_created': is_create,
                                'desc': invoice_id.invoice_line_ids[0].name if invoice_id else '',
                                'nb_days': lines.nb_days,
                                'invoice_id': invoice_id.id if invoice_id else False,
                                'payment_type': False,
                                'wizard_id': obj._origin.id,
                            })
                            all_line |= line
            for inv in acc_move_id:
                line = line_obj.create({
                    'company_id': obj.purchase_order_id.company_id.id,
                    'invoice_amount': sum(l.price_unit * l.quantity for l in inv.mapped('invoice_line_ids')),
                    'is_created': True,
                    'desc': inv.invoice_line_ids[0].name if inv.invoice_line_ids else '',
                    'invoice_id': inv.id,
                    'percent': inv.payment_percent,
                    'wizard_id': obj._origin.id,
                    'payment_type': inv.payment_types if inv.payment_types else 'down_payment',
                })
                all_line |= line
            if all_line:
                obj.line_ids = all_line
            else:
                obj.line_ids = False

    def _inverse_lines(self):
        pass

    def create_invoice(self):
        if self.payment_method == 'term':
            for line in self.line_ids:
                if line.is_new_create:
                    self.action_create_invoice(term_line=line)
        else:
            self.action_create_invoice()
        if self.amount_to_invoice_create == 0:
            for line in self.purchase_order_id.order_line:
                line.qty_to_invoice = 0
        return self.purchase_order_id.action_view_invoice()


    @api.onchange('line_ids')
    def _compute_display_draft_invoice_warning(self):
        for wizard in self:
            acc_move_id = wizard.line_ids.mapped('invoice_id')
            draft_invoice_ids = acc_move_id.filtered(lambda invoice: invoice.state == 'draft')
            wizard.display_draft_invoice_warning = True if draft_invoice_ids else False

    def view_draft_invoices(self):
        acc_move_id = self.line_ids.mapped('invoice_id')
        draft_invoice_ids = acc_move_id.filtered(lambda invoice: invoice.state == 'draft')
        return draft_invoice_ids

    def action_create_invoice(self, term_line=False):
        order = self.purchase_order_id
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        invoice_vals_list = []
        sequence = 10
        payment_type = self.payment_type if not term_line else term_line.payment_type
        if order.invoice_status == 'to invoice' or payment_type == 'down_payment' or self.purchase_order_id.purchase_type == 'local':
            order = order.with_company(order.company_id)
            invoice_vals = order._prepare_invoice()
            invoice_vals['payment_types'] = self.payment_type
            for line in order.order_line:
                if line.display_type == 'line_section':
                    continue
                if not line.is_downpayment:
                    down_payment_product_id = order.company_id.sudo().sale_down_payment_product_id
                    if line.product_template_id and line.product_template_id.categ_id and 'хангамж' in line.product_template_id.categ_id.name.lower():
                        if not order.company_id.sudo().purchase_down_payment_product_id:
                            order.company_id.purchase_down_payment_product_id = self.env['product.product'].sudo().create(
                                {
                                    'name': u'Нэхэмжлэл/Хангамжийн/',
                                    'type': 'service',
                                    'invoice_policy': 'order',
                                    'company_id': self.env.company.id,
                                    'categ_id': line.product_template_id.categ_id.id,
                                    'taxes_id': [Command.set(line.product_template_id.taxes_id.ids)],
                                }
                            )
                        down_payment_product_id = order.company_id.sudo().purchase_down_payment_product_id
                    else:
                        if line.product_id.detailed_type == 'service':
                            down_payment_product_id = line.product_id
                    if self.payment_method == 'fixed':
                        payment_percent = float(self.amount / float(sum((line.price_unit * line.product_qty) for line in self.purchase_order_id.order_line.filtered(lambda x: not x.is_downpayment)) / 100))
                        price_unit = float(line.price_unit * line.product_qty * payment_percent /  100)
                        down_payment_line = self.create_down_payment_line(price_unit, down_payment_product_id.id,
                                                                          line.taxes_id, line.id)
                        line_vals = down_payment_line._prepare_account_move_line()
                    elif self.payment_method == 'term':
                        payment_percent = term_line.percent
                        price_unit = float(line.price_unit * line.product_qty / 100) * payment_percent
                        invoice_vals['payment_percent'] = payment_percent
                        invoice_vals['payment_types'] = term_line.payment_type
                        down_payment_line = self.create_down_payment_line(price_unit, down_payment_product_id.id,
                                                                          line.taxes_id, line.id)
                        line_vals = down_payment_line._prepare_account_move_line()
                        line_vals.update({'name': term_line.desc if term_line.desc else dict(term_line._fields['payment_type']._description_selection(self.env)).get(term_line.payment_type)})
                    else:
                        payment_percent = float(self.amount_to_invoice_create / float(sum((line.price_unit * line.product_qty) for line in self.purchase_order_id.order_line.filtered(lambda x: not x.is_downpayment)) / 100))
                        price_unit = float(line.price_unit * line.product_qty * payment_percent / 100)
                        down_payment_line = self.create_down_payment_line(price_unit, down_payment_product_id.id,
                                                                          line.taxes_id, line.id)
                        line_vals = down_payment_line._prepare_account_move_line()
                    line_vals.update({'sequence': sequence})
                    invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                    sequence += 1
            invoice_vals_list.append(invoice_vals)

        if not invoice_vals_list:
            raise UserError(_('There is no invoiceable line. If a product has a control policy based on received quantity, please make sure that a quantity has been received.'))
        if self.payment_method == 'fixed':
            if self.payment_type != 'penalty' and self.amount_to_invoice_create < self.amount:
                raise UserError(_("Invoice amount is greater than the amount remaining to be invoiced"))
        moves = self.env['account.move']
        AccountMove = self.env['account.move'].with_context(default_move_type='in_invoice')
        for vals in invoice_vals_list:
            moves |= AccountMove.with_company(vals['company_id']).create(vals)

        moves.filtered(lambda m: m.currency_id.round(m.amount_total) < 0).action_switch_move_type()

        return

    def create_down_payment_line(self, price_unit, product_id, texes_id, main_line_id):
        order = self.purchase_order_id
        purchase_order_line_obj = self.env['purchase.order.line']
        sequence = max(order.order_line.mapped('sequence')) + 1
        if not order.order_line.filtered(lambda line: line.is_downpayment and line.display_type == 'line_section'):
            purchase_order_line_obj.create({
                'order_id': order.id,
                'name': _('Down payment'),
                'is_downpayment': True,
                'display_type': 'line_section',
                'sequence': sequence,
                'company_id': order.company_id.id,
                'product_qty': 0,
            })
            sequence += 1

        down_payment_line = purchase_order_line_obj.create({
            'order_id': order.id,
            'name': _('Down payment'),
            'is_downpayment': True,
            'sequence': sequence,
            'qty_to_invoice': 1,
            'company_id': order.company_id.id,
            'currency_id': order.currency_id.id,
            'price_unit': price_unit,
            'product_id': product_id,
            'taxes_id': texes_id,
            'state': 'draft',
            'product_qty': 1,
            'parent_line_id': main_line_id,
        })
        return down_payment_line

    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        if self.line_ids:
            created_payment_types = self.line_ids.mapped('payment_type')
            if self.payment_type in ['down_payment', 'final_payment'] and self.payment_type in created_payment_types:
                raise UserError(_("You cannot create more than one invoice with this payment type."))

class PurchaseCreateInvoiceLine(models.TransientModel):
    _name = 'purchase.create.invoice.line'
    _description = 'Purchase Create Invoice Line'

    company_id = fields.Many2one('res.company', string='Company')
    invoice_id = fields.Many2one('account.move', string='Invoice')
    invoice_amount = fields.Float(string='Invoice amount')
    percent = fields.Float(string='Percent')
    is_created = fields.Boolean(string='Is created')
    is_new_create = fields.Boolean(string='Is new create')
    desc = fields.Char(string='Description')
    nb_days = fields.Integer(string='Description')
    wizard_id = fields.Many2one('purchase.create.invoice')
    payment_type = fields.Selection([('down_payment', 'Down payment'),
                                     ('progress_payment', 'Progress payment'),
                                     ('final_payment', 'Final payment'),
                                     ('barter', 'Barter transaction'),
                                     ('guarantee_collateral', 'Guarantee and collateral'),
                                     ('penalty', 'Penalty')],
                                    default=False,
                                    string='Payment type')

    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        for obj in self:
            if obj.wizard_id:
                line_ids = obj.wizard_id.line_ids.filtered(lambda line: line.id != obj.id)
                created_payment_types = line_ids.mapped('payment_type') if line_ids else False
                if obj.payment_type in ['down_payment',
                                        'final_payment'] and created_payment_types and obj.payment_type in created_payment_types:
                    raise UserError(_("You cannot create more than one invoice with this payment type."))
