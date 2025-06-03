# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    def print_cash_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.report',
            'report_name': 'l10n_mn_account_report.cash_order_report',
            'report_type': 'xlsx',
        }

    @api.depends('amount')
    def _compute_cash_move_type(self):
        for line in self:
            line.cash_move_type = 'in' if line.amount > 0 else 'out'