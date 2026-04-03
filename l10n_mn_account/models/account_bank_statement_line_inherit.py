# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'


    cash_move_type_id = fields.Many2one('account.cash.move.type', string='Cash move type')
    move_account_names = fields.Char(compute='_compute_counterpart_account_name')
    company_amount = fields.Float(compute='_compute_company_amount')

    tax_ids = fields.Many2many(
        'account.tax',
        string='Taxes',
        help='Taxes applied to this bank statement line.'
    )

    def _synchronize_to_moves(self, changed_fields):
        if self._context.get('skip_account_move_synchronization'):
            return

        trigger_fields = (
            'payment_ref', 'amount', 'amount_currency',
            'foreign_currency_id', 'currency_id',
            'partner_id', 'cash_move_type_id',
            'tax_ids',
        )

        if not any(f in changed_fields for f in trigger_fields):
            return

        for st_line in self.with_context(skip_account_move_synchronization=True):

            if not st_line.move_id:
                continue

            move = st_line.move_id

            liquidity_lines, suspense_lines, other_lines = st_line._seek_for_lines()
            new_vals_list = st_line._prepare_move_line_default_vals()

            commands = []

            # 1️⃣ Update liquidity line
            if liquidity_lines:
                commands.append((1, liquidity_lines.id, new_vals_list[0]))

            # 2️⃣ Remove old counterpart lines
            for line in (suspense_lines | other_lines):
                commands.append((2, line.id))

            # 3️⃣ Create new counterpart lines (net + tax)
            for vals in new_vals_list[1:]:
                commands.append((0, 0, vals))


            was_posted = move.state == 'posted'

            if was_posted:
                move.button_draft()

            move.with_context(check_move_validity=False).write({
                'line_ids': commands,
            })

            if was_posted:
                move.action_post()


    @api.onchange('tax_ids')
    def _onchange_tax_ids(self):
        for line in self:
            if line.move_id:
                line._synchronize_to_moves(['tax_ids'])


    def _create_counterpart_move_line_vals(self, counterpart_vals):
        vals = super()._create_counterpart_move_line_vals(counterpart_vals)

        if self.tax_ids:
            vals['tax_ids'] = [(6, 0, self.tax_ids.ids)]

        return vals

    def _prepare_move_line_default_vals(self, counterpart_account_id=None):
        self.ensure_one()

        if not counterpart_account_id:
            counterpart_account_id = self.journal_id.suspense_account_id.id

        if not counterpart_account_id:
            raise UserError(_("Please configure suspense account."))

        company_currency = self.company_id.currency_id
        journal = self.journal_id
        journal_currency = journal.currency_id or company_currency

        amount = self.amount
        is_inbound = amount > 0

        # currency convert
        if journal_currency == company_currency:
            company_amount = amount
        else:
            company_amount = journal_currency._convert(
                amount, company_currency, self.company_id, self.date
            )

        abs_amount = abs(company_amount)
        sign = 1 if company_amount > 0 else -1


        liquidity_vals = {
            'name': self.payment_ref or '/',
            'account_id': journal.default_account_id.id,
            'partner_id': self.partner_id.id,
            'currency_id': journal_currency.id,
            'amount_currency': abs_amount * sign,
            'debit': abs_amount if is_inbound else 0.0,
            'credit': abs_amount if not is_inbound else 0.0,
        }


        if not self.tax_ids:
            counterpart_vals = {
                'name': self.payment_ref or '/',
                'account_id': counterpart_account_id,
                'partner_id': self.partner_id.id,
                'debit': abs_amount if not is_inbound else 0.0,
                'credit': abs_amount if is_inbound else 0.0,
                'amount_currency': -abs_amount * sign,
            }
            return [liquidity_vals, counterpart_vals]


        tax = self.tax_ids[0]

        res = tax.compute_all(
            abs_amount,
            currency=company_currency,
            quantity=1,
            partner=self.partner_id,
        )

        net = res['total_excluded']
        tax_amount = res['taxes'][0]['amount']


        net_vals = {
            'name': self.payment_ref or '/',
            'account_id': counterpart_account_id,
            'partner_id': self.partner_id.id,
            'debit': net if not is_inbound else 0.0,
            'credit': net if is_inbound else 0.0,
            'amount_currency': -net * sign,
        }


        tax_account = tax.invoice_repartition_line_ids.filtered(
            lambda x: x.repartition_type == 'tax'
        )[:1].account_id

        tax_vals = {
            'name': _('Tax'),
            'account_id': tax_account.id,
            'partner_id': self.partner_id.id,
            'debit': tax_amount if not is_inbound else 0.0,
            'credit': tax_amount if is_inbound else 0.0,
            'amount_currency': -tax_amount * sign,
        }


        total_debit = liquidity_vals['debit'] + net_vals['debit'] + tax_vals['debit']
        total_credit = liquidity_vals['credit'] + net_vals['credit'] + tax_vals['credit']

        diff = round(total_debit - total_credit, 2)

        if diff:
            if diff > 0:
                tax_vals['credit'] += diff
            else:
                tax_vals['debit'] += abs(diff)

        return [liquidity_vals, net_vals, tax_vals]

    def _compute_counterpart_account_name(self):
        for rec in self:
            rec.move_account_names = ', '.join(
                rec.move_id.line_ids.mapped('account_id.name')
            ) if rec.move_id else False

    def _compute_company_amount(self):
        for rec in self:
            if rec.move_id:
                rec.company_amount = sum(
                    rec.move_id.line_ids.filtered(
                        lambda l: l.account_id == rec.journal_id.default_account_id
                    ).mapped('balance')
                )
            else:
                rec.company_amount = 0.0