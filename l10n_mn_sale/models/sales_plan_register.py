# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class SalesPlanRegister(models.Model):
    _name = 'sales.plan.register'
    _description = 'Sales Plan Register'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    name = fields.Char(string='Name', required=True, default='/')
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.user.company_id)
    reg_date = fields.Date(string='Register date', 
                           default=fields.Date.today)
    start_date = fields.Date(string='Start date', required=True)
    end_date = fields.Date(string='End date', required=True)
    reg_user_id = fields.Many2one('res.users', 
                                  string='Register user', 
                                  default=lambda self: self.env.user)
    department_id = fields.Many2one('hr.department', string='Department', required=True)
    note = fields.Text(string='Note')
    state = fields.Selection([('draft', 'Draft'),
                                ('confirmed', 'Confirmed'),
                                ('cancel', 'Cancel')],
                                 string='State', default='draft', tracking=True)
    sales_plan_ids = fields.One2many('sales.plan', 'sales_plan_register_id', string='Sales plan')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True)


    def action_confirm(self):
        self.write({'state': 'confirmed'})


    
    def action_cancel(self):
        self.write({'state': 'cancel'})

class SalesPlan(models.Model):
    _name = 'sales.plan'
    _description = 'Sales Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True)
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.user.company_id)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity', required=True)
    unit_price = fields.Float(string='Unit price', required=True)
    total_price = fields.Float(string='Total price', required=True)
    sales_plan_register_id = fields.Many2one('sales.plan.register', string='Sales plan register')

    
