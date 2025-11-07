# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
    
    
    
class ProductCategoryNew(models.Model):
    _name= 'product.category.new'
    _description = 'Product Category New'

    active = fields.Boolean(string='Active', default=True)
    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    parent_id = fields.Many2one('product.category.new', string='Parent Category')
    
