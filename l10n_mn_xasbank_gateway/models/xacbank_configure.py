# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
import json, requests

class XacBankConfigure(models.Model):
    _name = "xacbank.configure"
    _description = "XacBank CGW Configure"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True)
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.user.company_id
    )
    config_url = fields.Char(string='Config URL', required=True)
    username = fields.Char(string='Username', required=True)
    password = fields.Char(string='Password', required=True)
    code = fields.Char(string='System Code', required=True)
    statement_url = fields.Char(string='Statement URL', required=True)
    requestId = fields.Char(string='Request id')
    keyfield = fields.Char(string='Key field')
    

    
    



    

