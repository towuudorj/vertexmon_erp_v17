# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, tools, _
from datetime import date, datetime, time
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class WorkingDayRegister(models.Model):
    _name = 'working.day.register'
    _inherit = ['mail.thread']
    _description = 'Working day register'
    
    
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.user.company_id)
    name = fields.Char(string='Year', required=True)
    line_ids = fields.One2many('working.day.register.line','working_id', string='Working day line')
    start_date = fields.Date(string='Start date',  required=True)
    end_date = fields.Date(string='End date', required=True)
    state = fields.Selection([('draft','Draft'),
                              ('confirmed','Confirmed')],
                              string='State', default='draft')
    
    def action_confirm(self):
        if self.line_ids:
            self.write({'state':'confirmed'})
        else:
            raise UserError(u'Ажилласан сарын бүртгэл үүсгэнэ үү!')
        
        
    

class WorkingDayRegisterLine(models.Model):
    _name = 'working.day.register.line'
    _description = 'Working day register line'
    
    company_id = fields.Many2one('res.company',string='Company')
    name = fields.Char(string='Month')
    work_day = fields.Integer(string='Work day')
    working_id = fields.Many2one('working.day.register',string='Working day')
    
    
    





