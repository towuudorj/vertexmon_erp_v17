    # -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class account_account(models.Model):
    _inherit = 'account.account'
    
    income_id=fields.Many2one('account.income.type', string='Income report type')
    balance_id=fields.Many2one('account.balance.type', string='Balance report type')
