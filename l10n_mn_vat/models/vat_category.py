# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools



class VatCategory(models.Model):
    _name = 'vat.category'
    _description = 'Vat category'
    _order = 'code'
    
    name = fields.Char(string='Category name')
    code = fields.Char(string='Category code')
    parent_id = fields.Many2one('vat.category',string='Parent')
    company_id = fields.Many2one('res.company',string='Company', 
                                 default=lambda self: self.env.user.company_id)
    type = fields.Selection([('vat_zero','Vat zero'),
                             ('vat_free','Vat free'),
                             ('product_list','Product list')],string='Type')