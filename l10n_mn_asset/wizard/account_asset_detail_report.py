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
    category_id = fields.Many2one('account.asset.category', string='Asset category')
    owner_id = fields.Many2one('hr.employee', string='Owner')
    is_extra = fields.Boolean(string=u'Задаргаатай эсэх')
    group_by = fields.Selection([('category', u'Хөрөнгийн ангилал'), ('location', u'Хөрөнгийн байрлал')], string=u"Бүлэглэх", default=False)
    group_by_category = fields.Boolean(string=u"Хөрөнгийн ангиллаар бүлэглэх", default=False)
    see_closed_scraped = fields.Boolean(string=u"Хаагдсан акталсан хөрөнгийг харах", default=False)


    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'category_id': self.category_id.id,
            'owner_id':self.owner_id.id,
            'is_extra':self.is_extra,
            'group_by':self.group_by,
            'see_closed_scraped':self.see_closed_scraped,
            'group_by_category':self.group_by_category,
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
                                    'num_format': 'General'
                                })
        
        data_bold_center = workbook.add_format({
                                    'align': 'center',
                                    'bold': True,
                                    'font_size': 12,
                                    'num_format': '#,##0.00;(#,##0.00)'
                                })

        sheet.set_column(0, 0, 6)
        sheet.set_column(1, 1, 30)
        sheet.set_column(2, 2, 40)
        sheet.set_column(3, 19, 15)
        start_date = datetime.strptime(data['start_date'], "%Y-%m-%d").date()
        sheet.merge_range("A1:B1", u'Байгууллагын нэр: %s' % (data['company_name']), header_txt)
        sheet.merge_range("A3:L3" if data['is_extra'] else 'A3:Q3', u'Үндсэн хөрөнгийн дэлгэрэнгүй тайлан', head)
        sheet.merge_range("I1:L1" if data['is_extra'] else 'N1:Q1',  u'Санхүү Эдийн Засгийн сайдын 2002 оны', header_txt)
        sheet.merge_range("J2:L2" if data['is_extra'] else 'O2:Q2',  u'191 тоот тушаалаар батлав.', header_txt)
        sheet.merge_range("K4:L4" if data['is_extra'] else 'P4:Q4', u'Дэлгэрэнгүй бүртгэл',header_txt)
        sheet.write("L5" if data['is_extra'] else 'Q5', u'ҮХ-1 №....', header_txt)
        sheet.write("E5" if data['is_extra'] else 'L5', u'Тайлант %s - %s'%(start_date,data['end_date']), header_txt)
        rowx = 7
        asset_obj = self.env['account.asset.asset']
        num = 1
        last_group_data = {'last_row': False, 'last_id': False, 'seq':0}
        if data['is_extra']:
            sheet.merge_range("A%s:A%s" % (rowx, rowx + 1), u'Д/д', title)
            sheet.merge_range("B%s:B%s" % (rowx, rowx + 1), u'Хөрөнгийн ангилал', title)
            sheet.merge_range("C%s:C%s" % (rowx, rowx + 1), u'Үндсэн хөрөнгийн нэр', title)
            sheet.merge_range("D%s:D%s" % (rowx, rowx + 1), u'Хөрөнгийн дугаар', title)
            sheet.merge_range("E%s:E%s" % (rowx, rowx + 1), u'Ашиглалтанд орсон он сар өдөр', title)
            sheet.merge_range("F%s:F%s" % (rowx, rowx + 1), u'Ашиглах жил', title)
            sheet.merge_range("G%s:G%s" % (rowx, rowx + 1), u'Эхний үлдэгдэл', title)
            sheet.merge_range("H%s:J%s" % (rowx, rowx), u'Элэгдэл', title)
            sheet.write("H%s" % (rowx + 1), u'Хуримтдлагдсан', title)
            sheet.write("I%s" % (rowx + 1), u'Сарын', title)
            sheet.write("J%s" % (rowx + 1), u'Элэгдлийн дүн', title)
            sheet.merge_range("K%s:K%s" % (rowx, rowx + 1), u'Зарлагадсан', title)
            sheet.merge_range("L%s:L%s" % (rowx, rowx + 1), u'Үлдэгдэл өртөг', title)
            rowx = 9
            domain = [('company_id', '=', data['company_id']), ('state', '!=', 'draft')]
            if data['category_id']:
                domain.append(('category_id', '=', data['category_id']))
            if data['owner_id']:
                domain.append(('owner_id', '=', data['owner_id']))
            if not data['see_closed_scraped']:
                domain.append(('state', 'not in', ['close', 'scrap']))
            order_by = ""
            if data['group_by'] == 'category':
                order_by = u'category_id asc, '
            if data['group_by'] == 'location':
                order_by = u'asset_location_id asc, '
            order_by += u'name asc, '

            asset_id = asset_obj.search(domain, order=order_by + 'date asc')

            if asset_id:
                total_g = 0
                total_h = 0
                total_i = 0
                total_j = 0
                total_k = 0
                total_l = 0
                for line in asset_id:
                    if data['group_by']:
                        if data['group_by'] == 'location':
                            if not last_group_data['last_row'] or last_group_data['last_id'] != line.asset_location_id.id:
                                if last_group_data['last_row']:
                                    sheet.write('G%s' % last_group_data['last_row'],
                                                "=SUM(G%s:G%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                                    sheet.write('H%s' % last_group_data['last_row'],
                                                "=SUM(H%s:H%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                                    sheet.write('I%s' % last_group_data['last_row'],
                                                "=SUM(I%s:I%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                                    sheet.write('J%s' % last_group_data['last_row'],
                                                "=SUM(J%s:J%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                                    sheet.write('K%s' % last_group_data['last_row'],
                                                "=SUM(K%s:K%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                                    sheet.write('L%s' % last_group_data['last_row'],
                                                "=SUM(L%s:L%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                                last_group_data['seq'] += 1
                                sheet.write("A%s"%rowx, last_group_data['seq'], data_center)
                                sheet.merge_range("B%s:F%s" % (rowx, rowx), line.asset_location_id.name, title)
                                last_group_data['last_id'] = line.asset_location_id.id
                                last_group_data['last_row'] = rowx
                                rowx += 1
                                num = 1

                        if data['group_by'] == 'category':
                            if not last_group_data['last_row'] or last_group_data['last_id'] != line.category_id.id:
                                if last_group_data['last_row']:
                                    sheet.write('G%s' % last_group_data['last_row'],
                                                "=SUM(G%s:G%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                                    sheet.write('H%s' % last_group_data['last_row'],
                                                "=SUM(H%s:H%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                                    sheet.write('I%s' % last_group_data['last_row'],
                                                "=SUM(I%s:I%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                                    sheet.write('J%s' % last_group_data['last_row'],
                                                "=SUM(J%s:J%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                                    sheet.write('K%s' % last_group_data['last_row'],
                                                "=SUM(K%s:K%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                                    sheet.write('L%s' % last_group_data['last_row'],
                                                "=SUM(L%s:L%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                                last_group_data['seq'] += 1
                                sheet.write("A%s" % rowx, last_group_data['seq'], data_center)
                                sheet.merge_range("B%s:F%s" % (rowx, rowx), line.category_id.name, title)
                                last_group_data['last_id'] = line.category_id.id
                                last_group_data['last_row'] = rowx
                                rowx += 1
                                num = 1

                    sequence = num if not data['group_by'] else str(last_group_data['seq']) + '.' + str(num)
                    sheet.write("A%s"%rowx, sequence, data_center)
                    sheet.write("B%s"%rowx, line.category_id.name, data_left)
                    sheet.write("C%s"%rowx, line.name, data_left)
                    sheet.write("D%s"%rowx, line.code, data_left)
                    sheet.write("E%s"%rowx, '%s'%line.date, data_left)
                    sheet.write("F%s"%rowx, line.method_number/12, data_left)
                    dep_line = line.depreciation_line_ids.search([('depreciation_date', '<', data['start_date']),
                                                                  ('move_check', '=', True ),
                                                                  ('asset_id', '=', line.id)], order='depreciation_date desc', limit=1)
                    sheet.write("G%s"%rowx, dep_line.remaining_value if dep_line else line.value, data_left)
                    sheet.write("H%s"%rowx, dep_line.depreciated_value if dep_line else 0, data_left)

                    month_dep = 0
                    for de in line.depreciation_line_ids:
                        if de.sequence != 1:
                            month_dep = de.amount
                            break
                    sheet.write("I%s"%rowx, month_dep, data_left)

                    dep_lines = line.depreciation_line_ids.filtered(lambda x: x.move_check and not x.is_sale_line and data['start_date'] <= str(x.depreciation_date) <= data['end_date'])
                    if dep_lines:
                        date_between_dep = sum(dep_lines.mapped('amount'))
                    else:
                        date_between_dep = 0
                    sheet.write("J%s" % rowx, date_between_dep, data_left)
                    sale_line = False
                    if line.state=='close':
                        sale_line = line.depreciation_line_ids.filtered(lambda x: x.is_sale_line)
                    sheet.write("K%s" % rowx, sale_line.amount if sale_line else 0, data_left)
                    sheet.write("L%s" % rowx, '=G%s-J%s-K%s' % (rowx, rowx, rowx), data_left)
                    total_g += dep_line.remaining_value if dep_line else line.value
                    total_h += dep_line.depreciated_value if dep_line else 0
                    total_i += month_dep
                    total_j += date_between_dep
                    # total_k += 0
                    total_l += dep_line.remaining_value if dep_line else line.value - date_between_dep
                    num += 1
                    rowx += 1
                if data['group_by']:
                    if data['group_by'] == 'location':
                        if last_group_data['last_row']:
                            sheet.write('G%s' % last_group_data['last_row'],
                                        "=SUM(G%s:G%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                            sheet.write('H%s' % last_group_data['last_row'],
                                        "=SUM(H%s:H%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                            sheet.write('I%s' % last_group_data['last_row'],
                                        "=SUM(I%s:I%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                            sheet.write('J%s' % last_group_data['last_row'],
                                        "=SUM(J%s:J%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                            sheet.write('K%s' % last_group_data['last_row'],
                                        "=SUM(K%s:K%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                    if data['group_by'] == 'category':
                        if last_group_data['last_row']:
                            sheet.write('G%s' % last_group_data['last_row'],
                                        "=SUM(G%s:G%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                            sheet.write('H%s' % last_group_data['last_row'],
                                        "=SUM(H%s:H%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                            sheet.write('I%s' % last_group_data['last_row'],
                                        "=SUM(I%s:I%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                            sheet.write('J%s' % last_group_data['last_row'],
                                        "=SUM(J%s:J%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                            sheet.write('K%s' % last_group_data['last_row'],
                                        "=SUM(K%s:K%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                sheet.merge_range("A%s:F%s" % (rowx, rowx), u'Нийт', title)
                sheet.write("G%s" % rowx, total_g, data_left)
                sheet.write("H%s" % rowx, total_h, data_left)
                sheet.write("I%s" % rowx, total_i, data_left)
                sheet.write("J%s" % rowx, total_j, data_left)
                sheet.write("K%s" % rowx, total_k, data_left)
                sheet.write("L%s" % rowx, total_l, data_left)
        else:
            where = f"WHERE (aaa.invoice_id is not null OR aaa.state!='draft') AND aaa.active=True AND aaa.company_id = {data['company_id']} "
            if data['category_id']:
                where += f"AND aac.id = '{data['category_id']}' "
            if data['owner_id']:
                where += f"AND aaa.owner_id = '{data['owner_id']}' "

            qry = f"""
                        select
                        	sub.category_id, sub.location_id, sub.category, sub.location, sub.acc_dep_balance, sub.expense_dep, sub.month_dep, sub.dep_balance, sub1.*
                        FROM (
                        	select 
            	                SUM(CASE WHEN aadl.depreciation_date < '{data['start_date']}' AND aadl.move_id is not null AND am.state='posted' AND aaa.state not in ('close', 'scrap') THEN aadl.amount ELSE 0 END) as acc_dep_balance,
            	                COALESCE(SUM(CASE WHEN aaa.method_end BETWEEN '{data['start_date']}' AND '{data['end_date']}' AND aaa.state = 'close' and aadl.is_sale_line = True
            	                                       THEN aadl.amount ELSE 0 END), 0) as expense_dep,
            	                SUM(CASE WHEN aadl.sequence = 2 THEN aadl.amount ELSE 0 END) as month_dep,
            	                SUM(CASE WHEN aadl.depreciation_date BETWEEN '{data['start_date']}' AND '{data['end_date']}' AND aadl.move_id is not null AND am.state='posted' AND aaa.state not in ('close', 'scrap') THEN aadl.amount ELSE 0 END) as dep_balance,
            	                aaa.name,
            	                aac.id as category_id,
            	                al.id as location_id,
            	                aac.name as category,
            	                al.name as location
            	            from account_asset_asset aaa
                            LEFT JOIN account_asset_depreciation_line aadl on aadl.asset_id = aaa.id
            	            LEFT JOIN account_asset_category aac on aac.id = aaa.category_id
            	            LEFT JOIN asset_location al on al.id = aaa.asset_location_id
            	            LEFT JOIN account_move am on am.id = aadl.move_id
            	            {where}
            	            GROUP BY aaa.name, aac.id, al.id
                        ) as sub
                        left join (
                        	select aaa.name,
            	            	COALESCE(SUM(CASE WHEN aaa.date < '{data['start_date']}' then aaa.value else 0 end), 0) as start_balance,
            	                COALESCE(count(distinct CASE WHEN aaa.date < '{data['start_date']}' then aaa.id else null end), 0) as start_count,
            	                COALESCE(SUM(CASE WHEN aaa.date BETWEEN '{data['start_date']}' AND '{data['end_date']}' THEN aaa.value else 0 end), 0) as income_balance,
            	                COALESCE(SUM(CASE WHEN aaa.date BETWEEN '{data['start_date']}' AND '{data['end_date']}' THEN 1 ELSE 0 END), 0) as income_count,
            	                COALESCE(SUM(CASE WHEN line.dep_date BETWEEN '{data['start_date']}' AND '{data['end_date']}' AND aaa.state in ('close', 'scrap') THEN aaa.value ELSE 0 END), 0) as expense_balance,
            	                COALESCE(SUM(CASE WHEN line.dep_date BETWEEN '{data['start_date']}' AND '{data['end_date']}' AND aaa.state in ('close', 'scrap') THEN 1 ELSE 0 END), 0) as expense_count
                            from account_asset_asset aaa
                            left join (
                                select depreciation_date as dep_date, asset_id, RANK() OVER (PARTITION BY asset_id ORDER BY depreciation_date DESC) AS rank
                                from account_asset_depreciation_line
                                where is_scrap_line = True or is_sale_line = True
                            ) as line on line.asset_id = aaa.id
                            where line.rank = 1 or line.rank is null
            	            GROUP BY aaa.name
                        ) as sub1 on sub1.name = sub.name
                        {'ORDER BY sub.category_id' if data['group_by_category'] else ''}
            """

            self.env.cr.execute(qry)
            lines = self._cr.dictfetchall()
            sheet.merge_range("A%s:A%s" % (rowx, rowx + 1), u'Д/д', title)
            sheet.merge_range("B%s:B%s" % (rowx, rowx + 1), u'Хөрөнгийн ангилал', title)
            sheet.merge_range("C%s:C%s" % (rowx, rowx + 1), u'Үндсэн хөрөнгийн нэр', title)

            sheet.merge_range("D%s:E%s"%(rowx, rowx), u'Эхний үлдэгдэл', title)
            sheet.write("D%s"%(rowx+1), u'Тоо', title)
            sheet.write("E%s"%(rowx+1), u'Өртөг', title)
            sheet.merge_range("F%s:G%s"%(rowx, rowx), u'Орлого', title)
            sheet.write("F%s"%(rowx+1), u'Тоо', title)
            sheet.write("G%s"%(rowx+1), u'Өртөг', title)
            sheet.merge_range("H%s:I%s"%(rowx, rowx), u'Зарлага', title)
            sheet.write("H%s"%(rowx+1), u'Тоо', title)
            sheet.write("I%s"%(rowx+1), u'Өртөг', title)
            sheet.merge_range("J%s:K%s"%(rowx, rowx), u'Эцсийн үлдэгдэл', title)
            sheet.write("J%s"%(rowx+1), u'Тоо', title)
            sheet.write("K%s"%(rowx+1), u'Өртөг', title)
            sheet.merge_range("L%s:P%s"%(rowx, rowx), u'Элэгдэл', title)
            sheet.write("L%s"%(rowx+1), u'Элэгдээгүй дүн', title)
            sheet.write("M%s"%(rowx+1), u'Хуримтдлагдсан элэгдэл', title)
            sheet.write("N%s"%(rowx+1), u'Сарын', title)
            sheet.write("O%s"%(rowx+1), u'Хасагдсанд ногдох', title)
            sheet.write("P%s"%(rowx+1), u'Элэгдлийн дүн', title)
            sheet.merge_range("Q%s:Q%s"%(rowx, rowx+1), u'Үлдэгдэл өртөг', title)
            total_d = 0
            total_e = 0
            total_f = 0
            total_g = 0
            total_h = 0
            total_i = 0
            total_j = 0
            total_k = 0
            total_l = 0
            total_m = 0
            total_n = 0
            total_o = 0
            total_p = 0
            total_q = 0
            rowx = 9
            for line in lines:
                if data['group_by_category']:
                    if not last_group_data['last_id'] or last_group_data['last_id'] != line['category_id']:
                        last_group_data['seq'] += 1
                        sheet.write("A%s" % rowx, last_group_data['seq'], data_center)
                        sheet.merge_range("B%s:D%s" % (rowx, rowx), line['category'], title)

                        if last_group_data['last_id']:
                            sheet.write('D%s' % last_group_data['last_row'], "=SUM(D%s:D%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                            sheet.write('E%s' % last_group_data['last_row'], "=SUM(E%s:E%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                            sheet.write('F%s' % last_group_data['last_row'], "=SUM(F%s:F%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                            sheet.write('G%s' % last_group_data['last_row'], "=SUM(G%s:G%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                            sheet.write('H%s' % last_group_data['last_row'], "=SUM(H%s:H%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                            sheet.write('I%s' % last_group_data['last_row'], "=SUM(I%s:I%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                            sheet.write('J%s' % last_group_data['last_row'], "=SUM(J%s:J%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                            sheet.write('K%s' % last_group_data['last_row'], "=SUM(K%s:K%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                            sheet.write('L%s' % last_group_data['last_row'], "=SUM(L%s:L%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                            sheet.write('M%s' % last_group_data['last_row'], "=SUM(M%s:M%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                            sheet.write('N%s' % last_group_data['last_row'], "=SUM(N%s:N%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                            sheet.write('O%s' % last_group_data['last_row'], "=SUM(O%s:O%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                            sheet.write('P%s' % last_group_data['last_row'], "=SUM(P%s:P%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                            sheet.write('Q%s' % last_group_data['last_row'], "=SUM(Q%s:Q%s)" % (last_group_data['last_row']+1, rowx - 1), data_right)
                        last_group_data['last_row'] = rowx
                        rowx += 1
                        num = 1
                        last_group_data['last_id'] = line['category_id']

                sequence = num if not data['group_by_category'] else str(last_group_data['seq']) + '.' + str(num)
                sheet.write("A%s" % rowx, sequence, data_center)
                sheet.write("B%s" % rowx, line['category'], data_left)
                sheet.write("C%s" % rowx, line['name'], data_left)
                sheet.write("D%s" % rowx, line['start_count'], data_left)
                sheet.write("E%s" % rowx, line['start_balance'], data_left)
                sheet.write("F%s" % rowx, line['income_count'], data_left)
                sheet.write("G%s" % rowx, line['income_balance'], data_left)
                sheet.write("H%s" % rowx, line['expense_count'], data_left)
                sheet.write("I%s" % rowx, line['expense_balance'], data_left)
                sheet.write("J%s" % rowx, '=D%s+F%s-H%s' % (rowx, rowx, rowx), data_left)
                sheet.write("K%s" % rowx, '=E%s+G%s-I%s' % (rowx, rowx, rowx), data_left)
                sheet.write("L%s" % rowx, '=K%s-M%s'  % (rowx, rowx), data_left)
                sheet.write("M%s" % rowx, line['acc_dep_balance'], data_left)
                sheet.write("N%s" % rowx, line['month_dep'], data_left)
                sheet.write("O%s" % rowx, line['expense_dep'], data_left)
                sheet.write("P%s" % rowx, line['dep_balance'], data_left)
                sheet.write("Q%s" % rowx, '=L%s-P%s' % (rowx, rowx), data_left)
                rowx += 1
                num += 1
                total_d += line['start_count']
                total_e += line['start_balance']
                total_f += line['income_count']
                total_g += line['income_balance']
                total_h += line['expense_count']
                total_i += line['expense_balance']
                total_j += line['start_count'] + line['income_count'] - line['expense_count']
                total_k += line['start_balance'] + line['income_balance'] -  line['expense_balance']
                total_l += line['start_balance'] + line['income_balance'] -  line['expense_balance'] - line['acc_dep_balance']
                total_m += line['acc_dep_balance']
                total_n += line['month_dep']
                total_o += line['expense_dep']
                total_p += line['acc_dep_balance'] + line['month_dep'] - line['expense_dep']
                total_q += line['start_balance'] + line['income_balance'] -  line['expense_balance'] - (line['acc_dep_balance'] + line['month_dep'] - line['expense_dep'])
            if data['group_by_category'] and last_group_data['last_id']:
                sheet.write('D%s' % last_group_data['last_row'], "=SUM(D%s:D%s)" % (last_group_data['last_row'] + 1, rowx - 1), data_right)
                sheet.write('E%s' % last_group_data['last_row'], "=SUM(E%s:E%s)" % (last_group_data['last_row'] + 1, rowx - 1), data_right)
                sheet.write('F%s' % last_group_data['last_row'], "=SUM(F%s:F%s)" % (last_group_data['last_row'] + 1, rowx - 1), data_right)
                sheet.write('G%s' % last_group_data['last_row'], "=SUM(G%s:G%s)" % (last_group_data['last_row'] + 1, rowx - 1), data_right)
                sheet.write('H%s' % last_group_data['last_row'], "=SUM(H%s:H%s)" % (last_group_data['last_row'] + 1, rowx - 1), data_right)
                sheet.write('I%s' % last_group_data['last_row'], "=SUM(I%s:I%s)" % (last_group_data['last_row'] + 1, rowx - 1), data_right)
                sheet.write('J%s' % last_group_data['last_row'], "=SUM(J%s:J%s)" % (last_group_data['last_row'] + 1, rowx - 1), data_right)
                sheet.write('K%s' % last_group_data['last_row'], "=SUM(K%s:K%s)" % (last_group_data['last_row'] + 1, rowx - 1), data_right)
                sheet.write('L%s' % last_group_data['last_row'], "=SUM(L%s:L%s)" % (last_group_data['last_row'] + 1, rowx - 1), data_right)
                sheet.write('M%s' % last_group_data['last_row'], "=SUM(M%s:M%s)" % (last_group_data['last_row'] + 1, rowx - 1), data_right)
                sheet.write('N%s' % last_group_data['last_row'], "=SUM(N%s:N%s)" % (last_group_data['last_row'] + 1, rowx - 1), data_right)
                sheet.write('O%s' % last_group_data['last_row'], "=SUM(O%s:O%s)" % (last_group_data['last_row'] + 1, rowx - 1), data_right)
                sheet.write('P%s' % last_group_data['last_row'], "=SUM(P%s:P%s)" % (last_group_data['last_row'] + 1, rowx - 1), data_right)
                sheet.write('Q%s' % last_group_data['last_row'], "=SUM(Q%s:Q%s)" % (last_group_data['last_row'] + 1, rowx - 1), data_right)
            sheet.merge_range("A%s:C%s" % (rowx, rowx), u'Нийт', data_center)
            sheet.write("D%s" % rowx, total_d, data_left)
            sheet.write("E%s" % rowx, total_e, data_left)
            sheet.write("F%s" % rowx, total_f, data_left)
            sheet.write("G%s" % rowx, total_g, data_left)
            sheet.write("H%s" % rowx, total_h, data_left)
            sheet.write("I%s" % rowx, total_i, data_left)
            sheet.write("J%s" % rowx, total_j, data_left)
            sheet.write("K%s" % rowx, total_k, data_left)
            sheet.write("L%s" % rowx, total_l, data_left)
            sheet.write("M%s" % rowx, total_m, data_left)
            sheet.write("N%s" % rowx, total_n, data_left)
            sheet.write("O%s" % rowx, total_o, data_left)
            sheet.write("P%s" % rowx, total_p, data_left)
            sheet.write("Q%s" % rowx, total_q, data_left)

        sheet.merge_range("B%s:E%s"%(rowx + 3, rowx + 3), u'Хөтөлсөн нягтлан бодогч....................................../\
                                                 /', data_bold_center)
        sheet.merge_range("B%s:E%s"%(rowx + 5, rowx + 5), u'Хянасан ерөнхий (ахлах) нягтлан бодогч....................................../\
                                                 /', data_bold_center)

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()