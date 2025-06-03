# -*- coding: utf-8 -*-

import io
import json
import xlsxwriter
from odoo import fields, models
from odoo.tools import date_utils

class CashMovelineReport(models.TransientModel):
    """
        Бэлэн мөнгө болон харилцахын гүйлгээний тайлан
    """
    _name = "cash.move.line.report"
    _description = "Account move line report"
    
    
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)
    date_from = fields.Date(string="Start date", required=True)
    date_to = fields.Date(string="End date", required=True)
    account_ids = fields.Many2many('account.account', 'account_move_report_rel', 'account_id','report_id', 
                                   string='Account', required=True)


    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'account_ids': self.account_ids.ids
        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {'model': 'cash.move.line.report',
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
                                    'font_size': '20px'
                                    })
        txt = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'font_size': 12
                                })
        sheet.set_column(0, 8, 24)


    
    def get_export_data(self):
        styledict = self.get_easyxf_styles()
        
        ezxf = xlwt.easyxf
        book = xlwt.Workbook(encoding='utf8')
        sheet = book.add_sheet(u'Account move')
        
        date_str = '%s-%s' % (
            datetime.strptime(str(self.date_from), '%Y-%m-%d').strftime('%Y.%m.%d'),
            datetime.strptime(str(self.date_to), '%Y-%m-%d').strftime('%Y.%m.%d')
        )
        
        sheet.write_merge(0, 0, 0, 1, u'НХМаягт МХ-4', xlwt.easyxf('font:bold on;align:wrap off,vert centre,horiz left;font: height 180'))
        sheet.write_merge(0, 0, 2, 7, u'Сангийн сайдын 2018 оны 100 дугаар', xlwt.easyxf('font:bold on;align:wrap off,vert centre,horiz right;font: height 180'))
        sheet.write_merge(1, 1, 2, 7, u'тушаалын хавсралт', xlwt.easyxf('font:bold on;align:wrap off,vert centre,horiz right;font: height 180'))
        sheet.write_merge(3, 3, 1, 6, u'Бэлэн мөнгөний гүйлгээний тайлан', xlwt.easyxf('font:bold on;align:wrap off,vert centre,horiz center;font: height 280'))
        sheet.write(5, 0, u'Байгууллагын нэр: %s' % self.company_id.name, xlwt.easyxf('font:bold on;align:wrap off,vert centre,horiz left;font: height 180'))
        sheet.write(5, 7, u'Он сар өдөр: %s' % date_str, xlwt.easyxf('font:bold on;align:wrap off,vert centre,horiz right;font: height 180'))
        rowx = 7
        
        sheet.write_merge(rowx, rowx+1, 0, 0, u'Д/д', styledict['heading_xf'])
        sheet.write_merge(rowx, rowx, 1, 2, u'Баримтын', styledict['heading_xf'])
        sheet.write_merge(rowx+1, rowx+1, 1, 1, u'Дугаар', styledict['heading_xf'])
        sheet.write_merge(rowx+1, rowx+1, 2, 2, u'Он сар өдөр', styledict['heading_xf'])
        sheet.write_merge(rowx, rowx+1, 3, 3, u'Гүйлгээний утга', styledict['heading_xf'])
        sheet.write_merge(rowx, rowx+1, 4, 4, u'Харилцагч', styledict['heading_xf'])
        sheet.write_merge(rowx, rowx+1, 5, 5, u'Орлого', styledict['heading_xf'])
        sheet.write_merge(rowx, rowx+1, 6, 6, u'Зарлага', styledict['heading_xf'])
        sheet.write_merge(rowx, rowx+1, 7, 7, u'Үлдэгдлийн дүн', styledict['heading_xf'])
        data_right = ezxf('font: bold off; align: wrap on, vert centre, horiz right; font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        data_bold_right = ezxf('font: bold on; align: wrap on, vert centre, horiz right; font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')

        rowx = 9
        number = 1
        account_obj = self.env['account.account']
        if len(self.account_ids) == 1:
            account_id = account_obj.search([('id','=',self.account_ids.id),('company_id','=',self.company_id.id)])
            self.env.cr.execute("select am.date, aml.name, aml.ref, sp.name, aa.code, aa.name, acmt.name, \
            aml.debit, aml.credit, am.name,am.partner_id from account_move_line AS aml \
            left join account_move AS am ON am.id = aml.move_id \
            left join res_partner AS sp on sp.id = aml.partner_id \
            left join account_account AS aa on aa.id = aml.account_id \
            left join account_cash_move_type AS acmt on acmt.id = aml.cash_move_type_id \
            WHERE am.date >= '%s' and am.date <='%s' and aml.account_id = %s and am.state='posted' \
            order by aml.date asc"%(self.date_from,self.date_to,self.account_ids.id))
            all = self._cr.fetchall()
            
        else:
            account_id = account_obj.search([('id','in',tuple(self.account_ids)),('company_id','=',self.company_id.id)])
            self.env.cr.execute("select am.date, aml.name, aml.ref, sp.name, aa.code, aa.name, acmt.name, \
            aml.debit, aml.credit, am.name,am.partner_id from account_move_line AS aml \
            left join account_move AS am ON am.id = aml.move_id \
            left join res_partner AS sp on sp.id = aml.partner_id \
            left join account_account AS aa on aa.id = aml.account_id \
            left join account_cash_move_type AS acmt on acmt.id = aml.cash_move_type \
            WHERE am.date >= '%s' and am.date <='%s' and aml.account_id in %s and am.state='posted' \
            order by aml.date asc"%(self.date_from,self.date_to,tuple(self.account_ids)))
            all = self._cr.fetchall()
        start_balance = 0.0
        total = 0.0
        partner_obj = self.env['res.partner']
        for line in account_id:
            balance = 0.0
            self.env.cr.execute("select sum(debit-credit) as balance from account_move_line where date >= '%s' and date < '%s' and account_id = %s"%(self.date_from,self.date_from,line.id))
            acc = self._cr.dictfetchall()
            if acc[0]['balance'] !=None:
                balance = acc[0]['balance']
            
            sheet.write_merge(rowx, rowx, 0, 1, u'Дансны №', styledict['heading_xf'])
            sheet.write_merge(rowx, rowx, 2, 3, u'%s %s'%(line.code,line.name), styledict['heading_xf'])
            sheet.write_merge(rowx, rowx, 4, 6, u'Эхний үлдэгдэл', styledict['heading_xf'])
            sheet.write_merge(rowx, rowx, 7, 7, balance, data_bold_right)
            rowx +=1
            for i in all:
                if line.code==i[4]:
                    if i[10]:
                        partner = partner_obj.browse(i[10])
                        sheet.write(rowx, 4, partner.name, data_right)
                    else:
                        sheet.write(rowx, 4, '', data_right)
                    sheet.write(rowx, 0, number, styledict['text_xf'])
                    sheet.write(rowx, 1, i[9], styledict['text_xf'])
                    sheet.write(rowx, 2, '%s'%i[0], styledict['text_xf'])
                    sheet.write(rowx, 3, i[1], styledict['text_xf'])
                    
                    sheet.write(rowx, 5, i[7], data_right)
                    sheet.write(rowx, 6, i[8], data_right)
                    if i[7] >0.0:
                        if balance !=None:
                            balance +=float(i[7])
                    elif i[8] > 0.0:
                        if balance !=None:
                            balance -=float(i[8])
                    sheet.write(rowx, 7, balance, data_right)
                    number += 1
                    rowx += 1
            
        inch = 1000
        sheet.col(0).width = 1 * inch
        sheet.col(1).width = 4 * inch
        sheet.col(2).width = 3 * inch
        sheet.col(3).width = 7 * inch
        sheet.col(4).width = 5 * inch
        sheet.col(5).width = 4 * inch
        sheet.col(6).width = 4 * inch
        sheet.col(7).width = 4 * inch
        sheet.col(8).width = 4 * inch
        sheet.col(9).width = 4 * inch
        sheet.row(3).height = 540
        
        
        sheet.write_merge(rowx + 1, rowx + 1, 1, 6, u'Орлогын                 зарлагын                 ширхэг баримтыг шалгаж хүлээн авсан болно.', ezxf('font:bold off;align:wrap off,vert centre,horiz left;font: height 160'))
        
        sheet.write(rowx + 4, 1, u"Нягтлан бодогч: ..................................................../                                            /",
                    xlwt.easyxf('font:bold off;align:wrap off,vert centre,horiz left;font: height 180'))
        sheet.write(rowx + 6, 1, u"Мөнгөний нярав: ..................................................../                                           /",
                    xlwt.easyxf('font:bold off;align:wrap off,vert centre,horiz left;font: height 180'))
        
        return {'data':book, 'directory_name':"Ажил гүйлгээ",
                'attache_name':"Ажил гүйлгээ"}
        
