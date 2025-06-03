# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    is_po_return = fields.Boolean(string='Is purchase return')
    is_so_return = fields.Boolean(string='Is sale return')
    default_debit_account_id = fields.Many2one('account.account', string='Debit account')
    default_credit_account_id = fields.Many2one('account.account', string='Credit account')
    type = fields.Selection(selection=[('sale', 'Sales'),
                                        ('purchase', 'Purchase'),
                                        ('cash', 'Cash'),
                                        ('bank', 'Bank'),
                                        ('general', 'Miscellaneous'),
                                        ('opening','Opening/close'),
                                        ('salary', 'Salary'),
                                        ('asset','Asset')])