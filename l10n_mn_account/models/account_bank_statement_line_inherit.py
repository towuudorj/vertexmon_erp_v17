# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    cash_move_type_id = fields.Many2one('account.cash.move.type', string='Cash move type')
    move_account_names = fields.Char(compute='_compute_counterpart_account_name', string='Account names')
    company_amount = fields.Float(compute='_compute_company_amount', string='Company amount')

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