# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools import format_date, frozendict
from datetime import timedelta
import logging
_logger = logging.getLogger(__name__)


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'
    _description = "Sales Advance Payment Invoice"

    line_ids = fields.One2many('sale.order.invoice.payment.term.line', 'wizard_id', string='Invoice list',
                                compute='_compute_lines', inverse='_inverse_lines', store=True)
    advance_payment_method = fields.Selection(
        selection_add=[('term', 'Payment term')],
        string="Create Invoice",
        default='fixed',
        required=True,
        ondelete={'term': 'set default'})
    new_payment_method = fields.Selection(
        selection=[
            ('fixed', 'Fixed amount'),
            ('term', "Payment term")
        ],
        string="Create Invoice",
        default='fixed',
        required=True,
        help="A standard invoice is issued with all the order lines ready for invoicing,"
             "according to their invoicing policy (based on ordered or delivered quantity).")
    payment_term_id = fields.Many2one('account.payment.term',  string="Payment Term")
    invoice_created_amount = fields.Monetary(
        string="Invoice created amount",
        compute="_compute_invoice_create_amounts",
        help="The amount invoice created = Sale Order Total - Down Payments.")
    amount_to_invoice_create = fields.Monetary(
        string="Amount to invoice create",
        compute="_compute_invoice_create_amounts",
        help="The amount to invoice create = Sale Order Total - Down Payments.")
    payment_type = fields.Selection([('down_payment', 'Down payment'),
                                     ('progress_payment', 'Progress payment'),
                                     ('final_payment', 'Final payment'),
                                     ('barter', 'Barter transaction'),
                                     ('guarantee_collateral', 'Guarantee and collateral'),
                                     ('penalty', 'Penalty')],
                                    required=True,
                                    default='down_payment',
                                    string='Payment type')


    @api.model
    def default_get(self, fields_list):
        res = super(SaleAdvancePaymentInv, self).default_get(fields_list)
        sale_order_id = self.env['sale.order'].browse(self.env.context['active_id'])
        line_data = []
        account_move_obj = self.env['account.move']
        acc_move_id = account_move_obj.search([('invoice_origin', '=', sale_order_id.name),
                                               ('state', '!=', 'cancel'),
                                               ('partner_id', '=', sale_order_id.partner_id.id),
                                               ('company_id', '=', sale_order_id.company_id.id)])

        for inv in acc_move_id:
            line_data.append((0, 0, {
                'company_id': sale_order_id.company_id.id,
                'invoice_amount': inv.amount_total,
                'is_created': True,
                'desc': _('Down payment'),
                'invoice_id': inv.id,
                'payment_type': inv.payment_type if inv.payment_type else 'down_payment',
            }))
        res['line_ids'] = line_data
        res['advance_payment_method'] = 'fixed'
        return res

    def _create_invoices(self, sale_orders):
        self.ensure_one()
        if self.advance_payment_method == 'delivered':
            return sale_orders._create_invoices(final=self.deduct_down_payments, grouped=not self.consolidated_billing)
        else:
            invoice_ids = self.env['account.move']
            if self.advance_payment_method == 'fixed':
                if self.payment_type != 'penalty' and self.display_invoice_amount_warning:
                    raise UserError(_("Invoice amount is greater than the amount remaining to be invoiced"))
                self.create_down_payment_invoices(self.fixed_amount)
            else:
                for line in self.line_ids:
                    if line.is_new_create:
                        invoice_ids |= self.create_down_payment_invoices(line.invoice_amount, line)
        return invoice_ids

    def create_down_payment_invoices(self, invoice_amount, payment_line=False):
        self.sale_order_ids.ensure_one()
        self = self.with_company(self.company_id)
        order = self.sale_order_ids

        # Create deposit product if necessary
        if not self.product_id:
            self.company_id.sale_down_payment_product_id = self.env['product.product'].create(
                self._prepare_down_payment_product_values(self.fixed_amount)
            )
            self._compute_product_id()

        # Create down payment section if necessary
        SaleOrderline = self.env['sale.order.line'].with_context(sale_no_log_for_new_lines=True)
        if not any(line.display_type and line.is_downpayment for line in order.order_line):
            SaleOrderline.create(
                self._prepare_down_payment_section_values(order)
            )

        down_payment_lines = SaleOrderline.create(
            self._prepare_down_payment_lines_values(order, invoice_amount=invoice_amount)
        )
        invoice = self.env['account.move'].sudo().create(
            self._prepare_invoice_values(order, down_payment_lines, payment_line=payment_line if payment_line else False)
        ).with_user(self.env.uid)

        # Ensure the invoice total is exactly the expected fixed amount.
        delta_amount = (invoice.amount_total - invoice_amount) * (1 if invoice.is_inbound() else -1)
        if not order.currency_id.is_zero(delta_amount):
            receivable_line = invoice.line_ids \
                .filtered(lambda aml: aml.account_id.account_type == 'asset_receivable')[:1]
            product_lines = invoice.line_ids \
                .filtered(lambda aml: aml.display_type == 'product')
            tax_lines = invoice.line_ids \
                .filtered(lambda aml: aml.tax_line_id.amount_type not in (False, 'fixed'))

            if product_lines and tax_lines and receivable_line:
                line_commands = [Command.update(receivable_line.id, {
                    'amount_currency': receivable_line.amount_currency + delta_amount,
                })]
                delta_sign = 1 if delta_amount > 0 else -1
                for lines, attr, sign in (
                        (product_lines, 'price_total', -1),
                        (tax_lines, 'amount_currency', 1),
                ):
                    remaining = delta_amount
                    lines_len = len(lines)
                    for line in lines:
                        if order.currency_id.compare_amounts(remaining, 0) != delta_sign:
                            break
                        amt = delta_sign * max(
                            order.currency_id.rounding,
                            abs(order.currency_id.round(remaining / lines_len)),
                        )
                        remaining -= amt
                        line_commands.append(Command.update(line.id, {attr: line[attr] + amt * sign}))
                invoice.line_ids = line_commands
        invoice.advance_payment_percentage = self.amount
        poster = self.env.user._is_internal() and self.env.user.id or SUPERUSER_ID
        invoice.with_user(poster).message_post_with_source(
            'mail.message_origin_link',
            render_values={'self': invoice, 'origin': order},
            subtype_xmlid='mail.mt_note',
        )
        title = _("Down payment invoice {}%").format(payment_line.percent) if payment_line else _("Down payment invoice")
        order.with_user(poster).message_post(
            body=_("%s has been created",
                   invoice._get_html_link(title=title)),
        )

        return invoice

    def _prepare_down_payment_lines_values(self, order, invoice_amount=0):
        """ Create one down payment line per tax or unique taxes combination.
            Apply the tax(es) to their respective lines.

            :param order: Order for which the down payment lines are created.
            :return:      An array of dicts with the down payment lines values.
        """
        self.ensure_one()
        if self.advance_payment_method == 'term':
            percentage = invoice_amount / order.amount_total if order.amount_total else 1
        elif self.advance_payment_method == 'percentage':
            percentage = self.amount / 100
        else:
            percentage = self.fixed_amount / order.amount_total if order.amount_total else 1

        order_lines = order.order_line.filtered(lambda l: not l.display_type and not l.is_downpayment)
        base_downpayment_lines_values = self._prepare_base_downpayment_line_values(order)

        tax_base_line_dicts = [
            line._convert_to_tax_base_line_dict(
                analytic_distribution=line.analytic_distribution,
                handle_price_include=False
            )
            for line in order_lines
        ]
        computed_taxes = self.env['account.tax']._compute_taxes(
            tax_base_line_dicts)
        down_payment_values = []
        for line, tax_repartition in computed_taxes['base_lines_to_update']:
            taxes = line['taxes'].flatten_taxes_hierarchy()
            fixed_taxes = taxes.filtered(lambda tax: tax.amount_type == 'fixed')
            down_payment_values.append([
                taxes - fixed_taxes,
                line['analytic_distribution'],
                tax_repartition['price_subtotal']
            ])
            for fixed_tax in fixed_taxes:
                if fixed_tax.price_include:
                    continue

                if fixed_tax.include_base_amount:
                    pct_tax = taxes[list(taxes).index(fixed_tax) + 1:]\
                        .filtered(lambda t: t.is_base_affected and t.amount_type != 'fixed')
                else:
                    pct_tax = self.env['account.tax']
                down_payment_values.append([
                    pct_tax,
                    line['analytic_distribution'],
                    line['quantity'] * fixed_tax.amount
                ])

        downpayment_line_map = {}
        analytic_map = {}
        for tax_id, analytic_distribution, price_subtotal in down_payment_values:
            grouping_key = frozendict({'tax_id': tuple(sorted(tax_id.ids))})
            downpayment_line_map.setdefault(grouping_key, {
                **base_downpayment_lines_values,
                **grouping_key,
                'product_uom_qty': 0.0,
                'price_unit': 0.0,
            })
            downpayment_line_map[grouping_key]['price_unit'] += price_subtotal
            if analytic_distribution:
                analytic_map.setdefault(grouping_key, [])
                analytic_map[grouping_key].append((price_subtotal, analytic_distribution))

        lines_values = []
        for key, line_vals in downpayment_line_map.items():
            # don't add line if price is 0 and prevent division by zero
            if order.currency_id.is_zero(line_vals['price_unit']):
                continue
            # weight analytic account distribution
            if analytic_map.get(key):
                line_analytic_distribution = {}
                for price_subtotal, account_distribution in analytic_map[key]:
                    for account, distribution in account_distribution.items():
                        line_analytic_distribution.setdefault(account, 0.0)
                        line_analytic_distribution[account] += price_subtotal / line_vals['price_unit'] * distribution
                line_vals['analytic_distribution'] = line_analytic_distribution
            # round price unit
            line_vals['price_unit'] = order.currency_id.round(line_vals['price_unit'] * percentage)
            lines_values.append(line_vals)

        return lines_values

    def _prepare_invoice_values(self, order, so_line, payment_line=False):
        res = super()._prepare_invoice_values(order, so_line)
        if self.advance_payment_method == 'term' and payment_line:
            today = fields.Date.today()
            res['invoice_date'] = today + timedelta(days=payment_line.nb_days)
            res['payment_type'] = payment_line.payment_type
            for line_vals in res['invoice_line_ids']:
                line_vals[2]['name'] = payment_line.desc
        if self.advance_payment_method == 'fixed':
            res['payment_type'] = self.payment_type
        return res

    @api.onchange('new_payment_method')
    def _compute_advance_payment_method(self):
        for obj in self:
            obj.advance_payment_method = obj.new_payment_method

    @api.onchange('payment_term_id', 'new_payment_method')
    def _compute_lines(self):
        for obj in self:
            line_obj = self.env['sale.order.invoice.payment.term.line']
            all_line = line_obj
            sale_order_id = obj.sale_order_ids[0]
            if obj.amount_to_invoice_create != 0:
                account_move_obj = self.env['account.move']
                acc_move_id = account_move_obj.search([('invoice_origin', '=', sale_order_id.name),
                                                       ('state', '!=', 'cancel'),
                                                       ('partner_id', '=', sale_order_id.partner_id.id),
                                                       ('company_id', '=', sale_order_id.company_id.id)])
                if obj.payment_term_id and obj.new_payment_method == 'term':
                    for lines in obj.payment_term_id.line_ids:
                        if lines.value == 'percent':
                            amount = obj.amount_to_invoice_create / 100.0 * lines.value_amount
                            is_create = False
                            invoice_id = False
                            for inv in acc_move_id:
                                if inv.amount_total == amount:
                                    is_create = True
                                    invoice_id = inv
                                    acc_move_id -= inv
                            line = line_obj.create({
                                'company_id': sale_order_id.company_id.id,
                                'invoice_amount': amount,
                                'percent': lines.value_amount,
                                'is_created': is_create,
                                'desc': invoice_id.invoice_line_ids[0].name if invoice_id else '',
                                'nb_days': lines.nb_days,
                                'invoice_id': invoice_id.id if invoice_id else False,
                                'payment_type': 'down_payment',
                                'wizard_id': obj._origin.id,
                            })
                            all_line |= line
                for inv in acc_move_id:
                    line = line_obj.create({
                        'company_id': sale_order_id.company_id.id,
                        'invoice_amount': inv.amount_total,
                        'is_created': True,
                        'desc': inv.invoice_line_ids[0].name,
                        'invoice_id': inv.id,
                        'wizard_id': obj._origin.id,
                        'payment_type': inv.payment_type if inv.payment_type else 'down_payment',
                    })
                    all_line |= line
                if all_line:
                    obj.line_ids = all_line
                else:
                    obj.line_ids = False
            else:
                obj.line_ids = False

    def _inverse_lines(self):
        pass

    @api.onchange('sale_order_ids')
    def _compute_invoice_create_amounts(self):
        for obj in self:
            sale_order_id = obj.sale_order_ids[0]
            acc_move_ids = self.env['account.move'].search([('invoice_origin', '=', sale_order_id.name),
                                                   ('state', '!=', 'cancel'),
                                                   ('partner_id', '=', sale_order_id.partner_id.id),
                                                   ('company_id', '=', sale_order_id.company_id.id)])
            if acc_move_ids:
                total_invoice_created_amount = sum(acc_move_ids.mapped('amount_total'))
                obj.invoice_created_amount = total_invoice_created_amount
                obj.amount_to_invoice_create = obj.sale_order_ids[0].amount_total - total_invoice_created_amount
            else:
                obj.invoice_created_amount = 0
                obj.amount_to_invoice_create = obj.sale_order_ids[0].amount_total

    @api.depends('amount', 'fixed_amount', 'advance_payment_method', 'amount_to_invoice')
    def _compute_display_invoice_amount_warning(self):
        for wizard in self:
            invoice_amount = wizard.fixed_amount
            if wizard.advance_payment_method == 'percentage':
                invoice_amount = wizard.amount / 100 * sum(wizard.sale_order_ids.mapped('amount_total'))
            wizard.display_invoice_amount_warning = invoice_amount > wizard.amount_to_invoice_create


class SaleOrderInvoicePaymentTermLine(models.TransientModel):
    _name = 'sale.order.invoice.payment.term.line'
    _description = 'Sale order invoice payment term line'

    company_id = fields.Many2one('res.company', string='Company')
    invoice_id = fields.Many2one('account.move', string='Invoice')
    invoice_amount = fields.Float(string='Invoice amount')
    percent = fields.Float(string='Percent')
    is_created = fields.Boolean(string='Is created')
    is_new_create = fields.Boolean(string='Is new create')
    desc = fields.Char(string='Description')
    nb_days = fields.Integer(string='Description')
    wizard_id = fields.Many2one('sale.advance.payment.inv', string='Payment term')
    payment_type = fields.Selection([('down_payment', 'Down payment'),
                                     ('progress_payment', 'Progress payment'),
                                     ('final_payment', 'Final payment'),
                                     ('barter', 'Barter transaction'),
                                     ('guarantee_collateral', 'Guarantee and collateral'),
                                     ('penalty', 'Penalty')],
                                    required=True,
                                    default='down_payment',
                                    string='Payment type')