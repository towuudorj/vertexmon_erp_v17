# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
    
    
    
class ItemGroup(models.Model):
    _name = 'item.group'
    _description = 'Item Group'

    
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.user.company_id
    )
    name = fields.Char(
        string='Item Group',
        required=True
    )
    code = fields.Char(
        string='Code',
        required=True
    )


    