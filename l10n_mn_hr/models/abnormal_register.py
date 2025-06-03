# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo import tools, _

class AbnormalRegister(models.Model):
    _name = 'abnormal.register'
    _description = 'Work Environment Register'

    name = fields.Char('Name', required=True)
    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 default=lambda self: self.env.user.company_id) #Компани
    
