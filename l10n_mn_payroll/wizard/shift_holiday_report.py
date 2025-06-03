# -*- coding: utf-8 -*-

import xlrd, base64, xlwt
from io import StringIO
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning

class ShiftHolidayReport(models.TransientModel):
    _inherit = 'abstract.report.excel'
    _name = 'shift.holiday.report'
    
    
    def get_export_data(self):
        context = self._context
        ezxf = xlwt.easyxf
        book = xlwt.Workbook(encoding='utf8')
        sheet = book.add_sheet('Shift report')
        header = ezxf('font: bold on; align: wrap on, vert centre, horiz centre;font: height 220')
        header1 = ezxf('font: bold off; align: wrap on, vert centre, horiz left;font: height 200')
        print_dateL = ezxf('font: bold off; align: wrap off, vert centre, horiz left;font: height 200')
        print_dateR = ezxf('font: bold off; align: wrap off, vert centre, horiz right;font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        line = ezxf('font: bold off; align: wrap on, vert centre, horiz left;font: height 200; borders: left thin, right thin, top thin, bottom thin;')
        line_data = ezxf('font: bold off; align: wrap on, vert centre, horiz right;font: height 200; borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        line_center = ezxf('font: bold off; align: wrap on, vert centre, horiz center;font: height 200; borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        nonline = ezxf('font: bold off; align: wrap off, vert centre, horiz left;font: height 200;')
        line_right =  ezxf('font: bold off; align: wrap on, vert centre, horiz right;font: height 200; borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')

        rowx = 0
        col = 3
        num = 1
        sheet.write(rowx, 0, u'Татвар төлөгчийн дугаар', header)
        sheet.write(rowx, 1, u'Овог', header)
        sheet.write(rowx, 2, u'Нэр', header)
        sheet.write(rowx, 3, u'Хуулийн 7.1.1', header)
        sheet.write(rowx, 4, u'Хуулийн 7.1.2, 7.1.3, 7.1.4, 7.1.5, 7.1.7', header)
        sheet.write(rowx, 5, u'Хуулийн 7.1.6', header)
        sheet.write(rowx, 6, u'Нийт (1+2+3)', header)
        sheet.write(rowx, 7, u'ЭМД, НДШ Хувь', header)
        sheet.write(rowx, 8, u'ЭМД, НДШ Дүн', header)
        sheet.write(rowx, 9, u'Татвар ногдуулах орлого', header)
        sheet.write(rowx, 10, u'Ногдуулсан татвар', header)
        sheet.write(rowx, 11, u'Орлого хүлээн авсан сарын тоо /ажилласан сар/', header)
        sheet.write(rowx, 12, u'Хуулийн 23.1-т заасан хөнгөлөлт сард ногдох', header)
        sheet.write(rowx, 13, u'Хуулийн 23.1-т заасан хөнгөлөлт нийт', header)
        sheet.write(rowx, 14, u'Хөнгөлөлтийн дараах татварын дүн', header)
        sheet.write(rowx, 15, u'Хуулийн 7.1.6-д заасан орлогод ногдуулсан дүн', header)
        sheet.write(rowx, 16, u'Нийт суутгуулсан албан татварын дүн', header)

        
        
        inch = 1000
        sheet.col(0).width = 3*inch
        sheet.col(1).width = 4*inch
        sheet.col(2).width = 5*inch
        sheet.col(3).width = 7*inch
        sheet.col(4).width = 4*inch
        sheet.col(5).width = 4*inch
        sheet.col(6).width = 4*inch
        sheet.col(7).width = 4*inch
        sheet.col(8).width = 4*inch
        sheet.col(9).width = 4*inch
        sheet.col(10).width = 4*inch
        sheet.col(11).width = 4*inch
        sheet.col(12).width = 4*inch
        sheet.col(13).width = 4*inch
        sheet.col(14).width = 4*inch
        sheet.col(15).width = 4*inch
        sheet.col(16).width = 4*inch
        sheet.col(17).width = 4*inch
        sheet.row(0).height = 1200   



        return {'data':book,'directory_name':u'Цалингийн тайлан',
                'attache_name':u'Цалингийн тайлан'} 