# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    cash_move_type_id = fields.Many2one('account.cash.move.type', string='Cash move type')
    move_account_names = fields.Char(compute='_compute_counterpart_account_name', string='Account names')
    company_amount = fields.Float(compute='_compute_company_amount', string='Company amount')
    tax_ids = fields.Many2many(
        'account.tax',
        string='Taxes',
        help='Taxes applied to this bank statement line.'
    )



    def _synchronize_to_moves(self, changed_fields):
        """ Update the account.move regarding the modified account.bank.statement.line.
        :param changed_fields: A list containing all modified fields on account.bank.statement.line.
        """
        if self._context.get('skip_account_move_synchronization'):
            return

        if not any(field_name in changed_fields for field_name in (
            'payment_ref', 'amount', 'amount_currency',
            'foreign_currency_id', 'currency_id', 'partner_id',
            'cash_move_type_id'

        )):
            return
        for st_line in self.with_context(skip_account_move_synchronization=True):
            liquidity_lines, suspense_lines, other_lines = st_line._seek_for_lines()
            journal = st_line.journal_id
            company_currency = journal.company_id.currency_id
            journal_currency = journal.currency_id if journal.currency_id != company_currency else False

            line_vals_list = st_line._prepare_move_line_default_vals()
            line_ids_commands = [(1, liquidity_lines.id, line_vals_list[0])]

            if suspense_lines:
                line_ids_commands.append((1, suspense_lines.id, line_vals_list[1]))
            else:
                line_ids_commands.append((0, 0, line_vals_list[1]))

            for line in other_lines:
                line_ids_commands.append((2, line.id))

            st_line_vals = {
                'currency_id': (st_line.foreign_currency_id or journal_currency or company_currency).id,
                'line_ids': line_ids_commands,
            }
            if st_line.move_id.journal_id != journal:
                st_line_vals['journal_id'] = journal.id
            if st_line.move_id.partner_id != st_line.partner_id:
                st_line_vals['partner_id'] = st_line.partner_id.id
            st_line.move_id.write(st_line_vals)
        
    def _create_counterpart_move_line_vals(self, counterpart_vals):
        """
        Ensure taxes are added during reconciliation as well
        """
        vals = super()._create_counterpart_move_line_vals(counterpart_vals)

        if self.tax_ids:
            vals['tax_ids'] = [(6, 0, self.tax_ids.ids)]

        return vals
    
    
    
    
    
    # =====================================================
    # MAIN VAT SPLIT ENGINE (BALANCED & SAFE)
    # =====================================================
    def _prepare_move_line_default_vals(self, counterpart_account_id=None):
        self.ensure_one()

        if not counterpart_account_id:
            counterpart_account_id = self.journal_id.suspense_account_id.id

        if not counterpart_account_id:
            raise UserError(_(
                "You must configure a Suspense Account on journal %s.",
                self.journal_id.display_name
            ))

        company = self.company_id
        company_currency = company.currency_id
        journal = self.journal_id
        journal_currency = journal.currency_id or company_currency

        amount = self.amount
        is_inbound = amount > 0

        # Company currency amount
        if journal_currency == company_currency:
            company_amount = amount
        else:
            company_amount = journal_currency._convert(
                amount, company_currency, company, self.date
            )

        abs_amount = abs(company_amount)
        sign = 1 if company_amount > 0 else -1

        # =====================================================
        # 1️⃣ LIQUIDITY LINE (BANK)
        # =====================================================
        liquidity_vals = {
            'name': self.payment_ref,
            'move_id': self.move_id.id,
            'partner_id': self.partner_id.id,
            'account_id': journal.default_account_id.id,
            'currency_id': journal_currency.id,
            'cash_move_type_id': self.cash_move_type_id.id,
            'amount_currency': abs_amount * sign,
            'debit': abs_amount if is_inbound else 0.0,
            'credit': abs_amount if not is_inbound else 0.0,
        }

        # =====================================================
        # NO TAX → NORMAL BEHAVIOR
        # =====================================================
        if not self.tax_ids:
            counterpart_vals = {
                'name': self.payment_ref,
                'account_id': counterpart_account_id,
                'move_id': self.move_id.id,
                'partner_id': self.partner_id.id,
                'debit': abs_amount if not is_inbound else 0.0,
                'credit': abs_amount if is_inbound else 0.0,
                'amount_currency': -abs_amount * sign
            }
            return [liquidity_vals, counterpart_vals]

        # =====================================================
        # TAX SPLIT
        # =====================================================
        tax = self.tax_ids[0]  # single tax support

        tax_result = tax.compute_all(
            abs_amount,
            currency=company_currency,
            quantity=1.0,
            partner=self.partner_id,
        )

        net_amount = tax_result['total_excluded']
        tax_amount = tax_result['taxes'][0]['amount']

        # =====================================================
        # 2️⃣ NET LINE
        # =====================================================
        net_vals = {
            'name': self.payment_ref,
            'account_id': counterpart_account_id,
            'move_id': self.move_id.id,
            'partner_id': self.partner_id.id,
            'debit': net_amount if not is_inbound else 0.0,
            'credit': net_amount if is_inbound else 0.0,
            'amount_currency': -net_amount * sign,
        }

        # =====================================================
        # 3️⃣ TAX LINE
        # =====================================================
        tax_account = tax.invoice_repartition_line_ids.filtered(
            lambda x: x.repartition_type == 'tax'
        )[0].account_id

        tax_vals = {
            'name': u'Татвар',
            'account_id': tax_account.id,
            'move_id': self.move_id.id,
            'partner_id': self.partner_id.id,
            'debit': tax_amount if not is_inbound else 0.0,
            'credit': tax_amount if is_inbound else 0.0,
            'amount_currency': -tax_amount * sign,
        }

        # =====================================================
        # FINAL SAFETY CHECK (100% BALANCED)
        # =====================================================
        total_debit = (
            liquidity_vals['debit'] +
            net_vals['debit'] +
            tax_vals['debit']
        )

        total_credit = (
            liquidity_vals['credit'] +
            net_vals['credit'] +
            tax_vals['credit']
        )

        diff = round(total_debit - total_credit, 2)

        if diff != 0:
            # adjust tax line automatically to force balance
            if diff > 0:
                tax_vals['credit'] += diff
            else:
                tax_vals['debit'] += abs(diff)

        return [liquidity_vals, net_vals, tax_vals]

    def _compute_counterpart_account_name(self):
        for obj in self:
            if not obj.move_id:
                obj.move_account_names = False
                continue
            move_account_names = ', '.join(l.code + ' ' + l.name
                for l in obj.move_id.line_ids.mapped('account_id')
            )
            obj.move_account_names = move_account_names

    def _compute_company_amount(self):
        for obj in self:
            if obj.move_id:
                obj.company_amount = sum(
                    obj.move_id.line_ids.filtered(
                        lambda l: l.account_id == obj.journal_id.default_account_id
                    ).mapped('balance')
                )
            else:
                obj.company_amount = 0