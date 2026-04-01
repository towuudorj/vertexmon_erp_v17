# -*- coding: utf-8 -*-
from odoo import models, fields, api, SUPERUSER_ID

class account_income_type(models.Model):
    _name = 'account.income.type'
    _description = 'Account income type'
    
    name=fields.Char(string=u'Index', required=True)
    company_id=fields.Many2one('res.company', string='Company',
                               default=lambda self: self.env.user.company_id)
    sequence=fields.Char(string=u'Number')
    seq_type=fields.Selection([('1','1'),
                                 ('2','2'),
                                 ('3','3'),
                                 ('4','4'),
                                 ('5','5'),
                                 ('6','6')],string=u'Sequence')
    type=fields.Selection([('income','Income'),
                             ('expense','Expense'),
                             ('tax','Vat'),
                             ('other','Other')],string=u'Type')
    is_value_negative = fields.Boolean(string=u'Сөрөг дүнгээр нэмэгдэх эсэх')

