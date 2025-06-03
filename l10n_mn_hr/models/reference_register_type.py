# -*- coding: utf-8 -*-
from odoo import models, fields

class ReferenceRegisterType(models.Model):
    _name = 'reference.register.type'
    _description = 'Reference Register Type'

    name = fields.Char(string='Reference Type', required=True)
    company = fields.Many2one('res.company', string='Company', required=True)
    code = fields.Char(string='Code')
    note = fields.Text(string='Note')
