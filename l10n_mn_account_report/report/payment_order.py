# -*- coding: utf-8 -*-

import io
import json
import xlsxwriter
from odoo import fields, models
from odoo.tools import date_utils

class payment_order_reportsd(models.TransientModel):
    """
        Төлбөрийн даалгаврын тайлан
    """
    _name = "payment.order.reportsd"
    _description = "Төлбөрийн даалгаврын тайлан"



    def action_print_xls_report(self):
        st_line_obj = self.env['account.bank.statement.line']
        active_ids = self._context.get('active_ids', [])
        st_data = st_line_obj.browse(active_ids)
        data = {
            'company_name': st_data.company_id.name,
            'director_name': u'М.Хишигмөнх' if st_data.company_id.id == 4 else u'Д.Мэндсайхан',
            'date': st_data.date,
            'partner_name': st_data.partner_id.name,
            'amount': st_data.amount,
            'amount_text': st_data.amount_text,
            'name':st_data.name,
            'payment_ref': st_data.payment_ref,
            'com_bank_name': st_data.company_id.partner_id.bank_ids[0].bank_id.name if st_data.company_id.partner_id.bank_ids else '',
            'com_account_number': st_data.company_id.partner_id.bank_ids[0].acc_number if st_data.company_id.partner_id.bank_ids else '',
            'com_bank_iban': st_data.company_id.partner_id.bank_ids[0].iban if st_data.company_id.partner_id.bank_ids else '',
            'partner_bank_name': st_data.partner_id.bank_ids[0].bank_id.name if st_data.partner_id.bank_ids else '',
            'partner_bank_account_number': st_data.partner_id.bank_ids[0].acc_number if st_data.partner_id.bank_ids else '',
            'partner_bank_iban': st_data.partner_id.bank_ids[0].iban if st_data.partner_id.bank_ids else '',
            'bank_account_number': st_data.partner_id.bank_ids[0].acc_number if st_data.partner_id.bank_ids else '',
            'bank_iban': st_data.partner_id.bank_ids[0].iban if st_data.partner_id.bank_ids else '',
            }

        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {
                     'model': 'payment.order.reportsd',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'Account payment order report'}
        }


    def get_xlsx_report(self, data, response):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()

        no_border_left = workbook.add_format({
                                    'align': 'top_left',
                                    'font_size': 12,
                                    'valign': 'vcenter',
                                })  
        border_center = workbook.add_format({
                                    'border': 1,
                                    'font_size': 12,
                                    'align': 'center',
                                    'valign': 'vcenter',
                                })
        border_left = workbook.add_format({
                                    'border': 1,
                                    'font_size': 12,
                                    'align': 'left',
                                    'valign': 'vcenter',
                                })
        no_border = workbook.add_format({
                                    'font_size': 12,
                                    'align': 'left',
                                    'valign': 'vcenter',
                                    'bold': True
                                })
        
        no_border_right = workbook.add_format({
                                    'font_size': 12,
                                    'align': 'right',
                                    'valign': 'vcenter',
                                })
        no_border_bold_right = workbook.add_format({
                                    'font_size': 12,
                                    'align': 'right',
                                    'valign': 'vcenter',
                                    'bold': True
                                })
        no_border_center = workbook.add_format({
                                    'font_size': 12,
                                    'align': 'center',
                                    'valign': 'vcenter',
                                    'bold': True
                                })
        text_wrap = workbook.add_format({
                                    'font_size': 12,
                                    'align': 'center',
                                    'valign': 'vcenter',
                                    'text_wrap': True
                                })
        border_center_bold = workbook.add_format({
                                    'border': 1,
                                    'font_size': 12,
                                    'align': 'center',
                                    'valign': 'vcenter',
                                    'bold': True
                                })
        no_border_no_bold = workbook.add_format({
                                    'font_size': 12,
                                    'align': 'center',
                                    'valign': 'vcenter',
                                })
        no_border_bold_center = workbook.add_format({
                                    'font_size': 12,
                                    'align': 'center',
                                    'valign': 'vcenter',
                                    'bold': True
                                })


        sheet.set_column(3, 5, 20)
        sheet.set_column(2, 2, 40)
        sheet.set_column(1, 1, 40)
        sheet.set_column(0, 0, 20)
        sheet.set_row(9, 30)
        sheet.set_row(10, 30)
        sheet.set_row(3, 30)
        sheet.set_row(11, 20)
        sheet.set_row(12, 20)
        sheet.set_row(13, 20)
        sheet.set_row(14, 20)
        sheet.merge_range('D1:E1', u'Маягт N: TC-7', no_border_left)
        sheet.merge_range('D2:E2', u'Санхүү эдийн засгийн сайдын 2002 оны',  no_border_left)
        sheet.merge_range('D3:E3', u'06 дугаар сарын 28 ны өдрийн 182 тоот', no_border_left) 
        sheet.merge_range('D4:E4', u'тушаалаар батлав.', no_border_left)
        sheet.write('B3', u'Төлбөрийн даалгавар', no_border_bold_right)
        sheet.write('C3', u'%s'%data['name'], no_border_bold_center)
        sheet.write('B4', u'%s'%data['date'], no_border_right)


        sheet.write('A5', u'Төлөгч', no_border)
        sheet.write('C5', u'ДАНС', no_border_center)
        sheet.merge_range('D5:E5', u'ДҮН', no_border)

        sheet.write('A6', u'Код', border_left)
        sheet.write('B6', '%s'%data['company_name'], border_center)
        sheet.write('C6', u'Дебет', border_center)
        sheet.merge_range('D6:E9', data['amount'], border_center)
        
        sheet.write('A7', u'Төлөгчийн', border_left)
        sheet.write('B7', '%s'%data['com_bank_name'], border_center)
        sheet.write('C7', '%s'%data['com_account_number'], border_center)

        sheet.merge_range('A8:C8', u'Хүлээн авагч:', border_left)

        sheet.write('A9', u'Код', border_left)
        sheet.write('B9', '%s'%data['partner_bank_name'], border_center)
        sheet.write('C9', u'Кредит', border_center)


        sheet.merge_range('A10:C10', u'Мөнгөн дүн (тоогоор)  %s'%data['amount'], no_border)
        sheet.merge_range('A11:C11', u'Мөнгөн дүн (үсгээр) %s'%data['amount_text'], no_border)

        sheet.merge_range('D10:E11', u'....хоногийн......хувийн........торгууль бүгд.......төг.........мөн', text_wrap)

        sheet.merge_range('A12:C12', u'Барааг хүлээн авсан буюу ажил үйлчилгээг гүйцэтгэсэн огноо', no_border_left)
        sheet.merge_range('D12:E13', u'Дүн(торгуулийн хамт)', border_center)

        sheet.merge_range('A13:C13', data['date'], border_center_bold)

        sheet.merge_range('A14:C14', u'Төлбөрийн зориулалт  (Барааны болон ажил үйлчилгээний нэр, дагалдах баримтын дугаар)', )
        sheet.write('D14', u'Гүйлгээний утга', border_center)
        sheet.write('E14', '', border_center)
        sheet.merge_range('A15:C15', data['payment_ref'], border_center_bold)
        sheet.write('D15', u'Төлбөрийн зориулалт', border_center)
        sheet.write('E15', '', border_center)

        sheet.write('B16', u'Захирал:................../ %s /' % data['director_name'])
        sheet.write('C16', u'Банкинд гүйлгээ хийсэн .... оны ... сарын ... өдөр', text_wrap)
        sheet.write('D16', u'Төлөх хугацаа', border_center)
        sheet.write('E16', '', border_center)


        sheet.merge_range('A17:A18', u'Тамга', no_border_no_bold)

        sheet.write('B17', u'СЗА Захирал:................ / Д.Эрдэнэчимэг /')
        sheet.write('C17', u'......................', no_border_center)
        sheet.write('D17', u'Төлбөрийн ээлж', border_center)
        sheet.write('E17', '', border_center)

        sheet.write('B18', u'Ерөнхий нягтлан бодогч:..................../ С.Мөнхтуяа /')
        sheet.write('C18', u'Тэмдэг, гарын үсэг', no_border_no_bold)
      

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()            

    
        


    def get_export_data(self):
        ''' Тайлангийн загварыг боловсруулж өгөгдлүүдийг
            тооцоолж байрлуулна.
        '''
        def name_padding(param):
            l = param['level'] - 2
            return ('  ' * l) + param['name']
        
        context= dict(self._context)
        datas = self.browse(self.id)
        account_line_obj = self.env['account.move.line']
        account_obj = self.env['account.account']
        ezxf = xlwt.easyxf
        styles = self.get_easyxf_styles()      

        book = xlwt.Workbook(encoding='utf8')
        sheet = book.add_sheet('Payment')
        header = ezxf('font: bold on; align: wrap off, vert centre, horiz centre;font: height 220')
        header1 = ezxf('font: bold off; align: wrap off, vert centre, horiz right;font: height 200')
        line = ezxf('font: bold off; align: wrap on, vert centre, horiz left;font: height 200; borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        line_center = ezxf('font: bold off; align: wrap on, vert centre, horiz center;font: height 200; borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        nonline = ezxf('font: bold off; align: wrap off, vert centre, horiz left;font: height 200;')
        sheet.write_merge(0, 0, 0, 4, u'''\t\t\t\t\t\t\t\tСанхүү эдийн засгийн сайдын 2002 оны 6 сарын 28 ны
                                        \t\t\t\t\t\t өдрийн 182 тоот тушаалаар батлав. ''', header1)
        sheet.write_merge(1, 1, 0, 4, u'ТӨЛБӨРИЙН ДААЛГАВАР №', header )
        cre_bnk_code = None
        de_bnk_code = None
        cre_bank_name = None
        de_bank_name = None
        de_account_number = None
        cre_account_number = None
        cre_amount = 0
        de_amount = 0
        res = None
        de_partner = None
        
        amount_text = None
        print("data",context)
        if context['amount'] < 0.0:
            cre_bank_name = context['com_bank_name']
            cre_account_number = context['com_account_number']
            cre_bnk_code = context['com_bnk_code']
            res = context['company']
            de_bank_name = context['partner_bnk_name']
            de_amount = context['amount']
            de_bnk_code = ''
            de_partner = context['partner']
            de_account_number = context['partner_account_number']
            amount_text = context['amount_text']
        else:
            cre_bank_name = context['partner_bnk_name']
            cre_account_number = context['partner_account_number']
            cre_bnk_code = ''
            res = context['partner']
            de_bank_name = context['com_bank_name']
            de_amount = context['amount']
            de_bnk_code = context['com_bnk_code']
            de_partner = context['company']
            de_account_number = context['com_account_number']
            amount_text = context['amount_text']
            
        sheet.write(3, 0, u'Төлөгч:', line)
        sheet.write(3, 1, u'%s'%(res or ''),line)
        sheet.write(3, 2, u'Данс', line)
        sheet.write_merge(3, 3, 3, 4, u'Дүн', line_center)
        sheet.write(4, 0, u'Код', line)
        sheet.write(4, 1, u'%s'%(cre_bnk_code or ''), line)
        sheet.write(4, 2, u'Кредит',line)
        sheet.write_merge(4, 9, 3, 4, de_amount or '',line_center)
        sheet.write(5, 0, u'Төлөгчийн банк',line)
        sheet.write(5, 1, u'%s'%(cre_bank_name or ''),line)
        sheet.write(5, 2, u'%s'%(cre_account_number  or ''), line)
        sheet.write(7, 0, u'Хүлээн авагч',line)
        sheet.write(7, 1, u'%s'%(de_partner or ''),line)
        sheet.write(7, 2, u'Данс',line)
        sheet.write(8, 0, u'Код',line)
        sheet.write(8, 1, u'%s'%(de_bnk_code or ''),line)
        sheet.write(8, 2, u'Дебет',line)
        sheet.write(9, 0, u'Хүлээн авагчийн банк',line)
        sheet.write(9, 1, u'%s'%(de_bank_name or ''),line)
        sheet.write(9, 2, u'%s'%(de_account_number or ''),line)
        sheet.write_merge(10, 10, 0, 2, u'Нийт дүн тоогоор, үсгээр  %s \n (%s)'%(de_amount,amount_text),line_center)
        sheet.write_merge(10, 10, 3, 4, u'...хоногийн.. хувийн торгууль бүгд... төгрөг... мөнгө',line)
        sheet.write_merge(11, 11, 0, 2, u'Барааг худалдан авсан буюу ажил үйлчилгээг гүйцэтгүүлсэн',line)
        sheet.write_merge(12, 12, 0, 2, u'Төлбөрийн зориулалт  /Барааны болон ажил үйлчилгээний нэр, дагалдах баримтын дугаар/',line)
        sheet.write_merge(13, 13, 0, 2, u'%s'%(context['name'] or ''),line_center) 
        sheet.write(12, 3, u'Гүйлгээний утга',line)
        sheet.write(12, 4, u'',line)
        sheet.write(13, 3, u'Төлбөрийн зориулалт',line)
        sheet.write(13, 4, u'',line )
        sheet.write(14, 2, u'Банкинд гүйлгээ хийсэн',nonline)
        sheet.write_merge(14, 15, 3, 3, u'Төлөх хугацаа',line)
        sheet.write(14, 4, u'%s'%(context['date'] or ''),line)
        sheet.write(15, 4, u'',line)
        sheet.write(15, 0, u'\t\tЕрөнхий захирал________/            /', nonline )
        sheet.write(15, 2, u'%s'%(context['date'] or ''),nonline )
        sheet.write(17, 0, u'\t\tЕрөнхий НЯБО ______________/             /', nonline )
        sheet.write(16, 0, u'Тамга',nonline )
        sheet.write(16, 2, u'',nonline )
        sheet.write(17, 2, u'Тэмдэг, гарын үсэг ',nonline )
        sheet.write_merge(16, 17, 3, 3, u'Төлбөрийн ээлж',line )
        sheet.write(16, 4, u'',line )
        sheet.write(17, 4, u'',line )
        

        
        sheet.write_merge(19, 19, 0, 4, u'''\t\t\t\t\t\t\t\tСанхүү эдийн засгийн сайдын 2002 оны 6 сарын 28 ны
                                        \t\t\t\t\t\t өдрийн 182 тоот тушаалаар батлав. ''', header1)
        sheet.write_merge(20, 20, 0, 4, u'ТӨЛБӨРИЙН ДААЛГАВАР №', header )        
        sheet.write(22, 0, u'Төлөгч:', line)
        sheet.write(22, 1, u'%s'%(res or ''),line)
        sheet.write(22, 2, u'Данс', line)
        sheet.write_merge(22, 22, 3, 4, u'Дүн', line_center)
        sheet.write(23, 0, u'Код', line)
        sheet.write(23, 1, u'%s'%(cre_bnk_code or ''), line)
        sheet.write(23, 2, u'Кредит',line)
        sheet.write_merge(23, 28, 3, 4, de_amount or '',line_center)
        sheet.write(24, 0, u'Төлөгчийн банк',line)
        sheet.write(24, 1, u'%s'%(cre_bank_name or ''),line)
        sheet.write(24, 2, u'%s'%(cre_account_number or ''),line)
        sheet.write(26, 0, u'Хүлээн авагч',line)
        sheet.write(26, 1, u'%s'%(de_partner or ''),line)
        sheet.write(26, 2, u'Данс',line)
        sheet.write(27, 0, u'Код',line)
        sheet.write(27, 1, u'%s'%(de_bnk_code or ''),line)
        sheet.write(27, 2, u'Дебит',line)
        sheet.write(28, 0, u'Хүлээн авагчийн банк',line)
        sheet.write(28, 1, u'%s'%(de_bank_name or ''),line)
        sheet.write(28, 2, u'%s'%(de_account_number or ''),line)
        sheet.write_merge(29, 29, 0, 2, u'Нийт дүн тоогоор, үсгээр  %s \n (%s)'%(de_amount,amount_text),line_center)
        sheet.write_merge(29, 29, 3, 4, u'...хоногийн.. хувийн торгууль бүгд... төгрөг... мөнгө',line)
        sheet.write_merge(30, 30, 0, 2, u'Барааг худалдан авсан буюу ажил үйлчилгээг гүйцэтгүүлсэн',line)
        sheet.write_merge(31, 31, 0, 2, u'Төлбөрийн зориулалт  /Барааны болон ажил үйлчилгээний нэр, дагалдах баримтын дугаар/',line)
        sheet.write_merge(32, 32, 0, 2, u'%s'%(context['name'] or ''),line_center)
        sheet.write(31, 3, u'Гүйлгээний утга',line)
        sheet.write(31, 4, u'',line)
        sheet.write(32, 3, u'Төлбөрийн зориулалт',line)
        sheet.write(32, 4, u'',line )
        sheet.write(33, 2, u'Банкинд гүйлгээ хийсэн',nonline)
        sheet.write_merge(33, 34, 3, 3, u'Төлөх хугацаа',line)
        sheet.write(33, 4, u'%s'%(context['date']),line)
        sheet.write(34, 4, u'',line)
        sheet.write(34, 0, u'\t\tЕрөнхий захирал________/            /', nonline )
        sheet.write(34, 2, u'%s'%(context['date'] or ''),nonline )
        sheet.write(36, 0, u'\t\tЕрөнхий НЯБО ______________/             /', nonline )
        sheet.write(35, 0, u'Тамга',nonline )
        sheet.write(35, 2, u'',nonline )
        sheet.write(36, 2, u'Тэмдэг, гарын үсэг ',nonline )
        sheet.write_merge(35, 36, 3, 3, u'Төлбөрийн ээлж',line )
        sheet.write(35, 4, u'',line )
        sheet.write(36, 4, u'',line )        
        
        inch = 1000
        sheet.col(0).width = 4*inch
        sheet.col(1).width = 7*inch
        sheet.col(2).width = 6*inch
        sheet.col(3).width = 5*inch
        sheet.col(4).width = 4*inch
        sheet.row(19).height = 800
        sheet.row(12).height = 600
        sheet.row(0).height = 800
        sheet.row(1).height = 500
        sheet.row(6).height = 300
        sheet.row(7).height = 300
        sheet.row(10).height = 600
        sheet.row(13).height = 600
        sheet.row(7).height = 600
        sheet.row(26).height = 600
        sheet.row(9).height = 600
        sheet.row(28).height = 600
        sheet.row(32).height = 600
        sheet.row(29).height = 600
        sheet.row(31).height = 600
        return {'data':book}