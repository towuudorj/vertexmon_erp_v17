# -*- coding: utf-8 -*-
##############################################################################
#
#    ShineERP, Enterprise Management Solution    
#    Copyright (C) 2007-2012 ShineERP Co.,ltd (<http://www.erp.mn>). All Rights Reserved
#
#    Address : Suhkbaatar District, National ITPark, ShineERP LLC
#    Email : info@erp.mn
#    Phone : 976 + 11-318043
#
##############################################################################

import time
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta

from odoo import api, fields, models
from odoo import tools, _
from odoo.exceptions import ValidationError, AccessError
from odoo.modules.module import get_module_resource


class hr_payroll_prepayment(models.Model):
    _name = 'hr.payroll.prepayment'
    _description = 'Payroll Prepayment'
    
    now_date = fields.Date('Now date')
    start_date = fields.Date('Date',required=True)
    end_date = fields.Date('End date',required=True)
    name = fields.Char(u'Гүйлгээний утга',required=True)
    type = fields.Char(u'Гүйлгээний төрөл',required=True)
    dep_id = fields.Many2one('hr.department','Hr department')
    company_id = fields.Many2one('res.company','Company',required=True)
    create_user = fields.Many2one('hr.employee','Employee',required=True)
    state = fields.Selection([('draft','Draft'),
                              ('confirm','Confirm')],'State')
    percent = fields.Float('Prepayment payroll percent')
    journal_id = fields.Many2one('account.journal','Journal',required=True)
    line_id = fields.One2many('hr.payroll.prepayment.line','prepayment_id','Hr payroll prepayment line')
                
    
    def button_click(self):
        hr_emp = self.env['hr.employee']
        hr_cont = self.env['hr.contract']
        line = self.env['hr.payroll.prepayment.line']
        
        obj = self.browse(cr, uid, ids)[0]
        if obj.dep_id.id !=False:
            hr_emp_id = hr_emp.search( [('company_id','=',obj.company_id.id),('department_id','=',obj.dep_id.id)])
        else:
            hr_emp_id = hr_emp.search( [('company_id','=',obj.company_id.id)])
        pre_pay = 0
        if hr_emp_id != []:
            for hr in hr_emp.browse(cr, uid, hr_emp_id):
                hr_cont_id = hr_cont.search([('employee_id','=',hr.id)],order="job_id")
                if  hr_cont_id != []:
                    for payroll in hr_cont.browse( hr_cont_id):
                        pre_pay = (payroll.wage * obj.percent)/100
                        line_id = line.search( [('prepayment_id','=',obj.id),('name','=',hr.id)])
                        if line_id ==[]:
                            line.create(cr, uid, {'name':hr.id,
                                                  'prepayment_payroll':pre_pay,
                                                  'prepayment_id':obj.id,
                                                  })
                else:
                   raise osv.except_osv(_(u'Анхааруулга'),_(u'%s -ны %s ажилтан дээр хөдөлмөрийн гэрээ үүсээгүй байна.')%(obj.company_id.name,hr.name))

                    
        return True
    
    def action_confirm(self):
        journal_obj = self.env['account.journal']
        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        obj = self.browse(cr, uid, ids)[0]
        period_id = self.env['account.period'].find(cr, uid, dt=obj.now_date)[0]
        date = obj.now_date
        move_id = move_obj.create({
                                  'journal_id':obj.journal_id.id,
                                  'period_id':period_id,
                                  'date':date,
                                  })
        debit_account = None
        credit_account = None
        if obj.journal_id.default_debit_account_id.id != False:
            debit_account = obj.journal_id.default_debit_account_id.id
        else:
            raise osv.except_osv(_(u'Анхааруулга'),_(u'Урьдчилгаа цалингийн сонгосон журналын debit эсвэл credit дансыг тохируулаагүй байна.'))

        if obj.journal_id.default_credit_account_id.id !=False:
            credit_account = obj.journal_id.default_credit_account_id.id
        else:
            raise osv.except_osv(_(u'Анхааруулга'),_(u'Урьдчилгаа цалингийн сонгосон журналын debit эсвэл credit дансыг тохируулаагүй байна.'))

        for line in obj.line_id:
            if line.name:
                #-------------------------------------------- partner_ids = None
                #-------------------- partner_obj = self.pool.get('res.partner')
                # partner_id = partner_obj.search(cr, uid, [('user_id','=',line.name.user_id.id)])
                #--------------------- if partner_id !=None and partner_id !=[]:
                    #---------------------------------- partner_ids = partner_id
                move_line_obj.create( {
                                               'name':u'Урьдчилгаа цалин %s'%line.name.name,
                                               'move_id':move_id,
                                               'debit':line.hand_give,
                                               'credit':0.0,
                                               'amount_currency':0,
                                              # 'partner_id':partner_ids,
                                             #  'currency_id':obj.company_id.currency_id.id,
                                               'state':'valid',
                                               'account_id':debit_account,
                                               'date':date,
                                               'company_id': obj.company_id.id,
                                               
                                               })
                move_line_obj.create({
                                                'name':u'Урьдчилгаа цалин %s'%line.name.name,
                                                'move_id':move_id,
                                               'debit':0.0,
                                               'credit':line.hand_give,
                                               'amount_currency':0,
                                             #  'partner_id':partner_ids,
                                           #    'currency_id':obj.company_id.currency_id.id,
                                               'state':'valid',
                                               'account_id':credit_account,
                                               'date':date,
                                               'company_id': obj.company_id.id,
                                               })
        self.write(cr, uid, ids[0],{'state':'confirm',})
        return True
    def action_cancel(self):
        self.write({'state':'draft'})
        return True
    def action_print(self):
        if context is None:
            context = {}
        obj = self.browse(ids)[0]
        res = []
        for lin in obj.line_id:
            res.append(lin.id)
        context['start_date'] = obj.start_date
        context['end_date'] = obj.end_date
        context['line_id'] = res
        context['company'] = obj.company_id.name
        context['create_by'] = obj.create_user.last_name[0]+'.'+obj.create_user.name
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'payroll.prepayment.report',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
            'nodestroy': True,
        }



class hr_payroll_prepayment_line(models.Model):
    _name = 'hr.payroll.prepayment.line'
    _description = 'HR payroll prepayment line'
    
    def _get_hand_give(self):
        res = {}
        total = 0
        for line in self:
            total = line.prepayment_payroll-line.other_payment
            res[line.id] = total
        return res
    
    name = fields.Many2one('hr.employee',string='Employee name',required=True)
    is_bank = fields.Boolean(string='Is bank')
    prepayment_payroll = fields.Float(string='Prepayment payroll',required=True)
    other_payment = fields.Float('Other payment')
    hand_give = fields.Float(compute="_get_hand_give", string='At hand give')
    prepayment_id = fields.Many2one('hr.payroll.prepayment',string='Hr payroll prepayment')
                   
