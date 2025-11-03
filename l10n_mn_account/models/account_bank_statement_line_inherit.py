# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    cash_move_type_id = fields.Many2one('account.cash.move.type', string='Cash move type')

    