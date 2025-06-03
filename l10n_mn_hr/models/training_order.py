# -*- coding: utf-8 -*-
from odoo import api, fields, models, SUPERUSER_ID, tools, _
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"


        
class training_order(models.Model):
    _name = 'training.order'
    _description = 'Training order' #Сургалтын бүртгэл
    _inherit = ['mail.thread']
    
    name = fields.Char('Name')#Хүсч буй сургалтын нэр
    training_type = fields.Many2one('training.type', string='Sub type')#Сургалтын төрөл
    hr_employee_id = fields.Many2one('hr.employee', string='Hr employee')#Ажилтан
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)#Харъяалагдах компани
    state = fields.Selection([
        ('draft', 'Draft'),#Хүсэлт
        ('send', 'Send'),#Илгээгдсэн
        ('approved', 'Approved'),#Захиалга батлагдсан
        ('done', 'Done'),#Сургалт хийгдсэн
        ('cancel', 'Cancelled'),#Цуцлагдсан
        ], string='State',default='draft', tracking=1)#Төлөв
    
    employee_id = fields.Many2one('hr.employee', string='Employee')#Ажилтан
    position_id = fields.Many2one('hr.job', string='Position')#Албан тушаал
    department_id = fields.Many2one('hr.department', string='Department')#Хэлтэс
    note = fields.Text('Note')


    #training_fee_option_id = fields.Many2one('training.fee.options', string='Training Fee Option')

    def action_send(self):
        self.state = 'send'
    
    def action_cancel(self):
        self.state = 'cancel'

    def action_draft(self):
        self.state = 'draft'

    def action_approve(self):
        self.state = 'approved'

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        res = {}
        list = []
        if self.employee_id:
            if self.employee_id:
                res['employee_id'] = self.employee_id.id
                res['company_id'] = self.employee_id.company_id.id
                res['department_id'] = self.employee_id.department_id.id
                res['position_id'] = self.employee_id.job_id.id
        else:
            res['employee_id'] = False
            res['company_id'] = False
            res['department_id'] = False
            res['position_id'] = False
            
        return {'value':res}



class training_type(models.Model):
    _name = 'training.type'
    _description = 'Training type'  # Сургалтын төрөл

    name = fields.Char(string='Name', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True)  # Харъяалагдах компани