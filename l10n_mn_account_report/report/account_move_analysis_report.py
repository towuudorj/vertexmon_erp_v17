# -*- coding: utf-8 -*-

import io
import json
import xlsxwriter
from odoo import fields, models
from odoo.tools import date_utils

class AccountMoveAnalysis(models.TransientModel):
    _name = 'account.move.analysis'
    _description = 'Account move analysis'
   
    
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)
    start_date = fields.Date(string='Start date', required=True)
    end_date = fields.Date(string='End date', required=True)
    fiscalyear_id = fields.Many2one('account.fiscal.year', string='Fiscal year', required=True)
    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                    ('all', 'All Entries')
                                    ], string='State', required=True, default='posted')




    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'state':self.target_move,
            'fiscalyear_id': self.fiscalyear_id.id,
        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {
                     'model': 'account.move.analysis',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'account_move'}
        }
    
    
    def get_xlsx_report(self, data, response):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        head = workbook.add_format({
                                    'align': 'center', 
                                    'bold': True, 
                                    'font_size': 20,
                                    'valign': 'vcenter',
                                    })

        txt_center_border = workbook.add_format({
                                    'align': 'center',
                                    'border':1,
                                    'font_size': 12
                                })
        data_center = workbook.add_format({
                                    'align': 'center',
                                    'border':1,
                                    'font_size': 12
                                })
        
        data_right = workbook.add_format({
                                    'align': 'right',
                                    'border':1,
                                    'font_size': 12,
                                    'num_format': '#,##0.00'
                                })
        
        data_left = workbook.add_format({
                                    'align': 'left',
                                    'border':1,
                                    'font_size': 12
                                })

        txt_left_border = workbook.add_format({
                                    'align': 'left',
                                     'border':1,
                                    'font_size': 12
                                })
        txt_right_border = workbook.add_format({
                                    'align': 'right',
                                    'border':1,
                                    'font_size': 12,
                                    'bold': True,
                                    'num_format': '#,##0.00'
                                })
        txt_left_no_border = workbook.add_format({
                                    'align': 'left',
                                    
                                    'font_size': 12
                                })
        txt_right_no_border = workbook.add_format({
                                    'align': 'right',
                                    'font_size': 12
                                })
        sheet.set_column(3, 8, 20)
        sheet.set_column(2, 2, 40)
        sheet.set_column(1, 1, 10)
        sheet.write('A1', u'НХМаягт МХ-4', txt_left_no_border)
        sheet.write('I1', u'Сангийн сайдын 2018 оны 100 дугаар', txt_right_no_border)
        sheet.write('I2', u'тушаалын хавсралт',txt_right_no_border)
        sheet.merge_range('A3:I3', u'Гүйлгээ баланс тайлан', head)
        sheet.write('A4', u'Байгууллагын нэр: %s' % data['company_name'], txt_left_no_border)
        sheet.write('I4', u'Он сар өдөр: %s - %s'%(data['start_date'],data['end_date']), txt_right_no_border)
        



        sheet.merge_range('A6:A7', u'Д/д', txt_left_border)
        sheet.merge_range('B6:B7', u'Код', txt_center_border)
        sheet.merge_range('C6:C7', u'Данс', txt_center_border)
        sheet.merge_range('D6:E6', u'Эхний үлдэгдэл', txt_center_border)
        sheet.write('D7', u'Дт', txt_center_border)
        sheet.write('E7', u'Кд', txt_center_border)
        sheet.merge_range('F6:G6', u'Гүйлгээ', txt_center_border)
        sheet.write('F7', u'Дт', txt_center_border)
        sheet.write('G7', u'Кд', txt_center_border)
        sheet.merge_range('H6:I6', u'Эцсийн үлдэгдэл', txt_center_border)
        sheet.write('H7', u'Дт', txt_center_border)
        sheet.write('I7', u'Кд', txt_center_border)

        account_obj = self.env['account.account']
        account_type_obj = self.env['account.account.type']
        journal_obj = self.env['account.journal']
        journal_ids = journal_obj.search([('company_id','=',data['company_id'])])
        f_journals = journal_obj.search([('type','=','opening'),('company_id','=',data['company_id'])])
        journals = journal_obj.search([('type','!=','opening'),('company_id','=',data['company_id'])])

        f_journal = []
        states = ''
        if data['state'] == 'posted':
            states = ['posted']
        else:
            states = ['posted','draft']

        for fj in f_journals:
            f_journal.append(fj.id)
        journal = []
        for jour in journals:
            journal.append(jour.id)

        account_type = account_type_obj.search([('type','!=','view')])

        ty = []
        for li in account_type:
            ty.append(li.id)
        account_ids = account_obj.search([('company_id','=',data['company_id'])])
        fiscalyear_id = self.env['account.fiscal.year'].browse(data['fiscalyear_id'])

        total_balance = 0.0
        pre_debit_balance = 0.0
        pre_credit_balance = 0.0
        pre_credit_bal = 0.0
        debit_balance = 0.0
        credit_balance = 0.0
        total_credit_balance = 0.0
        total_debit_balance = 0.0
        number = 0
        rowx = 8
        for line in account_ids:
            first_balance  = 0.0
            last_balance = 0.0
            number +=1

            if len(states)==1:
                if str(fiscalyear_id.date_from) == str(data['start_date']):

                    if len(f_journal)==1:
                        self.env.cr.execute("""select sum(aml.debit) as debit, sum(aml.credit) as credit from account_move_line as aml 
                                                left join account_move as am  on am.id = aml.move_id where aml.date >='%s' and aml.date <= '%s' 
                                                and aml.account_id = %s and am.state='%s'
                                                and aml.journal_id = %s and am.company_id = %s"""%(fiscalyear_id.date_from,
                                                data['start_date'],line.id,states[0],f_journal[0],data['company_id']))
                        pre_balance = self._cr.dictfetchall()
                    else:
                        self.env.cr.execute("""select sum(aml.debit) as debit, sum(aml.credit) as credit from account_move_line as aml 
                                                left join account_move as am  on am.id = aml.move_id where aml.date >='%s' and aml.date <= '%s' 
                                                and aml.account_id = %s and am.state='%s'
                                                and aml.journal_id in %s and am.company_id = %s"""%(fiscalyear_id.date_from,
                                                data['start_date'],line.id,states[0],tuple(f_journal),data['company_id']))
                        pre_balance = self._cr.dictfetchall()
                else:

                    self.env.cr.execute("""select sum(aml.debit) as debit, sum(aml.credit) as credit from account_move_line as aml 
                                            left join account_move as am  on am.id = aml.move_id where aml.date >='%s' and aml.date < '%s' 
                                            and aml.account_id = %s and am.state='%s'
                                            and am.company_id = %s"""%(fiscalyear_id.date_from,
                                            data['start_date'],line.id,states[0],data['company_id']))
                    pre_balance = self._cr.dictfetchall()
            else:
                if fiscalyear_id.date_from == data['start_date']:
                    self.env.cr.execute("""select sum(debit) as debit, sum(credit) as credit from account_move_line as aml
                                            left join account_move as am on am.id=aml.move_id 
                                            where aml.date >='%s' and aml.date <= '%s' and aml.account_id = %s 
                                            and am.state in %s and aml.journal_id = %s and am.company_id = %s"""%(fiscalyear_id.date_from,
                                            data['start_date'],line.id,tuple(states),f_journal[0],data['company_id']))
                    pre_balance = self._cr.dictfetchall()
                else:
                    self.env.cr.execute("""select sum(debit) as debit, sum(credit) as credit from account_move_line as aml
                                        left join account_move as am on am.id=aml.move_id 
                                        where aml.date >='%s' and aml.date < '%s' and aml.account_id = %s 
                                        and am.state in %s and am.company_id = %s """%(fiscalyear_id.date_from,
                                        data['start_date'],line.id,tuple(states),data['company_id']))
                    pre_balance = self._cr.dictfetchall()
            sheet.write('A%s'%rowx, number, data_center)
            sheet.write('B%s'%rowx, u'%s'%line.code, data_center)
            sheet.write('C%s'%rowx, u'%s'%line.name, data_left)
            for li in pre_balance:
                if li['debit'] !=None and li['credit'] !=None:
                    first_balance = li['debit']-li['credit']
                elif li['debit'] !=None and li['credit'] ==None:
                    first_balance = li['debit']
                elif li['debit'] ==None and li['credit'] !=None:
                    first_balance = li['credit']
                    
                
                if first_balance > 0.0:
                    sheet.write('D%s'%rowx, first_balance or 0.0, data_right)
                    sheet.write('E%s'%rowx, 0.0, data_right)
                    pre_debit_balance +=first_balance
                else:
                    sheet.write('D%s'%rowx, 0.0, data_right)
                    sheet.write('E%s'%rowx, first_balance*(-1), data_right)
                    pre_credit_balance +=first_balance
                    
            if len(states)==1:
                if self.fiscalyear_id.date_from == self.start_date:
                    if len(journal)==1:
                        self.env.cr.execute("""select sum(aml.debit) as debit, sum(aml.credit) as credit from account_move_line as aml
                                    left join account_move as am on am.id=aml.move_id 
                                    where aml.date >='%s' and aml.date <='%s' and aml.account_id = %s and am.state='%s' 
                                    and am.journal_id = %s and am.company_id = %s
                                    """%(data['start_date'],data['end_date'],line.id,states[0],journal[0],data['company_id']))
                        move_balance = self._cr.dictfetchall()
                    else:
                        self.env.cr.execute("""select sum(aml.debit) as debit, sum(aml.credit) as credit from account_move_line as aml
                                    left join account_move as am on am.id=aml.move_id 
                                    where aml.date >='%s' and aml.date <='%s' and aml.account_id = %s and am.state='%s' 
                                    and am.journal_id in %s and am.company_id = %s
                                    """%(data['start_date'],data['end_date'],line.id,states[0],tuple(journal),data['company_id']))
                        move_balance = self._cr.dictfetchall()
                else:
                    self.env.cr.execute("""select sum(aml.debit) as debit, sum(aml.credit) as credit from account_move_line as aml
                                left join account_move as am on am.id=aml.move_id 
                                where aml.date >='%s' and aml.date <='%s' and aml.account_id = %s and am.state='%s' 
                                and am.journal_id in %s and am.company_id = %s
                                """%(data['start_date'],data['end_date'],line.id,states[0],tuple(journal),data['company_id']))
                    move_balance = self._cr.dictfetchall()
            else:
                if self.fiscalyear_id.date_from == self.start_date:
                    if len(journal)==1:
                        self.env.cr.execute("""select sum(aml.debit) as debit, sum(aml.credit) as credit from account_move_line as aml
                                    left join account_move as am on am.id=aml.move_id 
                                    where aml.date >='%s' and aml.date <='%s' and aml.account_id = %s and am.state in %s 
                                    and am.journal_id = %s and am.company_id = %s"""
                                    %(data['start_date'],data['end_date'],line.id,tuple(states),journal[0],data['company_id']))
                        move_balance = self._cr.dictfetchall()
                    else:
                        self.env.cr.execute("""select sum(aml.debit) as debit, sum(aml.credit) as credit from account_move_line as aml
                                    left join account_move as am on am.id=aml.move_id 
                                    where aml.date >='%s' and aml.date <='%s' and aml.account_id = %s and am.state in %s 
                                    and am.journal_id in %s and am.company_id = %s"""
                                    %(data['start_date'],data['end_date'],line.id,tuple(states),tuple(journal),data['company_id']))
                        move_balance = self._cr.dictfetchall()
                else:
                    self.env.cr.execute("""select sum(aml.debit) as debit, sum(aml.credit) as credit from account_move_line as aml
                                left join account_move as am on am.id=aml.move_id 
                                where aml.date >='%s' and aml.date <='%s' and aml.account_id = %s and am.state in %s 
                                and am.journal_id in %s and am.company_id = %s"""
                                %(data['start_date'],data['end_date'],line.id,tuple(states),tuple(journal),data['company_id']))
                    move_balance = self._cr.dictfetchall()
            for mli in move_balance:
                if mli['debit'] !=None:
                    debit_balance +=mli['debit']
                    if first_balance > 0.0:
                        last_balance = first_balance+mli['debit']
                    else:
                        last_balance = first_balance+mli['debit']
                
                if mli['credit'] !=None:
                    if mli['credit'] >0.0:
                        credit_balance +=mli['credit']
                    else:
                        credit_balance +=mli['credit']
                        
                    last_balance = last_balance-mli['credit']

                sheet.write('F%s'%rowx, mli['debit'] or 0.0, data_right)
                if mli['credit']!=None:
                    if mli['credit'] > 0.0:
                        sheet.write('G%s'%rowx, mli['credit'] or 0.0, data_right)
                    else:
                        sheet.write('G%s'%rowx, mli['credit']*(-1) or 0.0, data_right)
                else:
                    
                    sheet.write('G%s'%rowx, 0.0, data_right)
                if mli['credit']==None and mli['debit'] ==None:
                    last_balance = first_balance
                
            if last_balance > 0.0:
                sheet.write('H%s'%rowx, last_balance or 0.0, data_right)
                sheet.write('I%s'%rowx,  0.0, data_right)
                total_debit_balance +=last_balance
            else:
                last_balance = last_balance*(-1)
                sheet.write('H%s'%rowx,  0.0, data_right)
                sheet.write('I%s'%rowx, last_balance or 0.0, data_right)
                total_credit_balance +=last_balance
            total_balance +=last_balance
            rowx += 1
            number +=1
        sheet.merge_range('A%s:C%s'%(rowx,rowx), u'Дүн', txt_right_border)
        sheet.write('D%s'%rowx, pre_debit_balance or 0.0, txt_right_border)
        sheet.write('E%s'%rowx, pre_credit_balance or 0.0, txt_right_border)
        sheet.write('F%s'%rowx, debit_balance or 0.0, txt_right_border)
        sheet.write('G%s'%rowx, credit_balance or 0.0, txt_right_border)
        sheet.write('H%s'%rowx, total_debit_balance or 0.0, txt_right_border)
        sheet.write('I%s'%rowx, total_credit_balance or 0.0, txt_right_border)



        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

