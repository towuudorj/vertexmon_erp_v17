# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
    
class FreightType(models.Model):
    _name = 'freight.type.register'

    name = fields.Char(string='Freight type', required=True)
    code = fields.Char(string='Code', required=True)
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.user.company_id
    )
    active = fields.Boolean(string='Active', default=True)

