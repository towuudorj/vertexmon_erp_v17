# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
    
    
    
class DistributorRegister(models.Model):
    _name = 'distributor.register'
    _description = 'Distributor Register'

    name = fields.Char(string='Distributer name', required=True)
    code = fields.Char(string='Code', required=True)
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.user.company_id
    )
    