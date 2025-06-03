# -*- coding: utf-8 -*-

from odoo import fields, models, api


class AccountCashMoveType(models.Model):
     _name = 'account.cash.move.type'
     _description = 'Cash Move Type'
     
     TYPE_SELECTION = [
         ('activities_income', 'Cash flows income from operating activities'),
         ('activities_expense', 'Cash flows expense from operating activities'),
         ('investing_income', 'Cash flows income from investing activities'),
         ('investing_expense', 'Cash flows expense from investing activities'),
         ('financing_income', 'Cash flows income from financing activities'),
         ('financing_expense', 'Cash flows expense from financing activities'),
         ('dummy', 'Non affects in statements')
     ]
     name = fields.Char(string='Cash move type', required=True)
     mn_type = fields.Selection([('tbb','TBB'),
                                 ('aan','AAN')],string='Type')
     group = fields.Selection(TYPE_SELECTION, string='Group', required=True)
     code = fields.Char(string='Code')
     sequence = fields.Integer(string='Sequence')
     description = fields.Text(string='Description')
     company_id = fields.Many2one('res.company', string='Company', required=True,
                                  default=lambda self: self.env.user.company_id)
     debit_account_ids = fields.Many2many('account.account','debit_cash_account_rel','account_id','debit_cash_id', string='Debit account')
     credit_account_ids = fields.Many2many('account.account','credit_cash_account_rel','account_id','credit_cash_id', string='Credit account')



     @api.depends('name', 'code')
     def _compute_display_name(self):
        for cash in self:
            cash.display_name = '{}{}'.format(cash.code and '[%s] ' % cash.code or '', cash.name)
     