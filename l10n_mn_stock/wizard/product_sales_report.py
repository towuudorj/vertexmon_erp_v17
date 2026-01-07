# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import timedelta, datetime
import xlwt, json
from odoo.tools import date_utils
import io
import json
import xlsxwriter

class ProductSalesReport(models.TransientModel):
    """
        Барааны материалын эргэцийн тайлан
    """
    _name = "product.sales.report"
    _description = "Product sales Report - Mongolia"
    
    
    
    company_id = fields.Many2one('res.company', string=u'Компани', readonly=True,
                                default=lambda self: self.env.user.company_id)
    start_date = fields.Date(string=u'Эхлэх огноо', required=True,
                                    default=fields.Date.context_today)
    end_date = fields.Date(string=u'Дуусах огноо', required=True,
                                    default=fields.Date.context_today)
    categ_id = fields.Many2one('product.category', string=u'Барааны ангилал')
    product_id = fields.Many2one('product.product', string=u'Бараа')
    warehouse_ids = fields.Many2many('stock.warehouse','product_sales_warehouse_product_rel','report_id','warehouse_ids', string=u'Агуулах')
    


    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'warehouse_ids': self.warehouse_ids.ids,
            'categ_id':self.categ_id.id,
            'product_id': self.product_id.id,

        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {
                     'model': 'product.sales.report',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'product_sales_report'}
        }

    def get_xlsx_report(self, data, response):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        head = workbook.add_format({
                                    'align': 'right', 
                                    'font_size': 12
                                    })
        head_title = workbook.add_format({
                                    'align': 'center', 
                                    'font_size': 16,
                                    'bold': True
                                    })
        txt_center = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'font_size': 12,
                                    'bold': True
                                })
        data_right = workbook.add_format({
                                    'align': 'right',
                                    'border': 1,
                                    'font_size': 12,
                                    'text_wrap': True,
                                    'num_format': '#,##0.00'
                                    })
        data_left = workbook.add_format({
                                    'align': 'left',
                                    'border': 1,
                                    'font_size': 12,
                                    'text_wrap': True,
                                    'num_format': '#,##0.00'
                                    })
        
        data_center = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'font_size': 12,
                                    'text_wrap': True,
                                    'num_format': '#,##0.00'
                                    })

        product_obj = self.env['product.product']
        category_obj = self.env['product.category']
        category_id = False
        product_id = False
        if data['categ_id']:
            category_id = data['categ_id']
        if data['product_id']:
            product_id = data['product_id']

        
        sheet.merge_range('A1:D1', u'Байгууллагын нэр: %s' % (data['company_name']), data_left)
        
        sheet.merge_range('A2:M2', u'Барааны материалын насжилтын тайлан', head_title)
        
        sheet.merge_range('K3:M3', u'Тайлант хугацаа: %s - %s'%(data['start_date'],data['end_date']), data_left )

        rowx = 4
        sheet.set_column(1, 1, 30)
        sheet.set_column(2, 20, 15)
        sheet.write('A%s'%(rowx), u'Д/д', data_right)
        sheet.write('B%s'%(rowx), u'Барааны нэр', data_right)
        sheet.write('C%s'%(rowx), u'Барааны код', data_right)
        sheet.write('D%s'%(rowx), u'Агуулах', data_right)
        sheet.write('E%s'%(rowx), u'Орлого хийсэн огноо', data_right)
        sheet.write('F%s'%(rowx), u'Зарлага хийсэн огноо', data_right)
        sheet.write('G%s'%(rowx), u'Орлогын тоо хэмжээ', data_right)
        sheet.write('H%s'%(rowx), u'Зарлагын тоо хэмжээ', data_right)
        sheet.write('I%s'%(rowx), u'Дундаж хадгалсан хоног', data_right)
        sheet.write('J%s'%(rowx), u'Үлдэгдэл тоо хэмжээ', data_right)
        sheet.write('K%s'%(rowx), u'Нэгж үнэ (₮)', data_right)
        sheet.write('L%s'%(rowx), u'Нийт үнэ (₮)', data_right)
        sheet.write('M%s'%(rowx), u'Насжилтын ангилал', data_right)
        
        
        self.env.cr.execute("""
                            SELECT
                            pt.name,
                            pp.default_code,
                            sw.name as wh_name,
                            MIN(CASE WHEN sl.usage = 'internal' THEN sm.date::date END),
                            MAX(CASE WHEN sl.usage != 'internal' THEN sm.date::date END),
                            SUM(CASE WHEN sl.usage = 'internal' THEN sml.quantity ELSE 0 END),
                            SUM(CASE WHEN sl.usage != 'internal' THEN sml.quantity ELSE 0 END),
                            AVG(CURRENT_DATE - sm.date::date)::INT,
                            SUM(CASE WHEN sl.usage = 'internal' THEN sml.quantity ELSE -sml.quantity END),
                            svl.unit_cost
                        FROM stock_move_line sml
                        JOIN stock_move sm ON sm.id = sml.move_id
                        JOIN stock_location sl ON sl.id = sml.location_dest_id
                        JOIN product_product pp ON pp.id = sml.product_id
                        JOIN product_template pt ON pt.id = pp.product_tmpl_id
                        LEFT JOIN stock_warehouse sw ON sw.lot_stock_id = sl.id
                        LEFT JOIN stock_valuation_layer svl ON svl.product_id = pp.id
                        WHERE sm.state = 'done' and pp.id = %s
                        GROUP BY pt.name, pp.default_code, sw.name, svl.unit_cost
                            """%(data['product_id']))
        income = self.env.cr.dictfetchall()
        rowx +=1
        row = 3
        num = 1
        for i, r in enumerate(income, start=1):
            total_value = (r['sum'] or 0) * (r['unit_cost'] or 0)
            total_value = 0
            print("sssss")
            age = r['avg'] or 0
            if age <= 30:
                bucket = "0–30 хоног"
            elif age <= 60:
                bucket = "31–60 хоног"
            elif age <= 90:
                bucket = "61–90 хоног"
            else:
                bucket = "90+ хоног"

            sheet.write_row(row, 0, [
                i, r['name']['mn_MN'], r['default_code'], r['wh_name'],
                r['min'], r['max'],
                r['sum'],
                age, r['avg'],
                r['unit_cost'], total_value, bucket
            ], data_left)
            row += 1
            num +=1

       
    
                
   
                  

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()



