# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class VatIncomeType(models.Model):
    _name = 'vat.income.type'
    _description = 'VAT Income Type'

    company_id = fields.Many2one('res.company',string='Company',
                                default=lambda self: self.env.user.company_id)
    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code')