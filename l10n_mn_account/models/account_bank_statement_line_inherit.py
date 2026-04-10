# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_is_zero

class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    cash_move_type_id = fields.Many2one('account.cash.move.type', string='Cash move type', required=True)
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
    
        if not any(field_name in changed_fields for field_name in (
            'payment_ref', 'amount', 'amount_currency',
            'foreign_currency_id', 'currency_id', 'partner_id',
            'cash_move_type_id', 'tax_ids'
        )):
            return
    
        for st_line in self.with_context(skip_account_move_synchronization=True):
    
            liquidity_lines, suspense_lines, other_lines = st_line._seek_for_lines()
            
            journal = st_line.journal_id
            company_currency = journal.company_id.currency_id
            journal_currency = journal.currency_id or company_currency
            
            # ✅ FIX: determine counterpart account
            counterpart_account_id = (
                suspense_lines.account_id.id
                if suspense_lines
                else journal.suspense_account_id.id
            )
    
            # =====================================================
            # 1️⃣ GET DEFAULT LINES (ONLY 2 LINES)
            # =====================================================
            vals_list = st_line._prepare_move_line_default_vals(counterpart_account_id)
    
            liquidity_vals = vals_list[0]
            counterpart_vals = vals_list[1]
    
            # =====================================================
            # 2️⃣ APPLY TAX SPLIT (MODIFY COUNTERPART)
            # =====================================================
            tax_line_vals = []
            if st_line.tax_ids:
    
                tax = st_line.tax_ids[0]
    
                tax_res = tax.compute_all(
                    abs(st_line.amount),
                    currency=company_currency,
                    quantity=1.0,
                    partner=st_line.partner_id,
                )
    
                base_amount = tax_res['total_excluded']
                tax_amount = tax_res['taxes'][0]['amount']
    
                is_inbound = st_line.amount > 0
                
                debit = base_amount if not is_inbound else 0.0
                credit = base_amount if is_inbound else 0.0
                balance = debit - credit
                # ✅ adjust counterpart (BASE)
                counterpart_vals.update({
                    'debit': debit,
                    'credit': credit,
                    'amount_currency': balance,
                })
    
                # =====================================================
                # TAX ACCOUNT
                # =====================================================
                tax_account = tax.invoice_repartition_line_ids.filtered(
                    lambda x: x.repartition_type == 'tax'
                )[0].account_id
                debit = tax_amount if not is_inbound else 0.0
                credit = tax_amount if is_inbound else 0.0
                balance = debit - credit
                tax_line_vals.append((0, 0, {
                    'name': 'Татвар',
                    'account_id': tax_account.id,
                    'partner_id': st_line.partner_id.id,
                    'debit': debit,
                    'credit': credit,
                    'amount_currency': balance,
                }))
    
            # =====================================================
            # 3️⃣ BUILD MOVE LINES
            # =====================================================
            line_ids_commands = [
                (1, liquidity_lines.id, liquidity_vals),
            ]
    
            if suspense_lines:
                line_ids_commands.append((1, suspense_lines.id, counterpart_vals))
            else:
                line_ids_commands.append((0, 0, counterpart_vals))
    
            # remove old extra lines
            for line in other_lines:
                line_ids_commands.append((2, line.id))
    
            # add tax lines
            line_ids_commands.extend(tax_line_vals)
    
            # =====================================================
            # 4️⃣ WRITE MOVE
            # =====================================================
            st_line_vals = {
                'currency_id': (st_line.foreign_currency_id or journal_currency).id,
                'line_ids': line_ids_commands,
            }
    
            if st_line.move_id.journal_id != journal:
                st_line_vals['journal_id'] = journal.id
    
            if st_line.move_id.partner_id != st_line.partner_id:
                st_line_vals['partner_id'] = st_line.partner_id.id
            #st_line.move_id.button_draft()
            st_line.move_id.write(st_line_vals)
            
    

    

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
                rec.company_a,mount = 0.0