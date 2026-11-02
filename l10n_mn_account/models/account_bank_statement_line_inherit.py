# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_is_zero
from odoo.osv import expression

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
    cash_move_type_group = fields.Selection(related='cash_move_type_id.group', string='Мөнгөн гүйлгээний бүлэг')
    cash_move_type_state = fields.Selection([
        ('missing', 'Сонгоогүй'),
        ('wrong_direction', 'Чиглэл зөрсөн'),
        ('ok', 'Зөв'),
    ], string='Мөнгөн гүйлгээний төрлийн шалгалт', compute='_compute_cash_move_type_state',
        search='_search_cash_move_type_state')

    # Орлогын бүлэгт зөвхөн орлого (+), зарлагын бүлэгт зөвхөн зарлага (-) орно.
    # Ханшийн зөрүү, тайланд нөлөөлөхгүй бүлэг аль ч чиглэлд зөв.
    CASH_MOVE_INCOME_GROUPS = ('activities_income', 'investing_income', 'financing_income')
    CASH_MOVE_EXPENSE_GROUPS = ('activities_expense', 'investing_expense', 'financing_expense')

    @api.depends('amount', 'cash_move_type_id.group')
    def _compute_cash_move_type_state(self):
        for line in self:
            group = line.cash_move_type_id.group
            if not line.cash_move_type_id:
                line.cash_move_type_state = 'missing'
            elif (line.amount > 0 and group in self.CASH_MOVE_EXPENSE_GROUPS) or \
                    (line.amount < 0 and group in self.CASH_MOVE_INCOME_GROUPS):
                line.cash_move_type_state = 'wrong_direction'
            else:
                line.cash_move_type_state = 'ok'

    def _search_cash_move_type_state(self, operator, value):
        if operator not in ('=', '!=', 'in', 'not in'):
            raise UserError(_('Unsupported operator: %s') % operator)
        missing = [('cash_move_type_id', '=', False)]
        wrong = expression.OR([
            [('amount', '>', 0), ('cash_move_type_id.group', 'in', self.CASH_MOVE_EXPENSE_GROUPS)],
            [('amount', '<', 0), ('cash_move_type_id.group', 'in', self.CASH_MOVE_INCOME_GROUPS)],
        ])
        domains = {
            'missing': missing,
            'wrong_direction': wrong,
            'ok': expression.AND([[('cash_move_type_id', '!=', False)],
                                  expression.distribute_not(['!'] + expression.normalize_domain(wrong))]),
        }
        values = value if isinstance(value, (list, tuple)) else [value]
        result = expression.OR([domains[v] for v in values if v in domains]) or expression.FALSE_DOMAIN
        if operator in ('!=', 'not in'):
            result = expression.distribute_not(['!'] + expression.normalize_domain(result))
        return result


    # =====================================================
    # PREPARE MOVE LINES (FULL FIXED)
    # =====================================================
    def _prepare_move_line_default_vals(self, counterpart_account_id=None):
        self.ensure_one()

        journal = self.journal_id
        company = self.company_id

        if not counterpart_account_id:
            counterpart_account_id = journal.suspense_account_id.id

        if not counterpart_account_id:
            raise UserError(_(
                "You must configure a Suspense Account on journal %s.",
                journal.display_name
            ))

        company_currency = company.currency_id
        journal_currency = journal.currency_id or company_currency

        amount_currency = self.amount  # 👉 ORIGINAL валют
        is_inbound = amount_currency > 0

        # =====================================================
        # COMPANY CURRENCY CONVERSION
        # =====================================================
        if self.env.context.get("no_currency_compute"):
            balance = self.amount_currency
        else:
            if journal_currency == company_currency:
                balance = amount_currency
            else:
                balance = journal_currency._convert(
                    amount_currency,
                    company_currency,
                    company,
                    self.date
                )

        abs_balance = abs(balance)
        abs_amount_currency = abs(amount_currency)

        # =====================================================
        # 1️⃣ LIQUIDITY LINE
        # =====================================================
        liquidity_vals = {
            'name': self.payment_ref or '/',
            'move_id': self.move_id.id,
            'partner_id': self.partner_id.id,
            'account_id': journal.default_account_id.id,
            'currency_id': journal_currency.id,
            'amount_currency': abs_amount_currency if is_inbound else -abs_amount_currency,
            'debit': abs_balance if is_inbound else 0.0,
            'credit': abs_balance if not is_inbound else 0.0,
            'cash_move_type_id':  self.cash_move_type_id.id or False,
        }

        # =====================================================
        # NO TAX
        # =====================================================
        if not self.tax_ids:
            counterpart_vals = {
                'name': self.payment_ref or '/',
                'move_id': self.move_id.id,
                'partner_id': self.partner_id.id,
                'account_id': counterpart_account_id,
                'currency_id': journal_currency.id,
                'amount_currency': -abs_amount_currency if is_inbound else abs_amount_currency,
                'debit': abs_balance if not is_inbound else 0.0,
                'credit': abs_balance if is_inbound else 0.0,
            }
            return [liquidity_vals, counterpart_vals]

        # =====================================================
        # TAX CALCULATION (FIXED)
        # =====================================================
        tax = self.tax_ids[0]

        tax_res = tax.compute_all(
            abs_amount_currency,
            currency=journal_currency,
            quantity=1.0,
            partner=self.partner_id,
        )

        base_currency = tax_res['total_excluded']
        tax_currency = tax_res['taxes'][0]['amount']

        # convert to company currency
        base_balance = journal_currency._convert(base_currency, company_currency, company, self.date)
        tax_balance = journal_currency._convert(tax_currency, company_currency, company, self.date)

        # =====================================================
        # 2️⃣ BASE LINE
        # =====================================================
        counterpart_vals = {
            'name': self.payment_ref or '/',
            'move_id': self.move_id.id,
            'partner_id': self.partner_id.id,
            'account_id': counterpart_account_id,
            'currency_id': journal_currency.id,
            'amount_currency': -base_currency if is_inbound else base_currency,
            'debit': base_balance if not is_inbound else 0.0,
            'credit': base_balance if is_inbound else 0.0,
        }

        # =====================================================
        # 3️⃣ TAX LINE
        # =====================================================
        tax_account = tax.invoice_repartition_line_ids.filtered(
            lambda x: x.repartition_type == 'tax'
        )[0].account_id

        tax_vals = {
            'name': 'Татвар',
            'move_id': self.move_id.id,
            'partner_id': self.partner_id.id,
            'account_id': tax_account.id,
            'currency_id': journal_currency.id,
            'amount_currency': -tax_currency if is_inbound else tax_currency,
            'debit': tax_balance if not is_inbound else 0.0,
            'credit': tax_balance if is_inbound else 0.0,
        }

        # =====================================================
        # BALANCE SAFETY (IMPORTANT)
        # =====================================================
        total_debit = liquidity_vals['debit'] + counterpart_vals['debit'] + tax_vals['debit']
        total_credit = liquidity_vals['credit'] + counterpart_vals['credit'] + tax_vals['credit']

        diff = round(total_debit - total_credit, 2)

        if diff != 0:
            if diff > 0:
                tax_vals['credit'] += diff
            else:
                tax_vals['debit'] += abs(diff)

        return [liquidity_vals, counterpart_vals, tax_vals]

    # =====================================================
    # SYNCHRONIZE MOVE (FULL FIXED)
    # =====================================================
    def _synchronize_to_moves(self, changed_fields):
        if self._context.get('skip_account_move_synchronization'):
            return

        trigger_fields = (
            'payment_ref', 'amount', 'amount_currency',
            'foreign_currency_id', 'currency_id',
            'partner_id', 'tax_ids', 'cash_move_type_id'
        )

        if not any(f in changed_fields for f in trigger_fields):
            return

        for st_line in self.with_context(skip_account_move_synchronization=True):

            liquidity_lines, suspense_lines, other_lines = st_line._seek_for_lines()

            journal = st_line.journal_id
            company_currency = journal.company_id.currency_id
            journal_currency = journal.currency_id or company_currency

            counterpart_account_id = (
                suspense_lines.account_id.id
                if suspense_lines
                else journal.suspense_account_id.id
            )
            if 'amount_currency' in changed_fields:
                vals_list = st_line.with_context(no_currency_compute=True)._prepare_move_line_default_vals(counterpart_account_id)
            else:
                vals_list = st_line._prepare_move_line_default_vals(counterpart_account_id)

            liquidity_vals = vals_list[0]
            counterpart_vals = vals_list[1]
            tax_vals = vals_list[2] if len(vals_list) > 2 else None

            # =====================================================
            # BUILD COMMANDS
            # =====================================================
            commands = []

            # liquidity update
            commands.append((1, liquidity_lines.id, liquidity_vals))

            # counterpart
            if suspense_lines:
                commands.append((1, suspense_lines.id, counterpart_vals))
            else:
                commands.append((0, 0, counterpart_vals))

            # remove old lines
            for line in other_lines:
                commands.append((2, line.id))

            # add tax
            if tax_vals:
                commands.append((0, 0, tax_vals))

            # =====================================================
            # WRITE MOVE
            # =====================================================
            move_vals = {
                'line_ids': commands,
                'currency_id': journal_currency.id,
            }

            if st_line.move_id.partner_id != st_line.partner_id:
                move_vals['partner_id'] = st_line.partner_id.id

            st_line.move_id.write(move_vals)
            
    

    

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