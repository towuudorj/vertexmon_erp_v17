# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo import tools, _

from datetime import date
from datetime import timedelta
from datetime import datetime
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
ATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"


class HrPayrollPrepayment(models.Model):
    _name = 'hr.payroll.prepayment'
    _inherit = ['mail.thread']
    _description = 'Hr payroll prepayment register'
    
    now_date = fields.Date(string='Register date', default=fields.Date.context_today)
    start_date = fields.Date('Start Date',required=True, default=fields.Date.context_today)
    end_date = fields.Date('End date',required=True, default=fields.Date.context_today)
    name = fields.Char(string=u'Move value',required=True)
    type = fields.Char(string=u'Move type', required=True)
    dep_id = fields.Many2one('hr.department', string='Department', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company)
    create_user = fields.Many2one('hr.employee','Employee', required=True)
    state = fields.Selection([('draft','Draft'),
                              ('confirm','Confirm')], 
                              string='State', default='draft')
    percent = fields.Float('Prepayment payroll percent')
    work_days = fields.Float(string='Work days', compute='_onchange_work_days')
    journal_id = fields.Many2one('account.journal', string='Journal', domain=[('type','in',('cash','bank'))],required=True)
    line_id = fields.One2many('hr.payroll.prepayment.line','prepayment_id',string='Hr payroll prepayment line')
    
    
    
    def workdaysub(uid,start_date, end_date):
        '''
        Calculate the number of working days between two dates inclusive
        (start_date <= end_date).
    
        The actual working days can be set with the optional whichdays
        parameter
        (default is MON-FRI)
        '''
        (MON, TUE, WED, THU, FRI, SAT, SUN) = range(7)
        whichdays=(MON,TUE,WED,THU,FRI)
        delta_days = (end_date - start_date).days + 1
        full_weeks, extra_days = divmod(delta_days, 7)
        num_workdays = (full_weeks + 1) * len(whichdays)
        for d in range(1, 8 - extra_days):
                    if (end_date + timedelta(d)).weekday() in whichdays:
                                    num_workdays -= 1
        return num_workdays
                
    @api.depends('start_date', 'end_date')
    def _onchange_work_days(self):
        for line in self:
            days = 0.0
            days = self.workdaysub(line.start_date,line.end_date)
            line.work_days = days
        
    
    def button_click(self):
        hr_emp = self.env['hr.employee']
        hr_cont = self.env['hr.contract']
        line = self.env['hr.payroll.prepayment.line']
        attendance_obj = self.env['hr.attendance']
        obj = self.browse(self.id)
        if obj.dep_id.id !=False:
            hr_emp_id = hr_emp.search( [('company_id','=',obj.company_id.id),('department_id','=',obj.dep_id.id)])
        else:
            hr_emp_id = hr_emp.search( [('company_id','=',obj.company_id.id)])
        pre_pay = 0
        if hr_emp_id != []:
            for hr in hr_emp_id:
                working_days = 0
                start_date = datetime.strptime(str(self.start_date),DATE_FORMAT)
                end_date = datetime.strptime(str(self.end_date),DATE_FORMAT)
                attendance_id = attendance_obj.search([('employee_id','=',hr.id),('check_in','>=',start_date),('check_out','<=',end_date)])
                for att in attendance_id:
                    working_days +=1

                hr_cont_id = hr_cont.search([('employee_id','=',hr.id)],order="job_id")
                if  hr_cont_id.id != [] and hr_cont_id.id !=False:
                    for payroll in hr_cont_id:
                        line_id = line.search([('prepayment_id','=',self.id),('name','=',hr.id)])
                        if working_days >0.0 and self.work_days >0.0:
                            pre_pay = (((payroll.wage * self.percent)/100.0)/self.work_days)*working_days
                        
                        if line_id.id==False or line_id.id == []:
                            line.create({ 
                                          'name':hr.id,
                                          'prepayment_payroll':pre_pay,
                                          'work_days':self.work_days,
                                          'working_days':working_days,
                                          'prepayment_id':obj.id,
                                          })
                else:
                   raise UserError(u'%s -ны %s ажилтан дээр хөдөлмөрийн гэрээ үүсээгүй байна.'%(obj.company_id.name,hr.name))

                    
        return True
    
    def action_confirm(self):
        journal_obj = self.env['account.journal']
        move_obj = self.env['account.move']
        obj = self.browse(self.id)
        date = obj.now_date
        self.write({'state':'confirm',
                    'name':self.env['ir.sequence'].next_by_code('hr.payroll.prepayment')
                    })
        return True
    
    def action_cancel(self):
        self.write({'state':'draft'})
        return True

    def action_print(self):
        context = dict(self._context)
        obj = self.browse(self.id)
        res = []
        for lin in obj.line_id:
            res.append(lin.id)
        context['start_date'] = obj.start_date
        context['end_date'] = obj.end_date
        context['line_id'] = res
        context['company'] = obj.company_id.name
        context['create'] = u'%s'%obj.create_user.last_name+'.'+obj.create_user.name
        return {
             
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'payroll.prepayment.report',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context':context,
            'nodestroy': True,
        }



class HrPayrollPrepaymentLine(models.Model):
    _name = 'hr.payroll.prepayment.line'
    _description = 'Hr payroll prepayment line register'
    
    
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        default=lambda self: self.env.user.company_id
    )
    name = fields.Many2one('hr.employee', string='Employee name', required=True)
    is_bank = fields.Boolean(string='Is bank')
    prepayment_payroll = fields.Float(string='Prepayment payroll', required=True)
    other_payment = fields.Float('Other payment')
    work_days = fields.Float(string='Work days')
    working_days = fields.Float(string='Working days')
    work_time = fields.Float(string='Work time')
    hand_give_amount = fields.Float(string='At hand give', compute='_compute_amount_total', store=True)
    prepayment_id = fields.Many2one('hr.payroll.prepayment', string='Hr payroll prepayment')
                   
                   
    @api.depends('prepayment_payroll', 'other_payment')
    def _compute_amount_total(self):
        for line in self:
            line.hand_give_amount = line.prepayment_payroll-line.other_payment
        