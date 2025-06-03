# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools


class VatDistrict(models.Model):
    _name = "vat.district"
    _description = 'Vat district'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    
    company_id = fields.Many2one('res.company',string='Company', 
                                 required=True, default=lambda self: self.env.company)
    name = fields.Char(string='Vat district', required=True)
    code = fields.Char(string='Vat code', required=True)
    parent_id = fields.Many2one('vat.district', string='Parent district')
    
    
    
    