# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models
from odoo import tools, _

class InsuranceType(models.Model):
    _name = 'insurance.type'
    _description = 'Insurance type'
    
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        default=lambda self: self.env.user.company_id
    )
    name = fields.Char(string='Insurance type')
    code = fields.Char(string='Code')
    insurance_percent_employee = fields.Float(string='Insurance percent employee')
    insurance_percent_employer = fields.Float(string='Insurance percent employer')