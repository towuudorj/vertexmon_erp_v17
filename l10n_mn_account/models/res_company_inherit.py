# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'
    
    income_currency_exchange_account_id = fields.Many2one('account.account','Income currency exchange account')
    expense_currency_exchange_account_id = fields.Many2one('account.account','Expense currency exchange account')
    
    