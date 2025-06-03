# -*- coding: utf-8 -*-
from odoo import api, fields, models, SUPERUSER_ID, _
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"


class hr_penalty(models.Model):
    _name = 'hr.penalty'
    _inherit = ['mail.thread']
    _description = 'HR penalty' #Сахилга шийтгэл
    
    name = fields.Char('Last name')#Овог
    penalty_type = fields.Selection([
        ('penalty', 'Penalty'),#Сахилгын шийтгэл
        ('impropriety', 'Impropriety'),#Зөрчил
        ], 'Penalty type')#Төрөл
    penalty_name = fields.Many2one('hr.penalty.type', 'Penalty name')#Гаргасан зөрчил эсвэл Холбогдох хуулийн заалт
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.user.company_id)#Компани
    department_name = fields.Many2one('hr.department', 'Department')#Алба, хэлтэс
    position_name = fields.Many2one('hr.job', 'Position')#Албан тушаал
    date = fields.Date('Date', required=True,)#Сахилгын шийтгэл оноосон огноо
    
    decree_id = fields.Many2one('hr.decree', 'Decree')#Тушаал
    date_end = fields.Date('Date end')#Сахилгын шийтгэлгүйд тооцогдох хугацаа
    is_employee_accepted = fields.Boolean('Is employee accepted')#Ажилтан хүлээн зөвшөөрсөн эсэх
    nonaccepted_note = fields.Text('Nonaccepted note')#Зөвшөөрөөгүй тайлбар
    need_deliver_finance = fields.Boolean('Need deliver finance')#Санхүүд мэдээлэл илгээх
    
    
    penalty_select = fields.Many2one('hr.imposing.penalty', 'Penalty select', required=True)#Ногдуулсан шийтгэл
    note = fields.Text('Note')#Гаргасан зөрчлийн агуулга
    is_withhold_salary = fields.Boolean('Is withhold salary')#Цалингаас суутгах эсэх
    percent = fields.Float('Percent')#Цалингаас суутгах хувь
    amount = fields.Float('Amount')#Цалингаас суутгах дүн
    state = fields.Selection([
        ('nonapprove', 'Nonapprove'),
        ('approve', 'Approve'),
        ], 'State', default='nonapprove')#Төлөв
    
    department_id = fields.Many2one('hr.department', 'Department')#Хэлтэс
    hr_employee_id = fields.Many2one('hr.employee', 'First name', required=True)#Ажилтан
    hr_contract_id = fields.Many2one('hr.contract', 'Hr contract')#Хүний нөөцийн гэрээ

    def action_to_nonapprove(self):
        self.write({'state': 'nonapprove'})
        return True
    
    def action_to_approve(self):
        self.write({'state': 'approve'})
        return True
    
    @api.onchange('hr_employee_id','percent')
    def onchange_calculate(self):
        emp_obj = self.env['hr.employee']
        res = {}
        sum = 0
        contract_wage = 0
        if self.hr_employee_id and self.percent >= 0:
            if self.hr_employee_id.contract_id and self.hr_employee_id.contract_id.state == 'open':
                contract_wage = self.hr_employee_id.contract_id.wage
            else:
                contract_wage = 0
            sum = (self.percent * contract_wage) / 100
        res['amount'] = sum
        return {'value':res}
        
    @api.onchange('hr_employee_id')
    def onchange_penalty(self):
        res = {}
        if self.hr_employee_id:
            empl_obj = self.env['hr.employee']
            empl = empl_obj.browse(self.hr_employee_id.id)
            res['name'] = self.hr_employee_id.last_name
            res['company_id'] = self.hr_employee_id.company_id.id
            res['department_name'] = self.hr_employee_id.department_id.id
            res['position_name'] = self.hr_employee_id.job_id.id
            return {'value':res}

        
class hr_penalty_type(models.Model):
    _name = 'hr.penalty.type'
    _description = 'HR penalty type' #Гаргасан зөрчил

    name = fields.Char('Penalty name')#Гаргасан зөрчил
    penalty_code = fields.Char('Penalty code')#Гаргасан зөрчлийн код
    hr_employee_id = fields.Many2one('hr.employee', 'First name')#Ажилтан


class hr_imposing_penalty(models.Model):
    _name = 'hr.imposing.penalty'
    _description = 'HR imposing penalty'        #Ногдуулсан шийтгэл
    
    name = fields.Char('Imposing penalty')#Ногдуулах шийтгэл
    hr_employee_id = fields.Many2one('hr.employee', 'First name')#Ажилтан

