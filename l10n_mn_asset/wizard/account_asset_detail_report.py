# -*- coding: utf-8 -*-

import io
import json
import xlsxwriter
from odoo import fields, models
from odoo.tools import date_utils
from datetime import datetime

class AccountAssetDetailReport(models.TransientModel):
    """
        Үндсэн хөрөнгийн дэлгэрэнгүй тайлан
    """
    _name = "account.asset.detail.report"
    _description = "Asset detial Report - Mongolia"
    
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)
    start_date = fields.Date(string='Start date', required=True)
    end_date = fields.Date(string='End date', required=True)
    fiscalyear_id = fields.Many2one('account.fiscal.year', string='Fiscal year', required=True)
    category_id = fields.Many2one('account.asset.category', string='Asset category')
    owner_id = fields.Many2one('hr.employee', string='Owner')


    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'category_id': self.category_id.id,
            'owner_id':self.owner_id.id,
            'fiscalyear_id': self.fiscalyear_id.id,
            'is_balance':False,
        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {'model': 'account.asset.detail.report',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'Account asset report'}
        }

    def get_xlsx_report(self, data, response):
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
                                    'font_size': 12
                                })

        title = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'bold': True,
                                    'font_size': 12,
                                    'text_wrap': True,
                                })
        data_right = workbook.add_format({
                                    'align': 'right',
                                    'border': 1,
                                    'text_wrap': True,
                                    'font_size': 12,
                                    'num_format': '#,##0.00;(#,##0.00)'
                                })
        data_left = workbook.add_format({
                                    'align': 'left',
                                    'border': 1,
                                    'font_size': 12,
                                    'num_format': '#,##0.00;(#,##0.00)'
                                })
        
        data_center = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'font_size': 12,
                                    'num_format': '#,##0.00;(#,##0.00)'
                                })


        data_bold_left = workbook.add_format({
                                    'align': 'left',
                                    'bold': True,
                                    'border': 1,
                                    'font_size': 12,
                                    'num_format': '#,##0.00;(#,##0.00)'
                                })
        
        data_bold_center = workbook.add_format({
                                    'align': 'center',
                                    'bold': True,
                                    'border': 1,
                                    'font_size': 12,
                                    'num_format': '#,##0.00;(#,##0.00)'
                                })

        sheet.set_column(0, 0, 6)
        sheet.set_column(1, 1, 30)
        sheet.set_column(2, 2, 40)
        sheet.set_column(3, 19, 15)
        start_date = datetime.strptime(data['start_date'], "%Y-%m-%d").date()
        sheet.merge_range("A1:B1", u'Байгууллагын нэр: %s' % (data['company_name']), header_txt)
        sheet.merge_range("A3:S3", u'Үндсэн хөрөнгийн дэлгэрэнгүй тайлан', head)
        sheet.merge_range("P1:S1",  u'Санхүү Эдийн Засгийн сайдын 2002 оны', header_txt)
        sheet.merge_range("Q2:S2",  u'191 тоот тушаалаар батлав.', header_txt)
        sheet.merge_range("R4:S4", u'Дэлгэрэнгүй бүртгэл',header_txt)
        sheet.merge_range("S5", u'ҮХ-1 №....', header_txt)
        sheet.write("H5", u'Тайлант %s - %s'%(start_date,data['end_date']), header_txt)
        rowx = 7

        sheet.merge_range("A%s:A%s"%(rowx, rowx+1), u'Д/д', title)
        sheet.merge_range("B%s:B%s"%(rowx, rowx+1), u'Дансны дугаар', title)
        sheet.merge_range("C%s:C%s"%(rowx, rowx+1), u'Үндсэн хөрөнгийн нэр', title)
        sheet.merge_range("D%s:D%s"%(rowx, rowx+1), u'Хөрөнгийн дугаар', title)
        sheet.merge_range("E%s:E%s"%(rowx, rowx+1), u'Ашиглалтанд орсон он сар өдөр', title)
        sheet.merge_range("F%s:F%s"%(rowx, rowx+1), u'Ашиглах жил', title)
        sheet.merge_range("G%s:H%s"%(rowx, rowx), u'Эхний үлдэгдэл', title)
        sheet.write("G%s"%(rowx+1), u'Тоо', title)
        sheet.write("H%s"%(rowx+1), u'Өртөг', title)
        sheet.merge_range("I%s:J%s"%(rowx, rowx), u'Орлого', title)
        sheet.write("I%s"%(rowx+1), u'Тоо', title)
        sheet.write("J%s"%(rowx+1), u'Өртөг', title)
        sheet.merge_range("K%s:L%s"%(rowx, rowx), u'Зарлага', title)
        sheet.write("K%s"%(rowx+1), u'Тоо', title)
        sheet.write("L%s"%(rowx+1), u'Өртөг', title)
        sheet.merge_range("M%s:N%s"%(rowx, rowx), u'Эцсийн үлдэгдэл', title)
        sheet.write("M%s"%(rowx+1), u'Тоо', title)
        sheet.write("N%s"%(rowx+1), u'Өртөг', title)
        sheet.merge_range("O%s:R%s"%(rowx, rowx), u'Элэгдэл', title)
        sheet.write("O%s"%(rowx+1), u'Хуримтдлагдсан', title)
        sheet.write("P%s"%(rowx+1), u'Сарын', title)
        sheet.write("Q%s"%(rowx+1), u'Хасагдсанд ногдох', title)
        sheet.write("R%s"%(rowx+1), u'Элэгдлийн дүн', title)
        sheet.merge_range("S%s:S%s"%(rowx, rowx+1), u'Үлдэгдэл өртөг', title)
        rowx +=2

        sheet.write("A%s"%rowx, 1,title)
        sheet.write("B%s"%rowx, 2,title)
        sheet.write("C%s"%rowx, 3,title)
        sheet.write("D%s"%rowx, 4,title)
        sheet.write("E%s"%rowx, 5,title)
        sheet.write("F%s"%rowx, 6,title)
        sheet.write("G%s"%rowx, 7,title)
        sheet.write("H%s"%rowx, 8,title)
        sheet.write("I%s"%rowx, 9,title)
        sheet.write("J%s"%rowx, 10,title)
        sheet.write("K%s"%rowx, 11,title)
        sheet.write("L%s"%rowx, 12,title)
        sheet.write("M%s"%rowx, 13,title)
        sheet.write("N%s"%rowx, 14,title)
        sheet.write("O%s"%rowx, 15,title)
        sheet.write("P%s"%rowx, 16,title)
        sheet.write("Q%s"%rowx, 17,title)
        sheet.write("R%s"%rowx, 18,title)
        sheet.write("S%s"%rowx, 19,title)

        rowx = 10
        asset_obj = self.env['account.asset.asset']
        fiscalyear_id = self.env['account.fiscal.year'].browse(data['fiscalyear_id'])
        
        asset_capital_obj = self.env['account.asset.asset.capitalization']
        domain = [('company_id','=',data['company_id']),('state','!=','draft')]
        if data['category_id']:
            domain.append(('category_id','=',data['category_id']))
        if data['owner_id']:
            domain.append(('owner_id', '=', data['owner_id']))
        asset_id = asset_obj.search(domain, order='date asc')
        num = 0
        first_balance = 0.0
        first_qty = 0.0
        
        income_balance = 0.0
        income_qty = 0.0
        
        expense_balance = 0.0
        expense_qty = 0.0
        
        last_balance = 0.0
        last_qty = 0.0
        
        in_dep_balance = 0.0
        month_balance = 0.0
        drop_balance = 0.0
        dep_balance = 0.0
        total_balance_amount = 0.0

        if asset_id:
            for line in asset_id:
                if data['is_balance'] == True:
                    if line.value_residual > 0.0:
                        balance_amount = 0.0
                        write_off_amount = 0.0
                        deprecation_amount = 0.0
                        month_deprecation_amount = 0.0
                        act_amount = 0.0
                        capital_amount = 0.0
                        num +=1
                        sheet.write("A%s"%rowx, '%s'%num, data_center)
                        sheet.write("B%s"%rowx, line.category_id.name,data_left)
                        sheet.write("C%s"%rowx, line.name,data_left)
                        sheet.write("D%s"%rowx, line.code,data_left)
                        sheet.write("E%s"%rowx, '%s'%line.date,data_left)
                        sheet.write("F%s"%rowx, line.method_number/12,data_left)
                        sheet.write("G%s"%rowx, data_left)
                        if line.date <= start_date:
                            sheet.write("H%s"%rowx, line.value,data_right)
                            sheet.write("I%s"%rowx, 0, data_right)
                        else:
                            sheet.write("H%s"%rowx, 0,data_right)
                            sheet.write("I%s"%rowx, 0,data_right)
                        #asset_cap_id = asset_capital_obj.search( [('asset_id','=',line.id)])
                        
                        first_balance +=line.value
                        first_qty +=1
                        
                        
                        #if asset_cap_id:
                        #    for cap in asset_cap_id:
                        #        capital_amount += cap.amount
                        #else:
                        #    if line.date >= start_date:
                        #        capital_amount +=line.value
                                
                        income_balance +=capital_amount
                        income_qty +=1
                        act_amount = line.value_residual
                        sheet.write(rowx, 9, capital_amount,data_right)
                        sheet.write(rowx, 10, 1,data_left)
                        sheet.write(rowx, 11, act_amount,data_right)
                        
                        expense_balance +=act_amount
                        expense_qty +=1
                        
                        sheet.write(rowx, 12, 1,data_left)
                        total_amount = line.value+capital_amount-act_amount
                        
                        last_balance +=total_amount
                        last_qty +=1
                        sheet.write(rowx, 13, total_amount,data_right)
                        for lis in line.depreciation_line_ids:
                            for history in lis.move_id.line_ids:
                                if history.date < start_date:
                                    deprecation_amount +=history.debit
                        in_dep_balance +=deprecation_amount
                        sheet.write(rowx, 14, deprecation_amount,data_right)                
                        for dep in line.depreciation_line_ids:
                            if dep.move_check == True:
                                if dep.depreciation_date >= start_date and dep.depreciation_date<=self.end_date:
                                    month_deprecation_amount += dep.amount
                                    
                        month_balance +=month_deprecation_amount
                        sheet.write("P%s"%rowx, month_deprecation_amount,data_right)
                        if line.state == 'close':
                            write_off = 0.0
                            self._cr.execute("""SELECT
                                   SUM(l.debit-l.credit) AS amount
                                FROM
                                    account_move_line l
                                WHERE
                                    l.asset_id = %s GROUP BY l.asset_id """, (line.id,))
                            res=self._cr.dictfetchall()
                            if res !=[]:
                                for lines in res:
                                    write_off = lines['amount']
                            write_off_amount = line.value_residual
                        drop_balance +=write_off_amount
                        sheet.write("Q%s"%rowx, write_off_amount,data_right)
                        last_amount = deprecation_amount+month_deprecation_amount-write_off_amount
                        sheet.write("R%s"%rowx, last_amount,data_right)
                        dep_balance +=last_amount
                        if line.state=='close':                          
                            balance_amount = 0.0
                        else:
                            balance_amount = total_amount-last_amount
                        sheet.write("S%s"%rowx, balance_amount,data_right)
                        total_balance_amount += balance_amount
                        rowx +=1
                else:
                
                    balance_amount = 0.0
                    write_off_amount = 0.0
                    deprecation_amount = 0.0
                    deprecation_amounts = 0.0
                    month_deprecation_amount = 0.0
                    act_amount = 0.0
                    capital_amount = 0.0
                    in_amount = 0.0
                    first_value = 0.0
                    
                    
                    num +=1
                    sheet.write("A%s"%rowx, '%s'%num,data_center)
                    sheet.write("B%s"%rowx, line.category_id.name,data_left)
                    sheet.write("C%s"%rowx, line.name,data_left)
                    sheet.write("D%s"%rowx, line.code,data_left)
                    sheet.write("E%s"%rowx, '%s'%line.date,data_left)
                    sheet.write("F%s"%rowx, line.method_number/12,data_left)
                    if str(line.date) <= str(start_date):
                        fact_amounts = 0.0
                        fact_amount = 0.0
                        fact_amountsd =0.0
                        if fiscalyear_id.date_from == start_date:
                            if line.state=='close':
                                if line.scrap_date <= start_date:
                                    first_value = 0.0
                                else:
                                    first_value = line.value
                                
                            else:
                                #or dep in line.depreciation_line_ids:
                                #        if dep.move_check == True:
                                #            if dep.depreciation_date < start_date:
                                #                fact_amountsd += dep.amount
                                first_value = line.value
                        else:
                            
                            first_value = line.value
                        first_balance +=first_value
                        first_qty +=1
                        count = 1
                        sheet.write("G%s"%rowx, count, data_left)
                        sheet.write("H%s"%rowx, first_value,data_right)
                        #sheet.write("I%s"%rowx, 0,data_right)
                    else:
                        count = 0
                        sheet.write("G%s"%rowx, count, data_left)
                        sheet.write("H%s"%rowx, 0,data_right)
                        #
                    #asset_cap_id = asset_capital_obj.search([('asset_id','=',line.id)])
                    
                    #print ("dddddd",asset_cap_id)
                    
                    
                    #if asset_cap_id:
                    #    for cap in asset_cap_id:
                    #        capital_amount += cap.amount
                        
                    #else:
                    if str(line.date) > str(start_date) and str(line.date) <= str(data['end_date']):
                            in_amount +=line.value
                                
                    income_balance +=capital_amount+in_amount
                    income_qty +=1

                    sheet.write("I%s"%rowx, 1,data_right)
                    sheet.write("J%s"%rowx, capital_amount+in_amount,data_right)
                    
                    if line.state=='close':
                        act_amounts = 0.0
                        if self.fiscalyear_id.date_from == start_date:
                            if line.scrap_date <= start_date:
                                for dep in line.depreciation_line_ids:
                                        if dep.depreciation_date<=self.end_date:
                                            act_amounts += dep.amount
                                act_amountd = line.value - act_amounts
                            else:
                                act_amountd = line.value
                           # print("addddddddddddddddddddfff",act_amountd)
                            if int(act_amountd) == 0.0:
                                #if line.is_closed == True:
                                    act_amount = 0.0
                            else:
                                act_amount = act_amountd
                        else:
                            if line.scrap_date <= self.end_date:
                                for dep in line.depreciation_line_ids:
                                    if dep.depreciation_date<=self.end_date:
                                            act_amounts += dep.amount
                            act_amountd = line.value - act_amounts
                            if int(act_amountd) == 0.0:
                                act_amount = line.value
                            else:
                                act_amount = 0.0
                    if act_amount == 0.0:
                        sheet.write("K%s"%rowx, 0,data_left)
                    else:
                        sheet.write("K%s"%rowx, 1, data_left)
                        expense_qty +=1
                    
                    sheet.write("L%s"%rowx, act_amount,data_right)
                    
                    expense_balance +=act_amount
                    
                    
                    sheet.write("M%s"%rowx, 1,data_left)
                    total_amount = 0.0
                    if first_value == 0.0:
                        #print("aaaaaaaaaaaaaaaaaaaaaaaaaaaa dsdssssssssssssssss",in_amount,line.name)
                        if in_amount == 0.0:
                            total_amount = 0.0
                        else:
                            total_amount = first_value+capital_amount+in_amount-act_amount
                    else:
                        total_amount = first_value+capital_amount+in_amount-act_amount
                    
                    last_balance +=total_amount
                    last_qty +=1
                    #print("aaaaaaaaaaaaaaaaaaaaaaaaaaaadddd",total_amount,line.name)
                    sheet.write("N%s"%rowx, total_amount,data_right)
                    if line.state == 'close':
                        for lis in line.depreciation_line_ids:
                            if lis.move_check == True:
                                for history in lis.move_id.line_ids:
                                    if history.date < start_date:
                                        if lis.move_id.state != 'cancel':
                                            deprecation_amount +=history.debit
                        #print("aaaaadddddddddddddddddddddddd",line.value, deprecation_amount)
                        act_amountds = line.value - deprecation_amount
                        if int(act_amountds) == 0.0:
                            if line.scrap_date <=start_date:
                                deprecation_amount = 0.0
                                deprecation_amounts = 0.0
                            else:
                                deprecation_amount = deprecation_amount
                                deprecation_amounts = deprecation_amount
                        else:
                            if line.scrap_date <=start_date:
                                deprecation_amount = 0.0
                                deprecation_amounts = 0.0
                            else:
                                deprecation_amount = deprecation_amount
                                deprecation_amounts = deprecation_amount

                            
                    else:
                        for lis in line.depreciation_line_ids:
                            if lis.move_check == True:
                                for history in lis.move_id.line_ids:
                                    if lis.move_id.state != 'cancel':
                                        if history.date < start_date:
                                            deprecation_amount +=history.debit
                    #print("aaaaaaaaaaaaaaaaaaaa",)
                    if total_amount == 0.0:
                        deprecation_amount = deprecation_amount
                        in_dep_balance +=deprecation_amount
                    else:
                        deprecation_amount = deprecation_amount
                        in_dep_balance +=deprecation_amount
                    sheet.write("O%s"%rowx, deprecation_amount,data_right)                
                    for lis in line.depreciation_line_ids:
                       # for history in lis.move_id.line_ids:
                           # if history.move_id.state =='posted':
                            if str(lis.depreciation_date) >= str(start_date) and str(lis.depreciation_date) <= str(data['end_date']):
                                month_deprecation_amount +=lis.amount
                                
                    month_balance +=month_deprecation_amount
                    
                    sheet.write("P%s"%rowx, month_deprecation_amount,data_right)
                    if line.state == 'close':
                        write_off = 0.0
                        self._cr.execute("""SELECT
                               SUM(l.debit-l.credit) AS amount
                            FROM
                                account_move_line l
                                left join account_move am
                                on am.id = l.move_id
                            WHERE
                                l.asset_id = %s
                                and am.date <= %s GROUP BY l.asset_id """, (line.id,data['end_date']))
                        res=self._cr.dictfetchall()
                        if res !=[]:
                            for lines in res:
                                write_off = lines['amount']
                                
                        #print("aaaaaaaaaaaaaaaaaaaaaaaaaa",write_off_amount,total_amount,line.name,deprecation_amounts,month_deprecation_amount,deprecation_amount)
                        if round(write_off_amount,2) == round(total_amount,2):
                            if deprecation_amounts > 0.0:
                                write_off_amount = month_deprecation_amount + deprecation_amounts
                            else:
                                write_off_amount = month_deprecation_amount + deprecation_amount
                        else:
                            for dep in line.depreciation_line_ids:
                                if dep.move_check == True:
                                    if dep.depreciation_date >= start_date and dep.depreciation_date<= data['end_date']:
                                            if deprecation_amounts >0.0:
                                                write_off_amount = month_deprecation_amount + deprecation_amounts
                                            else:
                                                write_off_amount = month_deprecation_amount + deprecation_amount
                                    else:
                                            write_off_amount = 0.0
                                else:
                                    if deprecation_amounts > 0.0:
                                        write_off_amount = month_deprecation_amount + deprecation_amount
                                    else:
                                        write_off_amount = month_deprecation_amount + deprecation_amount
                        
                    
                    if line.state == 'close':
                        if line.scrap_date <= start_date:
                            sheet.write("Q%s"%rowx, 0.0,data_right)
                            #drop_balance = 0.0
                        else:
                            sheet.write("Q%s"%rowx, write_off_amount,data_right)
                            drop_balance += write_off_amount
                    else:
                        sheet.write("Q%s"%rowx, write_off_amount,data_right)
                        drop_balance +=write_off_amount
                    #print("aaaaaaaaaaaaaaaaaaaaaaaa",write_off_amount,deprecation_amounts,month_deprecation_amount)
                    if deprecation_amounts >0.0:
                        last_amount = deprecation_amounts + month_deprecation_amount-write_off_amount
                    else:
                        last_amount = deprecation_amount + month_deprecation_amount-write_off_amount
                    sheet.write("R%s"%rowx, last_amount,data_right)
                    dep_balance +=last_amount
                    if line.state == 'close':
                        bal_amounts = 0.0
                        for dep in line.depreciation_line_ids:
                            if dep.move_check == True:
                                if dep.depreciation_date >= start_date and dep.depreciation_date<=data['end_date']:
                                    bal_amounts += dep.amount
                        act_amountd = line.value - bal_amounts
                        if act_amountd == 0.0:
                            balance_amount = 0.0
                        else:
                            if write_off_amount > 0.0:
                                balance_amount = total_amount
                            else:
                                balance_amount = total_amount-last_amount
                        
                    else:
                        #balance_amount = total_amount-last_amount
                        if write_off_amount > 0.0:
                            balance_amount = 0.0
                        else:
                            balance_amount = total_amount-last_amount
                    sheet.write("S%s"%rowx, balance_amount,data_right)
                    total_balance_amount += balance_amount
                    rowx +=1
                
            sheet.merge_range("A%s:F%s"%(rowx, rowx), 'НИЙТ',data_right)
            sheet.write("G%s"%rowx, first_qty,data_right)
            sheet.write("H%s"%rowx, first_balance,data_right)
            sheet.write("I%s"%rowx, income_qty,data_right)
            sheet.write("J%s"%rowx, income_balance,data_right)
            sheet.write("K%s"%rowx, expense_qty,data_right)
            sheet.write("L%s"%rowx, expense_balance,data_right)
            sheet.write("M%s"%rowx, last_qty,data_right)
            sheet.write("N%s"%rowx, last_balance,data_right)
            sheet.write("O%s"%rowx, in_dep_balance,data_right)
            sheet.write("P%s"%rowx, month_balance,data_right)
            sheet.write("Q%s"%rowx, drop_balance,data_right)
            sheet.write("R%s"%rowx, dep_balance,data_right)
            sheet.write("S%s"%rowx, total_balance_amount,data_right)
                
    
        sheet.write("C%s"%(rowx + 3), u'Хөтөлсөн нягтлан бодогч....................................../\
                                                 /', data_bold_center)
        sheet.write("C%s"%(rowx + 5), u'Хянасан ерөнхий (ахлах) нягтлан бодогч....................................../\
                                                 /', data_bold_center)
    




        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()


    

        
        
        
        
        
        

    