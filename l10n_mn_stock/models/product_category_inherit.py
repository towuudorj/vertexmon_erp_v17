# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
    
    
    
class ProductCategory(models.Model):
    _inherit= 'product.category'

    active = fields.Boolean(string='Active', default=True)