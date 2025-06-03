# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"

class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'
    
    is_salary_account = fields.Boolean(string=u'Salary give account')