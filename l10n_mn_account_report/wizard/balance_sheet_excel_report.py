# -*- coding: utf-8 -*-

import io
import json
import xlsxwriter
from odoo import fields, models
from odoo.tools import date_utils

class balance_sheet_excel(models.TransientModel):
    """
        Санхүүгийн байдлын тайлан
    """
    _name = "balance.sheet.excel"
    _description = "Balance Sheet Report - Mongolia"
    
    company_id=fields.Many2one('res.company', string='Company', required=True, 
                               default=lambda self: self.env.user.company_id)
    date_from=fields.Date('Date Start',default=fields.Date.context_today)
    date_to=fields.Date("Date Stop",default=fields.Date.context_today)
    target_move=fields.Selection([('posted', 'All Posted Entries'),
                                         ('all', 'All Entries'),
                                        ], string='State', required=True, default='posted')
    
    

    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'start_date': self.date_from,
            'end_date': self.date_to,
            'state': self.target_move
        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {'model': 'cash.move.line.report',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'Account balance report'}
        }

    def get_xlsx_report(self, data, response):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        head = workbook.add_format({
                                    'align': 'center', 
                                    'bold': True, 
                                    'font_size': 20
                                    })
        txt = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'font_size': 12
                                })

        title = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'font_size': 12
                                })

        sheet.set_column(0, 8, 24)

        sheet.merge_range('A1:D1', u'САНХҮҮ БАЙДЛЫН ТАЙЛАН', head)
        sheet.write('A2', u"%s" % (data['company_name']), head)

        sheet.write('A3', u'(Аж ахуй нэгж, байгууллагын нэр)', head)
        sheet.write('D2', u'%s - %s' % (data['start_date'],data['end_date']), head)
        sheet.write('D5', u'(төгрөгөөр)', head)
        rowx = 6
        sheet.write('A%s'%rowx, u'Д/д', title)
        sheet.write(rowx, 1, u'Үзүүлэлт', title)
        sheet.write(rowx, 2, u'%s'%(data['start_date']), title)
        sheet.write(rowx, 3, u'%s'%(data['end_date']), title)
        rowx += 1
        





    def get_export_data(self):
        ''' Тайлангийн загварыг боловсруулж өгөгдлүүдийг
            тооцоолж байрлуулна.
        '''

        date_str = '%s-%s' % (
            datetime.strptime(str(self.date_from), '%Y-%m-%d').strftime('%Y.%m.%d'),
            datetime.strptime(str(self.date_to), '%Y-%m-%d').strftime('%Y.%m.%d')
        )
        
        ezxf = xlwt.easyxf
        styles = self.get_easyxf_styles()
        
        book = xlwt.Workbook(encoding='utf8')
        sheet = book.add_sheet(u'Санхүү байдлын тайлан')
        sheet.portrait = False
        data_style = ezxf('font: bold off; align: wrap on, vert centre, horiz centre; font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        data_bold = ezxf('font: bold on; align: wrap on, vert centre, horiz centre; font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        data_right = ezxf('font: bold off; align: wrap on, vert centre, horiz right; font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        data_left = ezxf('font: bold off; align: wrap on, vert centre, horiz left; font: height 220;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        data_bold_left = ezxf('font: bold on; align: wrap on, vert centre, horiz left; font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        data_bold_center = ezxf('font: bold on; align: wrap on, vert centre, horiz centre; font: height 220;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')

        
        sheet.write_merge(0, 0, 0, 3, u'САНХҮҮ БАЙДЛЫН ТАЙЛАН', ezxf('font: bold on; align: wrap off, vert centre, horiz centre;font: height 250'))
        sheet.write(2, 1, u'"%s" ХХК' % (self.company_id.name,), ezxf('font:bold on;align:wrap off,vert centre,horiz left;font: height 180'))

        sheet.write(3, 1, u'(Аж ахуй нэгж, байгууллагын нэр)', ezxf('font:bold on;align:wrap off,vert centre,horiz left;font: height 180'))
        sheet.write(2, 3, u'%s' % (date_str,), ezxf('font:bold on;align:wrap off,vert centre,horiz right;font: height 180'))
        sheet.write(5, 3, u'(төгрөгөөр)', ezxf('font:bold on;align:wrap off,vert centre,horiz right;font: height 180'))
        rowx = 6
        sheet.write(rowx, 0, u'Д/д', styles['heading_xf'])
        sheet.write(rowx, 1, u'Үзүүлэлт', styles['heading_xf'])
        sheet.write(rowx, 2, u'%s'%(datetime.strptime(str(self.date_from), '%Y-%m-%d').strftime('%Y-%m-%d')), styles['heading_xf'])
        sheet.write(rowx, 3, u'%s'%(datetime.strptime(str(self.date_to), '%Y-%m-%d').strftime('%Y-%m-%d')), styles['heading_xf'])
        rowx += 1
        
        account_move_obj = self.env['account.move']
        account_move_line_obj = self.env['account.move.line']
        balance_report_obj = self.env['account.balance.type']
        journal_obj = self.env['account.journal']
        balance_report_id = balance_report_obj.search([('company_id','=',self.company_id.id)])
        account_obj = self.env['account.account']
        if self.target_move =='posted':
            state = ['posted']
        else:
            state = ['posted','draft']
        num = 1
        
        for line in balance_report_id:
            sheet.write(rowx, 0, u'%s'%num,data_right)
            if line.level == 'level1':
                debit = 0.0
                credit = 0.0
                total = 0.0
                pdebit = 0.0
                pcredit = 0.0
                pre_total = 0.0
                sheet.write(rowx, 1, u'%s'%line.name,data_bold_left)
                if line.parent_id.id==False:
                    account_ids = account_obj.search([('balance_id','=',line.id),('company_id','=',self.company_id.id)])
                    if len(account_ids)>1:
                        accounts = tuple(ac.id for ac in account_ids)
                        if len(state)==1:
                            move_line_ids = account_move_line_obj.search([('company_id','=',self.company_id.id),('account_id','in',accounts),('date','>=',self.date_from),('date','<=',self.date_to),('parent_state','=',state)])
                            pre_move_line_ids = account_move_line_obj.search([('company_id','=',self.company_id.id),('account_id','in',accounts),('date','<=',self.date_from),('parent_state','=',state)])

                        else:
                            move_line_ids = account_move_line_obj.search([('company_id','=',self.company_id.id),('account_id','in',accounts),('date','>=',self.date_from),('date','<=',self.date_to),('parent_state','in',state)])
                            pre_move_line_ids = account_move_line_obj.search([('company_id','=',self.company_id.id),('account_id','in',accounts),('date','<=',self.date_from),('parent_state','in',state)])

                    else:
                        if len(state)==1:
                            move_line_ids = account_move_line_obj.search([('company_id','=',self.company_id.id),('account_id','=',account_ids.id),('date','>=',self.date_from),('date','<=',self.date_to),('parent_state','=',state)])
                            pre_move_line_ids = account_move_line_obj.search([('company_id','=',self.company_id.id),('account_id','=',account_ids.id),('date','<=',self.date_from),('parent_state','=',state)])
                           
                        else:
                            move_line_ids = account_move_line_obj.search([('company_id','=',self.company_id.id),('account_id','=',account_ids.id),('date','>=',self.date_from),('date','<=',self.date_to),('parent_state','in',state)])
                            pre_move_line_ids = account_move_line_obj.search([('company_id','=',self.company_id.id),('account_id','=',account_ids.id),('date','<=',self.date_from),('parent_state','in',state)])
                    
                    if len(move_line_ids)==1:
                        for mlines in move_line_ids:
                            debit +=mlines.debit
                        for mlines in move_line_ids:
                            credit += mlines.credit
                    else:
                        for mlines in move_line_ids:
                            credit += mlines.credit
                        for mlines in move_line_ids:
                            debit +=mlines.debit
                    
                    
                    total = debit - credit
                    if len(pre_move_line_ids)==1:
                        for pmlines in pre_move_line_ids:
                            pdebit +=pmlines.debit
                        for pmlines in pre_move_line_ids:
                            pcredit += pmlines.credit
                    else:
                        for pmlines in pre_move_line_ids:
                            pcredit += pmlines.credit
                        for pmlines in pre_move_line_ids:
                            pdebit +=pmlines.debit
                    
                    
                    pre_total = pdebit - pcredit
                    
                    sheet.write(rowx, 2, pre_total,data_right)
                    sheet.write(rowx, 3, total,data_right)
                num +=1
                rowx +=1
                
                
            elif line.level == 'level2':
                sheet.write(rowx, 1, u'%s'%line.name,data_bold_left)
                debit = 0.0
                credit = 0.0
                total = 0.0
                pdebit = 0.0
                pcredit = 0.0
                pre_total = 0.0
                balance_id = balance_report_obj.search([('parent_id','=',line.id)])
                for bline in balance_id:
                    account_ids = []
                    li_account_ids = account_obj.search([('balance_id','=',bline.id),('company_id','=',self.company_id.id)])
                    for acc in li_account_ids:
                        account_ids.append(acc.id)
                    line_balance_id = balance_report_obj.search([('parent_id','=',bline.id)])
                    for blines in line_balance_id:
                        line_account_ids = account_obj.search([('balance_id','=',blines.id),('company_id','=',self.company_id.id)])
                        for li in line_account_ids:
                            account_ids.append(li.id)
                        fline_balance_id = balance_report_obj.search([('parent_id','=',blines.id)])
                        for flines in fline_balance_id:
                            fline_account_ids = account_obj.search([('balance_id','=',flines.id),('company_id','=',self.company_id.id)])
                            for fli in fline_account_ids:
                                account_ids.append(fli.id)
                    
                    if account_ids!=[]:
                        if len(account_ids)>1:
                            if len(state)==1:
                                move_line_ids = account_move_line_obj.search([('company_id','=',self.company_id.id),('account_id','in',tuple(account_ids)),('date','>=',self.date_from),('date','<=',self.date_to),('parent_state','=',state)])
                                pre_move_line_ids = account_move_line_obj.search([('company_id','=',self.company_id.id),('account_id','in',tuple(account_ids)),('date','<=',self.date_from),('parent_state','=',state)])
                            else:
                                move_line_ids = account_move_line_obj.search([('company_id','=',self.company_id.id),('account_id','in',tuple(account_ids)),('date','>=',self.date_from),('date','<=',self.date_to),('parent_state','in',state)])
                                pre_move_line_ids = account_move_line_obj.search([('company_id','=',self.company_id.id),('account_id','in',tuple(account_ids)),('date','<=',self.date_from),('parent_state','in',state)])
                        else:
                            if len(state)==1:
                                move_line_ids = account_move_line_obj.search([('company_id','=',self.company_id.id),('account_id','=',account_ids[0]),('date','>=',self.date_from),('date','<=',self.date_to),('parent_state','=',state)])
                                pre_move_line_ids = account_move_line_obj.search([('company_id','=',self.company_id.id),('account_id','=',account_ids[0]),('date','<=',self.date_from),('parent_state','=',state)])
                            else:
                                move_line_ids = account_move_line_obj.search([('company_id','=',self.company_id.id),('account_id','=',account_ids[0]),('date','>=',self.date_from),('date','<=',self.date_to),('parent_state','in',state)])
                                pre_move_line_ids = account_move_line_obj.search([('company_id','=',self.company_id.id),('account_id','=',account_ids[0]),('date','<=',self.date_from),('parent_state','in',state)])
                            
                        if len(move_line_ids)==1:
                            for mlines in move_line_ids:
                                debit +=mlines.debit
                            for mlines in move_line_ids:
                                credit += mlines.credit
                        else:
                            for mlines in move_line_ids:
                                debit +=mlines.debit
                            for mlines in move_line_ids:
                                credit += mlines.credit
                                
                        if len(pre_move_line_ids)==1:
                            for pmlines in pre_move_line_ids:
                                pdebit +=pmlines.debit
                            for pmlines in pre_move_line_ids:
                                pcredit += pmlines.credit
                        else:
                            for pmlines in pre_move_line_ids:
                                pdebit +=pmlines.debit
                            for pmlines in pre_move_line_ids:
                                pcredit += pmlines.credit
                            
                    total = debit - credit
                    pre_total = pdebit - pcredit
                sheet.write(rowx, 2, pre_total, data_bold_center)
                sheet.write(rowx, 3, total, data_bold_center)
                num +=1
                rowx +=1
            elif line.level == 'level3':
                sheet.write(rowx, 1, u'%s'%line.name,data_left)
                debit = 0.0
                credit = 0.0
                total = 0.0
                pdebit = 0.0
                pcredit = 0.0
                pre_total = 0.0
                account_ids = account_obj.search([('balance_id','=',line.id),('company_id','=',self.company_id.id)])
                if len(account_ids)>1:
                    accounts = tuple(ac.id for ac in account_ids)
                    if len(state)==1:
                        move_line_ids = account_move_line_obj.search([('company_id','=',self.company_id.id),('account_id','in',accounts),('date','>=',self.date_from),('date','<=',self.date_to),('parent_state','=',state)])
                        pre_move_line_ids = account_move_line_obj.search([('company_id','=',self.company_id.id),('account_id','in',accounts),('date','<=',self.date_from),('parent_state','=',state)])
                    else:
                        move_line_ids = account_move_line_obj.search([('company_id','=',self.company_id.id),('account_id','in',accounts),('date','>=',self.date_from),('date','<=',self.date_to),('parent_state','in',state)])
                        pre_move_line_ids = account_move_line_obj.search([('company_id','=',self.company_id.id),('account_id','in',accounts),('date','<=',self.date_from),('parent_state','in',state)])
                else:
                    if len(state)==1:
                        move_line_ids = account_move_line_obj.search([('company_id','=',self.company_id.id),('account_id','=',account_ids.id),('date','>=',self.date_from),('date','<=',self.date_to),('parent_state','=',state)])
                        pre_move_line_ids = account_move_line_obj.search([('company_id','=',self.company_id.id),('account_id','=',account_ids.id),('date','<=',self.date_from),('parent_state','=',state)])
                    else:
                        move_line_ids = account_move_line_obj.search([('company_id','=',self.company_id.id),('account_id','=',account_ids.id),('date','>=',self.date_from),('date','<=',self.date_to),('parent_state','in',state)])
                        pre_move_line_ids = account_move_line_obj.search([('company_id','=',self.company_id.id),('account_id','=',account_ids.id),('date','<=',self.date_from),('parent_state','in',state)])
                    
                if len(move_line_ids)==1:
                    for mlines in move_line_ids:
                        credit +=mlines.credit
                    for mlines in move_line_ids:
                        debit +=mlines.debit
                else:
                    for mlines in move_line_ids:
                        debit += mlines.debit
                    for mlines in move_line_ids:
                        credit +=mlines.credit

                if len(pre_move_line_ids)==1:
                    for pmlines in pre_move_line_ids:
                        pcredit +=pmlines.credit
                    for pmlines in pre_move_line_ids:
                        pdebit +=pmlines.debit
                else:
                    for pmlines in pre_move_line_ids:
                        pdebit += pmlines.debit
                    for pmlines in pre_move_line_ids:
                        pcredit +=pmlines.credit
                        
                total = debit - credit
                pre_total = pdebit - pcredit
                sheet.write(rowx, 2, pre_total,data_right)
                sheet.write(rowx, 3, total,data_right)
                num +=1
                rowx +=1
            else:
                debit = 0.0
                credit = 0.0
                total = 0.0
                pdebit = 0.0
                pcredit = 0.0
                pre_total = 0.0
                sheet.write(rowx, 1, u'%s'%line.name,data_left)
                account_ids = account_obj.search([('balance_id','=',line.id),('company_id','=',self.company_id.id)])
                if len(account_ids)>1:
                    accounts = tuple(ac.id for ac in account_ids)
                    if len(state)==1:
                        move_line_ids = account_move_line_obj.search([('company_id','=',self.company_id.id),('account_id','in',accounts),('date','>=',self.date_from),('date','<=',self.date_to),('parent_state','=',state)])
                        pre_move_line_ids = account_move_line_obj.search([('company_id','=',self.company_id.id),('account_id','in',accounts),('date','<=',self.date_from),('parent_state','=',state)])
                    else:
                        move_line_ids = account_move_line_obj.search([('company_id','=',self.company_id.id),('account_id','in',accounts),('date','>=',self.date_from),('date','<=',self.date_to),('parent_state','in',state)])
                        pre_move_line_ids = account_move_line_obj.search([('company_id','=',self.company_id.id),('account_id','in',accounts),('date','<=',self.date_from),('parent_state','in',state)])
                else:
                    if len(state)==1:
                        move_line_ids = account_move_line_obj.search([('company_id','=',self.company_id.id),('account_id','=',account_ids.id),('date','>=',self.date_from),('date','<=',self.date_to),('parent_state','=',state)])
                        pre_move_line_ids = account_move_line_obj.search([('company_id','=',self.company_id.id),('account_id','=',account_ids.id),('date','<=',self.date_from),('parent_state','=',state)])
                    else:
                        move_line_ids = account_move_line_obj.search([('company_id','=',self.company_id.id),('account_id','=',account_ids.id),('date','>=',self.date_from),('date','<=',self.date_to),('parent_state','in',state)])
                        pre_move_line_ids = account_move_line_obj.search([('company_id','=',self.company_id.id),('account_id','=',account_ids.id),('date','<=',self.date_from),('parent_state','in',state)])
                    
                if len(move_line_ids)==1:
                    for mlines in move_line_ids:
                        debit +=mlines.debit
                        
                    for mlines in move_line_ids:
                        credit += mlines.credit
                else:
                    for mlines in move_line_ids:
                        credit += mlines.credit
                    for mlines in move_line_ids:
                        debit +=mlines.debit
                        
                        
                
                if len(pre_move_line_ids)==1:
                    for pmlines in pre_move_line_ids:
                        pdebit +=pmlines.debit
                        
                    for mlines in pre_move_line_ids:
                        pcredit += pmlines.credit
                else:
                    for pmlines in pre_move_line_ids:
                        pcredit += pmlines.credit
                    for pmlines in pre_move_line_ids:
                        pdebit +=pmlines.debit
                                                
                total = debit - credit
                pre_total = pdebit - pcredit
                
                sheet.write(rowx, 2, pre_total,data_right)
                sheet.write(rowx, 3, total,data_right)
                num +=1
                rowx +=1
           
        
        inch = 1000
        sheet.col(0).width = 1 * inch
        sheet.col(1).width = 20 * inch
        sheet.col(2).width = 5* inch
        sheet.col(3).width = 5 * inch
        sheet.col(4).width = 3 * inch
        sheet.col(5).width = 3 * inch
        sheet.col(6).width = 3 * inch
        sheet.col(7).width = 3 * inch
        sheet.col(8).width = 3 * inch
        sheet.col(9).width = 3 * inch
        sheet.row(6).height = 640
        sheet.row(0).height = 640
        
        sheet.write(rowx + 1, 1, u'Гүйцэтгэх захирал....................................../\
                                                 /', ezxf('font: bold off; align: wrap off, vert centre, horiz left;font: height 180'))
        sheet.write(rowx + 3, 1, u'Ерөнхий нягтлан бодогч....................................../\
                                                 /', ezxf('font: bold off; align: wrap off, vert centre, horiz left;font: height 180'))
        
        return {'data':book, 'directory_name':u'Санхүү байдлын тайлан',
                'attache_name':'Санхүү байдлын тайлан'}