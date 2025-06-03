# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
    
class CountryRegister(models.Model):
    _name = 'country.register'
    _description = 'Country register'
    
    company_id = fields.Many2one('res.company',string='Company', required=True,
                                 default=lambda self: self.env.company)
    name = fields.Char(string='Country', required=True)
    code = fields.Char(string='Code', required=True)