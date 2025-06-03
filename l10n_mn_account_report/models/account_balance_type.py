# -*- coding: utf-8 -*-
from odoo import models, fields, api, SUPERUSER_ID

class AccountBalanceType(models.Model):
    _name = 'account.balance.type'
    _description = 'Account balance type'
    _order = "sequence"
    
    name = fields.Char(string='Balance type name')
    number = fields.Char(string='Number')
    level = fields.Selection([('level1','Level 1'),
                              ('level2','Level 2'),
                              ('level3','Level 3'),
                              ('level4','Level 4'),],string='Level',required=True)
    sequence = fields.Char(string='Sequence')
    company_id = fields.Many2one('res.company','Company', required=True,
                                 default=lambda self: self.env.user.company_id)
    parent_id = fields.Many2one('account.balance.type',string='Parent type')
    
