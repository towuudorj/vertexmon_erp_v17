# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from datetime import date, datetime, time
from datetime import timedelta
from odoo.exceptions import UserError
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"

class PayrollBonus(models.Model):
    _name = 'payroll.bonus'
    _inherit = ['mail.thread']
    _description = "Employee payroll bonus"
    
    now_date = fields.Date(string='Register date', 
                           default=fields.Date.context_today)
    start_date = fields.Date(string='Start date', required=True,
                            default=fields.Date.context_today)
    end_date = fields.Date(string='End date', required=True,
                            default=fields.Date.context_today)
    name = fields.Char(string='Name', required=True)
    dep_id = fields.Many2one('hr.department', string='Department', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                default=lambda self: self.env.user.company_id)
    create_user = fields.Many2one('res.users', string='Register employee', required=True,
                                  default=lambda self: self.env.user,)
    state = fields.Selection([('draft','Draft'),
                              ('confirm','Confirm')], string='State', default='draft')
    percent = fields.Float(string='Percent')
    line_id = fields.One2many('payroll.bonus.line','bonus_id',string='Hr payroll bonus line')
    type = fields.Selection([('BONUSM','Bonus month'),
                             ('BONUSY','Bonus year')], string='Type', required=True)

    def action_cancel(self):
        self.write({'state':'draft'})
        return True
    
    
    def action_confirm(self):
        self.write({'state':'confirm'})
        
    
    def button_click(self):
        hr_emp = self.env['hr.employee']
        hr_cont = self.env['hr.contract']
        line = self.env['payroll.bonus.line']
        hour_record_obj = self.env['hr.hour.record']
        
        obj = self.browse(self.id)
        d = datetime.strptime(str(self.start_date), DATE_FORMAT)
        s_date = d.replace(minute=0, hour=0, second=1) - timedelta(hours=8)
        e_d = datetime.strptime(str(self.end_date), DATE_FORMAT)
        e_date = e_d.replace(minute=59, hour=23,second=59) - timedelta(hours=8)
        if obj.dep_id.id !=False:
            hr_emp_id = hr_emp.search( [('company_id','=',obj.company_id.id),('department_id','=',obj.dep_id.id)])
            hour_id = hour_record_obj.search([('company_id','=',obj.company_id.id),('department','=',obj.dep_id.id),('start_date','>=',str(s_date)),('end_date','<=',str(e_date)),('state','=','done')])
        else:
            hr_emp_id = hr_emp.search( [('company_id','=',obj.company_id.id)])
            hour_id = hour_record_obj.search([('company_id','=',obj.company_id.id),('start_date','>=',str(s_date)),('end_date','<=',str(e_date)),('state','=','done')])
        if hour_id==False and hour_id==[]:
            raise UserError((u"Цагийн бүртгэл үүсгээгүй эсвэл батлагдаагүй байгаа тул шалгана уу!"))
        
        if hr_emp_id != []:
            for hr in hr_emp_id:
                pre_pay = 0
                hr_cont_id = hr_cont.search([('employee_id','=',hr.id)],order="job_id")
                if  hr_cont_id.id != [] and hr_cont_id.id !=False:
                    work_time = 0.0
                    worked_time = 0.0
                    for payroll in hr_cont_id:
                        
                        for hour in hour_id:
                            for tm in hour.line_id:
                                if tm.employee_id.id == hr.id:
                                    work_time = tm.total_time
                                    worked_time = tm.due_time
                        if work_time >0.0 and worked_time >0.0:
                            if work_time >=worked_time:
                                pre_pay = (payroll.wage/100.0)*self.percent
                            else:
                                
                                
                                pre_pay = (((payroll.wage/worked_time)*work_time)/100)*self.percent
                        #else:
                        #    raise UserError((u"Ажилласан цаг болон ажиллах ёстой цаг 0 их байх ёстойг анхаарна  уу!"))
                            
                        line_id = line.search([('bonus_id','=',self.id),('name','=',hr.id)])
                                    
                        if line_id.id==False or line_id.id == []:
                            line.create({ 
                                          'name':hr.id,
                                          'amount':pre_pay,
                                          'worked_time':worked_time,
                                          'work_time':work_time,
                                          'bonus_id':obj.id,
                                          })
                        else:
                            line_id.write({ 
                                          'name':hr.id,
                                          'amount':pre_pay,
                                          'worked_time':worked_time,
                                          'work_time':work_time,
                                          'bonus_id':obj.id,
                                          })
                else:
                   raise UserError(u'%s -ны %s ажилтан дээр хөдөлмөрийн гэрээ үүсээгүй байна.'%(obj.company_id.name,hr.name))

                    
        return True

class PayrollBonusLine(models.Model):
    _name = 'payroll.bonus.line'
    _inherit = ['mail.thread']
    _description = "Employee payroll bonus line"
    
    
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        default=lambda self: self.env.user.company_id
    )
    name = fields.Many2one('hr.employee',string='Employee', required=True)
    amount = fields.Float('Amount', required=True)
    work_time = fields.Float(string='Work time', readonly=True)
    worked_time = fields.Float(string='Worked time', readonly=True)
    bonus_id = fields.Many2one('payroll.bonus',string='Hr payroll bonus')
    
    
    
    
    
    
    