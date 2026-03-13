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
    _inherit = ['xls.report.base']
    _description = "Statement of stockholder's equity"
    
    company_id = fields.Many2one('res.company', string='Company', 
                                 required=True,default=lambda self: self.env.user.company_id)
    fiscalyear_id = fields.Many2one('account.fiscal.year', string='Fiscal year', required=True)
    date_from = fields.Date('Start Date', required=True, default=fields.Date.context_today)
    date_to = fields.Date('End Date', required=True, default=fields.Date.context_today)
    target_move=fields.Selection([('posted', 'All Posted Entries'),
                                     ('all', 'All Entries'),
                                    ], string='State', required=True, default='posted')

    def get_report_data(self):
        data = super(EquityChanges, self).get_report_data()
        data.update({
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'start_date': self.date_from,
            'end_date': self.date_to,
            'fiscalyear_id': self.fiscalyear_id.id,
            'target_move': self.target_move,
        })
        return data
    
    def action_print_xls_report(self):
        data = self.get_report_data()
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {'model': 'equity.changes',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'Cash and bank report'}
        }

    def get_xlsx_report(self, data, response, get_file=False):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        head = workbook.add_format({
                                    'align': 'center', 
                                    'bold': True, 
                                    'font_size': 16
                                    })

        header_txt = workbook.add_format({
                                    'align': 'center',
                                    'bold': True,
                                    'font_size': 12,
                                })
        data_left = workbook.add_format({
                                    'align': 'left',
                                    'border': 1,
                                    'font_size': 12,
                                    'text_wrap': True
                                })
        data_right = workbook.add_format({
                                    'align': 'right',
                                    'border': 1,
                                    'font_size': 12,
                                    'text_wrap': True
                                })
                            
        data_right_bold = workbook.add_format({
                                    'align': 'right',
                                    'border': 1,
                                    'font_size': 12,
                                    'text_wrap': True,
                                    'num_format': '#,##0.00',
                                    'bold': True
                                })

        title = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'bold': True,
                                    'font_size': 12,
                                    'text_wrap': True
                                })

        sheet.write("B4", u"%s ХХК" % (data['company_name']), header_txt)
        sheet.write('B5',u'(Аж ахуй нэгж, байгууллагын нэр)', header_txt)
        sheet.merge_range('A2:J2', u'ӨМЧИЙН ӨӨРЧЛӨЛТИЙН ТАЙЛАН', head)
        
        sheet.write('J4', u'%s - %s' % (data['start_date'],data['end_date']), header_txt)
        sheet.write('J6', u'(төгрөгөөр)', header_txt)
    
        sheet.set_paper(9)
        sheet.center_horizontally()
        sheet.fit_to_pages(1, 0.5)
        sheet.set_column(0, 0, 5)
        sheet.set_column(1, 1, 60)
        sheet.set_column(2, 9, 20)
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
        f_journal_id = journal_obj.search([('type', '=', 'opening'), ('company_id', '=', data['company_id'])],limit=1)

        now_fiscalyear = data['fiscalyear_id']
        nyear = fiscalyear_obj.browse(now_fiscalyear)
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
        date_to_obj = datetime.strptime(str(pre_two_year.date_to), '%Y-%m-%d')
        number = 1
        sheet.write("A%s"%rowx, number, data_right_bold)
        sheet.write("B%s"%rowx,  u'%s оны %s сарын %s-ний үлдэгдэл' % (pre_two_year.name,
                                                                         date_to_obj.strftime('%m'),
                                                                          date_to_obj.strftime('%d')), data_right_bold)

        report_account_equite_two = report_accounts.property_statutory_fund_account.id
        fund_move_line_ids = account_move_line_obj.search([('account_id','=',report_account_equite_two),('move_id.date','>=',data['start_date']),('move_id.date','<=',data['end_date']),('move_id.state','=','posted')])
        fund_amount = 0.0
        for fund in fund_move_line_ids:
            fund_amount = fund.debit - fund.credit
        if fund_amount < 0.0:
            fund_amount = fund_amount*(-1)
            
        sheet.write("C%s"%rowx, fund_amount, data_right_bold)
        sheet.write("D%s"%rowx, 0, data_right_bold)
        sheet.write("E%s"%rowx, 0, data_right_bold)
        sheet.write("F%s"%rowx, 0, data_right_bold)
        sheet.write("G%s"%rowx, 0, data_right_bold)
        sheet.write("H%s"%rowx, 0, data_right_bold)
        sheet.write("I%s"%rowx, 0, data_right_bold)
        sheet.write("J%s"%rowx, f"=SUM(C8:I8)", data_right_bold)
        move_id = account_move_obj.search([('journal_id','=',report_accounts.property_adjustment_journal.id),('date','>=',pre_two_year.date_to),('date','<=',pre_two_year.date_from)])
        if move_id !=[]:
            total_amount = 0.0
            for line in move_id:
                for lines in line.line_ids:
                    total_amount +=lines.debit
        
        sheet.write("A%s"%(rowx+1), number+1, data_right)
        sheet.write("B%s"%(rowx+1), u'НББүртгэлийн бодлогын өөрчлөлтийн нөлөө алдааны залруулга', data_right)
        sheet.write("C%s"%(rowx+1), 0, data_right)
        sheet.write("D%s"%(rowx+1), 0, data_right)
        sheet.write("E%s"%(rowx+1), 0, data_right)
        sheet.write("F%s"%(rowx+1), 0, data_right)
        sheet.write("G%s"%(rowx+1), 0, data_right)
        sheet.write("H%s"%(rowx+1), 0, data_right)
        sheet.write("I%s"%(rowx+1), 0, data_right)
        sheet.write("J%s"%(rowx+1), 0, data_right)


        sheet.write("A%s"%(rowx+2), number+2, data_right)
        sheet.write("B%s"%(rowx+2), u'Залруулсан үлдэгдэл', data_right)
        sheet.write("C%s"%(rowx+2), f"=C8+C9", data_right)
        sheet.write("D%s"%(rowx+2), f"=D8+D9", data_right)
        sheet.write("E%s"%(rowx+2), f"=E8+E9", data_right)
        sheet.write("F%s"%(rowx+2), f"=F8+F9", data_right)
        sheet.write("G%s"%(rowx+2), f"=G8+G9", data_right)
        sheet.write("H%s"%(rowx+2), f"=H8+H9", data_right)
        sheet.write("I%s"%(rowx+2), f"=I8+I9", data_right)
        sheet.write("J%s"%(rowx+2), f"=J8+J9", data_right)

        sheet.write("A%s"%(rowx+3), number+3, data_right)
        sheet.write("B%s"%(rowx+3), u'Тайлант үеийн цэвэр ашиг алдагдал', data_right)
        sheet.write("C%s"%(rowx+3), 0, data_right)
        sheet.write("D%s"%(rowx+3), 0, data_right)
        sheet.write("E%s"%(rowx+3), 0, data_right)
        sheet.write("F%s"%(rowx+3), 0, data_right)
        sheet.write("G%s"%(rowx+3), 0, data_right)
        sheet.write("H%s"%(rowx+3), 0, data_right)

        
        report_account_equite = report_accounts.property_previous_retained_earnings_account.id
        tw_earning_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_id.id),('account_id','=',report_account_equite),('move_id.date','>=',data['start_date']),('move_id.date','<=',data['start_date']),('move_id.state','=','posted')])
        tw_earning_amount = 0.0
        for tw_earning in tw_earning_move_line_ids:
            tw_earning_amount = tw_earning.debit - tw_earning.credit
        if tw_earning_amount < 0.0:
            sheet.write("I%s"%(rowx+3), tw_earning_amount*(-1), data_right)
        else:
            sheet.write("I%s"%(rowx+3), tw_earning_amount, data_right)

        sheet.write("J%s"%(rowx+3), f"=sum(C11:I11)", data_right)
        
        
        sheet.write("A%s"%(rowx+4), number+4, data_right)
        sheet.write("B%s"%(rowx+4), u'Бусад дэлгэрэнгүй орлого', data_right)
        sheet.write("C%s"%(rowx+4), 0, data_right)
        sheet.write("D%s"%(rowx+4), 0, data_right)
        sheet.write("E%s"%(rowx+4), 0, data_right)
        sheet.write("F%s"%(rowx+4), 0, data_right)
        sheet.write("G%s"%(rowx+4), 0, data_right)
        sheet.write("H%s"%(rowx+4), 0, data_right)
        sheet.write("I%s"%(rowx+4), 0, data_right)
        sheet.write("J%s"%(rowx+4), f"=SUM(C12:I12)", data_right)



        sheet.write("A%s"%(rowx+5), number+5, data_right)
        sheet.write("B%s"%(rowx+5), u'Өмчид гарсан өөрчлөлт', data_right)
        
        sheet.write("C%s"%(rowx+5), 0, data_right)
        sheet.write("D%s"%(rowx+5), 0, data_right)
        sheet.write("E%s"%(rowx+5), 0, data_right)
        sheet.write("F%s"%(rowx+5), 0, data_right)
        sheet.write("G%s"%(rowx+5), 0, data_right)
        sheet.write("H%s"%(rowx+5), 0, data_right)
        sheet.write("I%s"%(rowx+5), 0, data_right)
        sheet.write("J%s"%(rowx+5), f"=SUM(C13:I13)", data_right)

        
        sheet.write("A%s"%(rowx+6), number+6, data_right)
        sheet.write("B%s"%(rowx+6), u'Зарласан ноогдол ашиг', data_right)
        sheet.write("C%s"%(rowx+6), 0, data_right)
        sheet.write("D%s"%(rowx+6), 0, data_right)
        sheet.write("E%s"%(rowx+6), 0, data_right)
        sheet.write("F%s"%(rowx+6), 0, data_right)
        sheet.write("G%s"%(rowx+6), 0, data_right)
        sheet.write("H%s"%(rowx+6), 0, data_right)
        sheet.write("I%s"%(rowx+6), 0, data_right)
        sheet.write("J%s"%(rowx+6), f"=SUM(C14:I14)", data_right)

        sheet.write("A%s"%(rowx+7), str(number+7), data_right)
        sheet.write("B%s"%(rowx+7), u'Дахин үнэлгээний нэмэгдлийн хэрэгжсэн дүн', data_right)
        sheet.write("C%s"%(rowx+7), 0, data_right)
        sheet.write("D%s"%(rowx+7), 0, data_right)
        sheet.write("E%s"%(rowx+7), 0, data_right)
        sheet.write("F%s"%(rowx+7), 0, data_right)
        sheet.write("J%s"%(rowx+7), 0, data_right)
        sheet.write("H%s"%(rowx+7), 0, data_right)
        sheet.write("I%s"%(rowx+7), 0, data_right)
        sheet.write("J%s"%(rowx+7), f"=SUM(C15:I15)", data_right)


        date_one_obj = datetime.strptime(str(pre_one_year.date_to), '%Y-%m-%d')
        sheet.write("A%s"%(rowx+8), number+8, data_right_bold)
        sheet.write("B%s"%(rowx+8), u'%s оны %s сарын %s-ний үлдэгдэл' % (pre_one_year.name,
                                                                          date_one_obj.strftime('%m'),
                                                                          date_one_obj.strftime('%d')), data_right_bold)
        
        sheet.write("C%s"%(rowx+8), f"=SUM(C10+C13)", data_right_bold)
        sheet.write("D%s"%(rowx+8), f"=SUM(D10)", data_right_bold)
        sheet.write("E%s"%(rowx+8), f"=SUM(E10+E12)", data_right_bold)
        sheet.write("F%s"%(rowx+8), f"=SUM(F10+F15)", data_right_bold)
        sheet.write("G%s"%(rowx+8), f"=SUM(G10+G12)", data_right_bold)
        sheet.write("H%s"%(rowx+8), f"=SUM(H10+H12)", data_right_bold)
        sheet.write("I%s"%(rowx+8), f"=SUM(I10+I11-I14)", data_right_bold)
        sheet.write("J%s"%(rowx+8), f"=SUM(C16:I16)", data_right_bold)


        sheet.write("A%s"%(rowx+9), number+9, data_right)
        sheet.write("B%s"%(rowx+9), u'НББүртгэлийн бодлогын өөрчлөлтийн нөлөө алдааны залруулга', data_right)
        sheet.write("C%s"%(rowx+9), 0, data_right)
        sheet.write("D%s"%(rowx+9), 0, data_right)
        sheet.write("E%s"%(rowx+9), 0, data_right)
        sheet.write("F%s"%(rowx+9), 0, data_right)
        sheet.write("G%s"%(rowx+9), 0, data_right)
        sheet.write("H%s"%(rowx+9), 0, data_right)
        sheet.write("I%s"%(rowx+9), 0, data_right)
        sheet.write("J%s"%(rowx+9), 0, data_right)

        sheet.write("A%s"%(rowx+10), number+10, data_right)
        sheet.write("B%s"%(rowx+10), u'Залруулсан үлдэгдэл', data_right)
        sheet.write("C%s"%(rowx+10), f"=SUM(C16+C17)", data_right)
        sheet.write("D%s"%(rowx+10), f"=SUM(D16+D17)", data_right)
        sheet.write("E%s"%(rowx+10), f"=SUM(E16+E17)", data_right)
        sheet.write("F%s"%(rowx+10), f"=SUM(F16-F17)", data_right)
        sheet.write("G%s"%(rowx+10), f"=SUM(G16+G17)", data_right)
        sheet.write("H%s"%(rowx+10), f"=SUM(H16+H17)", data_right)
        sheet.write("I%s"%(rowx+10), f"=SUM(I16+I17)", data_right)
        sheet.write("J%s"%(rowx+10), f"=SUM(C18:I18)", data_right)


        sheet.write("A%s"%(rowx+11), number+11, data_right)
        sheet.write("B%s"%(rowx+11), u'Тайлант үеийн цэвэр ашиг алдагдал', data_right)
        sheet.write("C%s"%(rowx+11), 0, data_right)
        sheet.write("D%s"%(rowx+11), 0, data_right)
        sheet.write("E%s"%(rowx+11), 0, data_right)
        sheet.write("F%s"%(rowx+11), 0, data_right)
        sheet.write("G%s"%(rowx+11), 0, data_right)
        sheet.write("H%s"%(rowx+11), 0, data_right)
        report_account_equite = report_accounts.property_period_retained_earnings_account.id
        earning_move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_id.id),('account_id','=',report_account_equite),('move_id.date','>=',data['start_date']),('move_id.date','<=',data['end_date']),('move_id.state','=','posted')])
        earning_amount = 0.0
        for earning in earning_move_line_ids:
            earning_amount = earning.debit - earning.credit
        if earning_amount < 0.0:
            sheet.write("I%s"%(rowx+11), earning_amount*(-1), data_right)
        else:
            sheet.write("I%s"%(rowx+11), earning_amount, data_right)
        sheet.write("J%s"%(rowx+11), f"=SUM(C19:I19)", data_right)


        sheet.write("A%s"%(rowx+12), number+12, data_right)
        sheet.write("B%s"%(rowx+12), u'Бусад дэлгэрэнгүй орлого', data_right)
        sheet.write("C%s"%(rowx+12), 0, data_right)
        sheet.write("D%s"%(rowx+12), 0, data_right)
        sheet.write("E%s"%(rowx+12), 0, data_right)
        sheet.write("F%s"%(rowx+12), 0, data_right)
        sheet.write("G%s"%(rowx+12), 0, data_right)
        sheet.write("H%s"%(rowx+12), 0, data_right)
        sheet.write("I%s"%(rowx+12), 0, data_right)
        sheet.write("J%s"%(rowx+12), f"=SUM(C20:I20)", data_right)


        sheet.write("A%s"%(rowx+13), number+13, data_right)
        sheet.write("B%s"%(rowx+13), u'Өмчид гарсан өөрчлөлт', data_right)
        
        sheet.write("C%s"%(rowx+13), 0, data_right)
        sheet.write("D%s"%(rowx+13), 0, data_right)
        sheet.write("E%s"%(rowx+13), 0, data_right)
        sheet.write("F%s"%(rowx+13), 0, data_right)
        sheet.write("G%s"%(rowx+13), 0, data_right)
        sheet.write("H%s"%(rowx+13), 0, data_right)
        sheet.write("I%s"%(rowx+13), 0, data_right)
        sheet.write("J%s"%(rowx+13), f"=SUM(C21:I21)", data_right)


        sheet.write("A%s"%(rowx+14), number+14, data_right)
        sheet.write("B%s"%(rowx+14), u'Зарласан ноогдол ашиг', data_right)
        sheet.write("C%s"%(rowx+14), 0, data_right)
        sheet.write("D%s"%(rowx+14), 0, data_right)
        sheet.write("E%s"%(rowx+14), 0, data_right)
        sheet.write("F%s"%(rowx+14), 0, data_right)
        sheet.write("G%s"%(rowx+14), 0, data_right)
        sheet.write("H%s"%(rowx+14), 0, data_right)
        sheet.write("I%s"%(rowx+14), 0, data_right)
        sheet.write("J%s"%(rowx+14), f"=SUM(C22:I22)", data_right)


        sheet.write("A%s"%(rowx+15), number+15, data_right)
        sheet.write("B%s"%(rowx+15), u'Дахин үнэлгээний нэмэгдлийн хэрэгжсэн дүн', data_right)
        sheet.write("C%s"%(rowx+15), 0, data_right)
        sheet.write("D%s"%(rowx+15), 0, data_right)
        sheet.write("E%s"%(rowx+15), 0, data_right)
        sheet.write("F%s"%(rowx+15), 0, data_right)
        sheet.write("G%s"%(rowx+15), 0, data_right)
        sheet.write("H%s"%(rowx+15), 0, data_right)
        sheet.write("I%s"%(rowx+15), 0, data_right)
        sheet.write("J%s"%(rowx+15), f"=SUM(C23:I23)", data_right)


        date_now_obj = datetime.strptime(str(data['end_date']), '%Y-%m-%d')
        sheet.write("A%s"%(rowx+16), number+16, data_right_bold)
        sheet.write("B%s"%(rowx+16), u'%s оны %s сарын %s-ний үлдэгдэл' % (nyear.name,
                                                                          date_now_obj.strftime('%m'),
                                                                          date_now_obj.strftime('%d')), data_right_bold)
        sheet.write("C%s"%(rowx+16), f"=SUM(C18+C21)", data_right_bold)
        sheet.write("D%s"%(rowx+16), f"=SUM(D18)", data_right_bold)
        sheet.write("E%s"%(rowx+16), f"=SUM(E18+E20)", data_right_bold)
        sheet.write("F%s"%(rowx+16), f"=SUM(F18+F23)", data_right_bold)
        sheet.write("G%s"%(rowx+16), f"=SUM(G18+G20)", data_right_bold)
        sheet.write("H%s"%(rowx+16), f"=SUM(H18+H20)", data_right_bold)
        sheet.write("I%s"%(rowx+16), f"=SUM(I18+I19-I22)", data_right_bold)
        sheet.write("J%s"%(rowx+16), f"=SUM(C24:I24)", data_right_bold)
        rowx +=1


        workbook.close()
        output.seek(0)
        if get_file:
            return output.read()
        response.stream.write(output.read())
        output.close()
        return
        


        
        
        
