# -*- coding: utf-8 -*-

import xlrd, base64, xlwt
from io import StringIO
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning

class DikritPayrollWizard(models.TransientModel):
    _name = 'dikrit.payroll.wizard'
    
    company_id = fields.Many2one('res.company',string=u'Компани',default=lambda self: self.env.user.company_id)
    percent = fields.Float(string=u'Хувь',required=True)
    reg_date = fields.Date(string=u'Огноо',required=True,default=fields.Date.context_today)
    
    
    
    def action_compute(self):
        context = self._context
        employee_obj = self.env['hr.employee']
        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        contract_obj = self.env['hr.contract']
        employee = employee_obj.browse(context.get('active_ids', []))
        for emp in employee:
            invoice_line_ids = []
            in_invoice_vals_list = []
            position_id = self.env['account.fiscal.position'].get_fiscal_position(emp.user_id.partner_id.id)
            contract = contract_obj.search([('employee_id','=',emp.id),('state','=','open')])
            amount = (contract.wage/100.0)*self.percent
            invoice_db_line_ids = {
                                'quantity':1,
                                 'partner_id': emp.user_id.partner_id.id,
                                'company_id':self.company_id.id,
                                'debit':amount,
                                'name':u'Дикрит',
                                'account_id':emp.dikrit_debit_account_id.id,
                                }
            invoice_cr_line_ids = {
                                'quantity':1,
                                 'partner_id': emp.user_id.partner_id.id,
                                'company_id':self.company_id.id,
                                'credit':amount,
                                'name':u'Дикрит',
                                'account_id':emp.dikrit_credit_account_id.id,
                                }
            move = move_obj.search([('partner_id','=',emp.user_id.partner_id.id),('invoice_date','=',self.reg_date),('journal_id','=',self.journal_id.id)])
            if move:
                raise UserError(_(u"%s ажилтных сард нэг удаа үүсэх бөгөөд үүссэн эсэхээ шалгана уу"%emp.user_id.partner_id.id))
            else:
                move_obj.create({
                            'partner_id':emp.user_id.partner_id.id,
                            'invoice_date':self.reg_date,
                            'journal_id':contract.journal_id.id,
                            'invoice_type':'other',
                            'amount_total':amount,
                            'state':'draft',
                            'fiscal_position_id': position_id,
                            'user_id':self.env.uid,
                            'company_id':self.company_id.id,
                            'line_ids': [(0, 0, invoice_db_line_ids), (0, 0, invoice_cr_line_ids)],
                            })
            
        
        
        