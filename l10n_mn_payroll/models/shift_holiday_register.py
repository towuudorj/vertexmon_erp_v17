# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, tools, _
from datetime import date, datetime, time
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

class ShiftHolidayRegister(models.Model):
    _name = 'shift.holiday.register'
    _inherit = ['mail.thread']
    _description = 'Shift holiday register'
    
    
    company_id = fields.Many2one('res.company', string='Company', readonly=True, required=True,
                                 default=lambda self: self.env.user.company_id)
    name = fields.Char(string='Number', readonly=True, default='/')
    account = fields.Char(string='Account')
    reg_date = fields.Date(string='Register date', readonly=True, required=True,
                                default=fields.Date.context_today)
    reg_user_id = fields.Many2one('res.users',string='Register user', readonly=True, required=True,
                                default=lambda self: self.env.user)
    line_ids = fields.One2many('shift.holiday.register.line','shift_holiday_id',readonly=True,string='Line ids')
    employee_id = fields.Many2one('hr.employee',string='Employee',readonly=True,required=True,)
    shift_days = fields.Integer(string='Shift holiday day',readonly=True,required=True,)
    start_date = fields.Date(string='Start date',readonly=True,required=True,)
    end_date = fields.Date(string='End date',readonly=True,required=True,)
    shift_start_date = fields.Date(string='Shift start date',readonly=True,required=True,default=fields.Date.context_today)
    total_amount = fields.Float(string='Total amount',compute="action_salary_holiday")
    give_amount = fields.Float(string='Give amount',readonly=True,compute="action_give_amount")
    average_amount = fields.Float(string='Average amount',compute="action_salary_average")
    total_working_days = fields.Integer(string='Total work days',readonly=True,)
    total_days = fields.Float(string='Total days',readonly=True,)
    ndsh_percent = fields.Float(string='Ndsh percent',readonly=True,)
    hhoat_percent = fields.Float(string='Hhoat percent',readonly=True)
    ndsh_amount = fields.Float(string='Ndsh amount',readonly=True, compute="action_ndsh_amount")
    hhoat_amount = fields.Float(string='Hhoat amount',readonly=True,compute="action_hhoat_amount")
    working_month = fields.Integer(string='Working month',readonly=True,)
    confirm_user_id = fields.Many2one('res.users',string='Confirm user',readonly=True)
    state = fields.Selection([('draft','Draft'),
                              ('confirmed','Confirmed')],string='State',default='draft')
    
    def action_hhoat_amount(self):
        for line in self:
            hhoat_amount = 0.0
            if line.total_amount >0.0 and line.hhoat_percent >0.0:
                hhoat_amount = ((line.total_amount-line.ndsh_amount)/100.0)*line.hhoat_percent
            line.hhoat_amount = hhoat_amount
    
    
    def action_ndsh_amount(self):
        for line in self:
            ndsh_amount = 0.0
            if line.total_amount >0.0 and line.ndsh_percent >0.0:
                ndsh_amount = (line.total_amount/100.0)*line.ndsh_percent
            line.ndsh_amount = ndsh_amount
    
    def action_salary_holiday(self):
        for list in self:
            amount = list.average_amount*list.shift_days
            list.total_amount = amount
    
    def action_give_amount(self):
        for line in self:
            give_amount = 0.0
            if line.total_amount >0.0:
                give_amount = line.total_amount-line.ndsh_amount-line.hhoat_amount
            line.give_amount = give_amount
                
            
            
    
    def action_salary_average(self):
        for list in self:
            amount = 0.0
            total_salary = 0.0
            total_day = 0.0
            for line in list.line_ids:
                total_salary +=line.amount
                total_day +=line.work_days
            if total_salary >0.0 and total_day >0.0:
                amount = total_salary/total_day
            list.average_amount = amount
            list.total_days = total_day
            
    
    def action_salary(self):
        payslip_obj = self.env['hr.payslip']
        leave_obj = self.env['hr.leave']
        leave_type_obj = self.env['hr.leave.type']
        line_obj = self.env['shift.holiday.register.line']
        payroll_ids = payslip_obj.search([('employee_id','=',self.employee_id.id),('date_to','>=',self.start_date),('date_to','<=',self.end_date),('state','=','done')],limit=self.working_month, order="date_to desc")
        status_id = leave_type_obj.search([('new_type','=','legal_leave')],limit=1)
        leave_ids = leave_obj.search([('request_date_from','=',self.shift_start_date),('employee_id','=',self.employee_id.id),('state','=','validate'),('holiday_status_id','=',status_id.id)])
        for list in self:
            if leave_ids.number_of_days:
                list.vacation_day = leave_ids.number_of_days
        working_obj = self.env['working.day.register']
        now_working_ids = working_obj.search([('state','=','confirmed'),('start_date','<=',self.end_date),('end_date','>=',self.end_date)])
        pre_working_ids = working_obj.search([('state','=','confirmed'),('start_date','<=',self.start_date),('end_date','>=',self.start_date)])
        total_working_days = 0.0
        total_work_day = 0.0
        for line in payroll_ids:
            year = str(line.date_from)[:4]
            month = str(line.date_from)[5:7]
            working_days = 0.0
            salary_amount = 0.0
            work_days = 0.0
            
            for wlines in pre_working_ids.line_ids:
                if int(month) == int(wlines.name) and int(year)==int(pre_working_ids.name):
                    working_days +=wlines.work_day
            
            for wline in now_working_ids.line_ids:
                if int(month) == int(wline.name) and int(year)==int(now_working_ids.name):
                    working_days +=wline.work_day
            for lines in line.line_ids:
                if lines.code == 'WD':
                    work_days +=lines.amount
                
                if lines.code == 'TCDS' or lines.code == 'TCDSA' or lines.code == 'TCDSI' or lines.code == 'TCDSMO' or lines.code == 'TCDSI8' or lines.code == 'TCDSIHC':
                    salary_amount +=lines.amount
                
            
                    
            line_obj.create({
                            'year':year,
                            'month':month,
                            'amount':salary_amount,
                            'working_days':working_days,
                            'work_days':work_days,
                            'shift_holiday_id':self.id,
                             })
            total_working_days +=working_days
            total_work_day +=work_days
        self.write({'total_working_days':total_working_days,
                    'total_days':total_work_day})
        return True
    
    def action_confirm(self):
        if self.shift_days >0.0 and self.line_ids!=False:
            self.write({'confirm_user_id':self.env.user.id,
                        'name':self.env['ir.sequence'].get('shift.holiday.register'),
                        'state':'confirmed'})
        else:
            raise UserError(_(u"Амрах хоног ороогүй байгаа тул оруулана уу!"))
        
    def action_cancel(self):
        self.write({'state':'draft'})

class ShiftHolidayRegisterLine(models.Model):
    _name = 'shift.holiday.register.line'
    _inherit = ['mail.thread']
    _description = 'Shift holiday register line'
    
    company_id = fields.Many2one('res.company',string='Company',
                                 default=lambda self: self.env['res.company']._company_default_get('shift.holiday.register.line'))
    year = fields.Integer(string='Year')
    month = fields.Integer(string='Month')
    working_days = fields.Float(string='Working days')
    work_days = fields.Float(string='Work days')
    amount = fields.Float(string='Amount')
    shift_holiday_id = fields.Many2one('shift.holiday.register',string='Shift holiday')
    
    
    
    