# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class LocationRegister(models.Model):
    _name = 'location.register'
    _description = 'Location register'
    
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        default=lambda self: self.env.user.company_id
    )
    name = fields.Char(string='Location', required=True)
    code = fields.Char(string='Code', required=True)