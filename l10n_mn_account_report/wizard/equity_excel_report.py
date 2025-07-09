# -*- coding: utf-8 -*-

import io
import json
import xlsxwriter
from odoo import fields, models
from odoo.tools import date_utils
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, time

class EquityChanges(models.TransientModel):
    """
        ӨМЧИЙН ӨӨРЧЛӨЛТИЙН ТАЙЛАН
        Statement of stockholder's equity
    """
    _name = "equity.changes"
    _description = "Statement of stockholder's equity"
    
    company_id = fields.Many2one('res.company', string='Company', 
                                 required=True,default=lambda self: self.env.user.company_id)
    fiscalyear_id = fields.Many2one('account.fiscal.year', string='Fiscal year', required=True)
    date_from = fields.Date('Start Date', required=True, default=fields.Date.context_today)
    date_to = fields.Date('End Date', required=True, default=fields.Date.context_today)
    target_move=fields.Selection([('posted', 'All Posted Entries'),
                                     ('all', 'All Entries'),
                                    ], string='State', required=True, default='posted')
    
    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'start_date': self.date_from,
            'end_date': self.date_to,
            'fiscalyear_id': self.fiscalyear_id.id,
            'target_move': self.target_move,
        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {'model': 'equity.changes',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'Cash and bank report'}
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

        header_txt = workbook.add_format({
                                    'align': 'center',
                                    'bold': True,
                                    'font_size': 12
                                })
        data_left = workbook.add_format({
                                    'align': 'left',
                                    'border': 1,
                                    'font_size': 12
                                })
        title = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'bold': True,
                                    'font_size': 12
                                })

        sheet.write("B4", u"%s ХХК" % (data['company_name']), header_txt)
        sheet.write('B5',u'(Аж ахуй нэгж, байгууллагын нэр)', head)
        sheet.merge_range('A2:J2', u'ӨМЧИЙН ӨӨРЧЛӨЛТИЙН ТАЙЛАН', head)
        
        sheet.write('J4', u'%s - %s' % (data['start_date'],data['end_date']), head)
        sheet.write('J6', u'(төгрөгөөр)', head)
    

        sheet.set_column(0, 8, 24)
        rowx = 7
        sheet.write("A%s"%rowx, u'Д/д', title)
        sheet.write("B%s"%rowx, u'Үзүүлэлт', title)
        sheet.write("C%s"%rowx, u'Өмч', title)
        sheet.write("D%s"%rowx, u'Халаасны хувьцаа', title)
        sheet.write("E%s"%rowx, u'Нэмж төлөгдсөн капитал', title)
        sheet.write("F%s"%rowx, u'Дахин үнэлгээний нэмэгдэл', title)
        sheet.write("G%s"%rowx, u'Гадаад валютын хөрвүүлэлтийн нөөц', title)
        sheet.write("H%s"%rowx, u'Эздийн өмчийн бусад хэсэг', title)
        sheet.write("I%s"%rowx, u'Хуримтлагдсан ашиг', title)
        sheet.write("J%s"%rowx, u'Нийт дүн', title)
        rowx += 1

        account_obj = self.env['account.account']
        journal_obj = self.env['account.journal']
        account_move_obj = self.env['account.move']
        account_move_line_obj = self.env['account.move.line']
        currency_obj = self.env['res.currency']
        fiscalyear_obj = self.env['account.fiscal.year']

        now_fiscalyear = data['fiscalyear_id']
        nyear = fiscalyear_obj.browse(now_fiscalyear)
        print ("now_fiscalyear", int(nyear.name))
        pre_one_year_id = fiscalyear_obj.search([('name','=',str(int(nyear.name)-1))],order="id asc",limit=1)
        if pre_one_year_id.id == False:
            raise UserError(u"%s Санхүүгийн жил үүсээгүй байгаа тул үүсгэнэ үү!"%(int(nyear.name)-1))
        pre_one_year = pre_one_year_id
        pre_two_year_id = fiscalyear_obj.search([('name','=',str(int(nyear.name)-2))],order="id asc",limit=1)
        if pre_two_year_id.id ==False:
            raise UserError(u"%s Санхүүгийн жил үүсээгүй байгаа тул үүсгэнэ үү!"%(int(nyear.name)-2))
        
        pre_two_year = pre_two_year_id
        report_account = self.env['equity.configure.report'].search([('company_id', '=', data['company_id'])])
        if report_account.id !=False:
            report_accounts = self.env['equity.configure.report'].browse(report_account.id)
        else:
            raise UserError(u"Өмчийн өөрчлөлтийн тайлангийн тохиргоог хийнэ үү!")
        date_to_obj = datetime.strptime(str(pre_two_year.date_end), '%Y-%m-%d')
        number = 1
        #sheet.write(rowx, 0, str(number), data_style)
        #sheet.write(rowx, 1,  u'%s оны %s сарын %s-ний үлдэгдэл' % (pre_two_year.name,
        #                                                                 date_to_obj.strftime('%m'),
        #                                                                  date_to_obj.strftime('%d')), data_style)

        report_account_equite_two = report_accounts.property_statutory_fund_account.id
        fund_move_line_ids = account_move_line_obj.search([('account_id','=',report_account_equite_two),('move_id.date','>=',data['start_date']),('move_id.date','<=',data['end_date']),('move_id.state','=','posted')])
        fund_amount = 0.0
        for fund in fund_move_line_ids:
            fund_amount = fund.debit - fund.credit
        if fund_amount < 0.0:
            fund_amount = fund_amount*(-1)
            
        #sheet.write(rowx, 2, fund_amount, data_style)
        #sheet.write(rowx, 3, '', data_style)
        #sheet.write(rowx, 4, '', data_style)
        #sheet.write(rowx, 5, '', data_style)
        #sheet.write(rowx, 6, '', data_style)
        #sheet.write(rowx, 7, '', data_style)
        #sheet.write(rowx, 8, '', data_style)
        #sheet.write(rowx, 9, Formula("SUM(C8:I8)"), data_style)

        

    def get_export_data(self):
        ''' Тайлангийн загварыг боловсруулж өгөгдлүүдийг
            тооцоолж байрлуулна.
        '''



        
        
        

    
        
        
        
        move_id = account_move_obj.search([('journal_id','=',report_accounts.property_adjustment_journal.id),('date','>=',pre_two_year.date_start),('date','<=',pre_two_year.date_end)])
        if move_id !=[]:
            total_amount = 0.0
            for line in move_id:
                for lines in line.line_ids:
                    total_amount +=lines.debit
        
        sheet.write(rowx+1, 0, str(number+1), data_style)
        sheet.write(rowx+1, 1, u'НББүртгэлийн бодлогын өөрчлөлтийн нөлөө алдааны залруулга', data_style)
        sheet.write(rowx+1, 2, '', data_style)
        sheet.write(rowx+1, 3, '', data_style)
        sheet.write(rowx+1, 4, '', data_style)
        sheet.write(rowx+1, 5, '', data_style)
        sheet.write(rowx+1, 6, '', data_style)
        sheet.write(rowx+1, 7, '', data_style)
        sheet.write(rowx+1, 8, '', data_style)
        sheet.write(rowx+1, 9, '', data_style)
        
        
        
        sheet.write(rowx+2, 0, str(number+2), data_style)
        sheet.write(rowx+2, 1, u'Залруулсан үлдэгдэл', data_style)
        sheet.write(rowx+2, 2, Formula("SUM(C8+C9)"), data_style)
        sheet.write(rowx+2, 3, Formula("SUM(D8+D9)"), data_style)
        sheet.write(rowx+2, 4, Formula("SUM(E8+E9)"), data_style)
        sheet.write(rowx+2, 5, Formula("SUM(F8+F9)"), data_style)
        sheet.write(rowx+2, 6, Formula("SUM(G8+G9)"), data_style)
        sheet.write(rowx+2, 7, Formula("SUM(H8+H9)"), data_style)
        sheet.write(rowx+2, 8, Formula("SUM(I8+I9)"), data_style)
        sheet.write(rowx+2, 9, Formula("SUM(J8+J9)"), data_style)
        
        sheet.write(rowx+3, 0, str(number+3), data_style)
        sheet.write(rowx+3, 1, u'Тайлант үеийн цэвэр ашиг алдагдал', data_style)
        sheet.write(rowx+3, 2, '', data_style)
        sheet.write(rowx+3, 3, '', data_style)
        sheet.write(rowx+3, 4, '', data_style)
        sheet.write(rowx+3, 5, '', data_style)
        sheet.write(rowx+3, 6, '', data_style)
        sheet.write(rowx+3, 7, '', data_style)
        
        report_account_equite = report_accounts.property_previous_retained_earnings_account.id
        tw_earning_move_line_ids = account_move_line_obj.search([('account_id','=',report_account_equite),('move_id.date','>=',pre_one_year.date_start),('move_id.date','<=',pre_one_year.date_end),('move_id.state','=','posted')])
        tw_earning_amount = 0.0
        for tw_earning in tw_earning_move_line_ids:
            tw_earning_amount = tw_earning.debit - tw_earning.credit
        if tw_earning_amount < 0.0:
            sheet.write(rowx+3, 8, tw_earning_amount*(-1), data_style)
        else:
            sheet.write(rowx+3, 8, tw_earning_amount, data_style)

        sheet.write(rowx+3, 9, Formula("SUM(C11:I11)"), data_style)
        
        
        sheet.write(rowx+4, 0, str(number+4), data_style)
        sheet.write(rowx+4, 1, u'Бусад дэлгэрэнгүй орлого', data_style)
        sheet.write(rowx+4, 2, '', data_style)
        sheet.write(rowx+4, 3, '', data_style)
        sheet.write(rowx+4, 4, '', data_style)
        sheet.write(rowx+4, 5, '', data_style)
        sheet.write(rowx+4, 6, '', data_style)
        sheet.write(rowx+4, 7, '', data_style)
        sheet.write(rowx+4, 8, '', data_style)
        sheet.write(rowx+4, 9, Formula("SUM(C12:I12)"), data_style)
        
        sheet.write(rowx+5, 0, str(number+5), data_style)
        sheet.write(rowx+5, 1, u'Өмчид гарсан өөрчлөлт', data_style)
        
        
        sheet.write(rowx+5, 2, '', data_style)
        sheet.write(rowx+5, 3, '', data_style)
        sheet.write(rowx+5, 4, '', data_style)
        sheet.write(rowx+5, 5, '', data_style)
        sheet.write(rowx+5, 6, '', data_style)
        sheet.write(rowx+5, 7, '', data_style)
        sheet.write(rowx+5, 8, '', data_style)
        sheet.write(rowx+5, 9, Formula("SUM(C13:I13)"), data_style)
        
        
        sheet.write(rowx+6, 0, str(number+6), data_style)
        sheet.write(rowx+6, 1, u'Зарласан ноогдол ашиг', data_style)
        sheet.write(rowx+6, 2, '', data_style)
        sheet.write(rowx+6, 3, '', data_style)
        sheet.write(rowx+6, 4, '', data_style)
        sheet.write(rowx+6, 5, '', data_style)
        sheet.write(rowx+6, 6, '', data_style)
        sheet.write(rowx+6, 7, '', data_style)
        sheet.write(rowx+6, 8, '', data_style)
        sheet.write(rowx+6, 9, Formula("SUM(C14:I14)"), data_style)
        
        sheet.write(rowx+7, 0, str(number+7), data_style)
        sheet.write(rowx+7, 1, u'Дахин үнэлгээний нэмэгдлийн хэрэгжсэн дүн', data_style)
        sheet.write(rowx+7, 2, '', data_style)
        sheet.write(rowx+7, 3, '', data_style)
        sheet.write(rowx+7, 4, '', data_style)
        sheet.write(rowx+7, 5, '', data_style)
        sheet.write(rowx+7, 6, '', data_style)
        sheet.write(rowx+7, 7, '', data_style)
        sheet.write(rowx+7, 8, '', data_style)
        sheet.write(rowx+7, 9, Formula("SUM(C15:I15)"), data_style)
        
        
        
        date_one_obj = datetime.strptime(str(pre_one_year.date_end), '%Y-%m-%d')
        sheet.write(rowx+8, 0, str(number+8), data_style)
        sheet.write(rowx+8, 1,  u'%s оны %s сарын %s-ний үлдэгдэл' % (pre_one_year.name,
                                                                          date_one_obj.strftime('%m'),
                                                                          date_one_obj.strftime('%d')), data_style)
        
        sheet.write(rowx+8, 2, Formula("SUM(C10+C13)"), data_style)
        sheet.write(rowx+8, 3, Formula("SUM(D10)"), data_style)
        sheet.write(rowx+8, 4, Formula("SUM(E10+E12)"), data_style)
        sheet.write(rowx+8, 5, Formula("SUM(F10+F15)"), data_style)
        sheet.write(rowx+8, 6, Formula("SUM(G10+G12)"), data_style)
        sheet.write(rowx+8, 7, Formula("SUM(H10+H12)"), data_style)
        sheet.write(rowx+8, 8, Formula("SUM(I10+I11-I14)"), data_style)
        sheet.write(rowx+8, 9, Formula("SUM(C16:I16)"), data_style)
        
        
        sheet.write(rowx+9, 0, str(number+9), data_style)
        sheet.write(rowx+9, 1, u'НББүртгэлийн бодлогын өөрчлөлтийн нөлөө алдааны залруулга', data_style)
        sheet.write(rowx+9, 2, '', data_style)
        sheet.write(rowx+9, 3, '', data_style)
        sheet.write(rowx+9, 4, '', data_style)
        sheet.write(rowx+9, 5, '', data_style)
        sheet.write(rowx+9, 6, '', data_style)
        sheet.write(rowx+9, 7, '', data_style)
        sheet.write(rowx+9, 8, '', data_style)
        sheet.write(rowx+9, 9, '', data_style)
        
        
        
        
        sheet.write(rowx+10, 0, str(number+10), data_style)
        sheet.write(rowx+10, 1, u'Залруулсан үлдэгдэл', data_style)
        sheet.write(rowx+10, 2, Formula("SUM(C16+C17)"), data_style)
        sheet.write(rowx+10, 3, Formula("SUM(D16+D17)"), data_style)
        sheet.write(rowx+10, 4, Formula("SUM(E16+E17)"), data_style)
        sheet.write(rowx+10, 5, Formula("SUM(F16-F17)"), data_style)
        sheet.write(rowx+10, 6, Formula("SUM(G16+G17)"), data_style)
        sheet.write(rowx+10, 7, Formula("SUM(H16+H17)"), data_style)
        sheet.write(rowx+10, 8, Formula("SUM(I16+I17)"), data_style)
        sheet.write(rowx+10, 9, Formula("SUM(C18:I18)"), data_style)

        
        sheet.write(rowx+11, 0, str(number+11), data_style)
        sheet.write(rowx+11, 1, u'Тайлант үеийн цэвэр ашиг алдагдал', data_style)
        sheet.write(rowx+11, 2, '', data_style)
        sheet.write(rowx+11, 3, '', data_style)
        sheet.write(rowx+11, 4, '', data_style)
        sheet.write(rowx+11, 5, '', data_style)
        sheet.write(rowx+11, 6, '', data_style)
        sheet.write(rowx+11, 7, '', data_style)
        report_account_equite = report_accounts.property_period_retained_earnings_account.id
        earning_move_line_ids = account_move_line_obj.search([('account_id','=',report_account_equite),('move_id.date','>=',self.date_from),('move_id.date','<=',self.date_to),('move_id.state','=','posted')])
        earning_amount = 0.0
        for earning in earning_move_line_ids:
            earning_amount = earning.debit - earning.credit
        if earning_amount < 0.0:
            sheet.write(rowx+11, 8, earning_amount*(-1), data_style)
        else:
            sheet.write(rowx+11, 8, earning_amount, data_style)
        sheet.write(rowx+11, 9, Formula("SUM(C19:I19)"), data_style)
        
        
        sheet.write(rowx+12, 0, str(number+12), data_style)
        sheet.write(rowx+12, 1, u'Бусад дэлгэрэнгүй орлого', data_style)
        sheet.write(rowx+12, 2, '', data_style)
        sheet.write(rowx+12, 3, '', data_style)
        sheet.write(rowx+12, 4, '', data_style)
        sheet.write(rowx+12, 5, '', data_style)
        sheet.write(rowx+12, 6, '', data_style)
        sheet.write(rowx+12, 7, '', data_style)
        sheet.write(rowx+12, 8, '', data_style)
        sheet.write(rowx+12, 9, Formula("SUM(C20:I20)"), data_style)
        
        
        sheet.write(rowx+13, 0, str(number+13), data_style)
        sheet.write(rowx+13, 1, u'Өмчид гарсан өөрчлөлт', data_style)
        

        sheet.write(rowx+13, 2, '', data_style)
        sheet.write(rowx+13, 3, '', data_style)
        sheet.write(rowx+13, 4, '', data_style)
        sheet.write(rowx+13, 5, '', data_style)
        sheet.write(rowx+13, 6, '', data_style)
        sheet.write(rowx+13, 7, '', data_style)
        sheet.write(rowx+13, 8, '', data_style)
        sheet.write(rowx+13, 9, Formula("SUM(C21:I21)"), data_style)
        
        
        sheet.write(rowx+14, 0, str(number+14), data_style)
        sheet.write(rowx+14, 1, u'Зарласан ноогдол ашиг', data_style)
        sheet.write(rowx+14, 2, '', data_style)
        sheet.write(rowx+14, 3, '', data_style)
        sheet.write(rowx+14, 4, '', data_style)
        sheet.write(rowx+14, 5, '', data_style)
        sheet.write(rowx+14, 6, '', data_style)
        sheet.write(rowx+14, 7, '', data_style)
        sheet.write(rowx+14, 8, '', data_style)
        sheet.write(rowx+14, 9, Formula("SUM(C22:I22)"), data_style)
        
        sheet.write(rowx+15, 0, str(number+15), data_style)
        sheet.write(rowx+15, 1, u'Дахин үнэлгээний нэмэгдлийн хэрэгжсэн дүн', data_style)
        sheet.write(rowx+15, 2, '', data_style)
        sheet.write(rowx+15, 3, '', data_style)
        sheet.write(rowx+15, 4, '', data_style)
        sheet.write(rowx+15, 5, '', data_style)
        sheet.write(rowx+15, 6, '', data_style)
        sheet.write(rowx+15, 7, '', data_style)
        sheet.write(rowx+15, 8, '', data_style)
        sheet.write(rowx+15, 9, Formula("SUM(C23:I23)"), data_style)
        
        date_now_obj = datetime.strptime(str(self.date_to), '%Y-%m-%d')
        sheet.write(rowx+16, 0, str(number+16), data_style)
        sheet.write(rowx+16, 1,  u'%s оны %s сарын %s-ний үлдэгдэл' % (now_fiscalyear.name,
                                                                          date_now_obj.strftime('%m'),
                                                                          date_now_obj.strftime('%d')), data_style)
        sheet.write(rowx+16, 2, Formula("SUM(C18+C21)"), data_style)
        sheet.write(rowx+16, 3, Formula("SUM(D18)"), data_style)
        sheet.write(rowx+16, 4, Formula("SUM(E18+E20)"), data_style)
        sheet.write(rowx+16, 5, Formula("SUM(F18+F23)"), data_style)
        sheet.write(rowx+16, 6, Formula("SUM(G18+G20)"), data_style)
        sheet.write(rowx+16, 7, Formula("SUM(H18+H20)"), data_style)
        sheet.write(rowx+16, 8, Formula("SUM(I18+I19-I22)"), data_style)
        sheet.write(rowx+16, 9, Formula("SUM(C24:I24)"), data_style)
        rowx +=1
        
        
        
        inch = 1000
        sheet.col(0).width = 1 * inch
        sheet.col(1).width = 10 * inch
        sheet.col(2).width = 4 * inch
        sheet.col(3).width = 4 * inch
        sheet.col(4).width = 4 * inch
        sheet.col(5).width = 4 * inch
        sheet.col(6).width = 4 * inch
        sheet.col(7).width = 4 * inch
        sheet.col(8).width = 4 * inch
        sheet.col(9).width = 4 * inch
        sheet.row(6).height = 650
        sheet.row(8).height = 640
        sheet.row(14).height = 640
        sheet.row(16).height = 640
        sheet.row(22).height = 640
        
        sheet.write(rowx + 19, 2, u'Гүйцэтгэх захирал....................................../\
                                                 /', ezxf('font: bold off; align: wrap off, vert centre, horiz left;font: height 180'))
        sheet.write(rowx + 20, 2, u'Ерөнхий нягтлан бодогч....................................../\
                                                 /', ezxf('font: bold off; align: wrap off, vert centre, horiz left;font: height 180'))
        

