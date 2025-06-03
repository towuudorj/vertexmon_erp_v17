# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"

class ResCompany(models.Model):
    _inherit = 'res.company'
    
    location_id = fields.Many2one('location.register', string='Location', 
                                  required=True)
    ndsh_country_id = fields.Many2one('country.register', string='Ndsh Country', 
                                        required=True)