# -*- coding: utf-8 -*-
from odoo import models, fields

class ContractTypeRegister(models.Model):
    _name = 'contract.type.register'
    _description = 'Contract Type Register'
    

    
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.user.company_id
    )
    code = fields.Char(string='Code', required=True)
    name = fields.Char(string='Contract type', required=True)
    description = fields.Text(string='Contract description')
