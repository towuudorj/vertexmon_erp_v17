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
            'date_from': self.start_date,
            'date_to': self.end_date,
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
                                    'font_size': 14,
                                    'bold': True,
                                    'text_wrap': True,
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
        
        total_format = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'font_size': 12,
                                    'text_wrap': True,
                                    'num_format': '#,##0.00'
                                    })


        
        sheet.merge_range('A1:D1', u'Байгууллагын нэр: %s' % (data['company_name']), data_left)
        
        sheet.merge_range('A2:M2', u'Барааны материалын эргэцийн тайлан', head_title)
        
        sheet.merge_range('H3:J3', u'Тайлант хугацаа: %s - %s'%(data['date_from'],data['date_to']), data_left )

        rowx = 4
        sheet.set_column(1, 1, 30)
        sheet.set_column(2, 20, 15)
        sheet.write_row(3, 0, [
                            "№",
                            "Барааны нэр",
                            "Барааны код",
                            "Эхний үлдэгдэл (₮)",
                            "Худалдан авалт (₮)",
                            "Нийт боломжит дүн (₮)",
                            "Борлуулсан / хэрэглэсэн дүн (₮)",
                            "Эцсийн үлдэгдэл (₮)",
                            "Эргэцийн тоо (удаа)",
                            "Тайлбар",
                        ], head_title)
        
        
        location_obj = self.env['stock.location']
        location_id = []
        if data['warehouse_ids']:
            if len(data['warehouse_ids'])==1:
                location_ids = location_obj.search([('warehouse_id','=',data['warehouse_ids'][0])])
                for loc in location_ids:
                    location_id.append(loc.id)
            else:
                location_id = location_obj.search([('warehouse_id','in',tuple(data['warehouse_ids']))])
                for loc in location_ids:
                    location_id.append(loc.id)
        
        query = """
                SELECT
                    pt.name ->> 'mn_MN' AS name,
                    pp.default_code AS code,
            
                    SUM(CASE
                        WHEN svl.create_date < %s THEN svl.value
                        ELSE 0 END
                    ) AS opening_value,
            
                    SUM(CASE
                        WHEN svl.value > 0
                         AND svl.create_date BETWEEN %s AND %s
                        THEN svl.value
                        ELSE 0 END
                    ) AS purchase_value,
            
                    SUM(CASE
                        WHEN svl.value < 0
                         AND svl.create_date BETWEEN %s AND %s
                        THEN ABS(svl.value)
                        ELSE 0 END
                    ) AS out_value
            
                FROM stock_valuation_layer svl
                JOIN stock_move sm on sm.id = svl.stock_move_id
                JOIN product_product pp ON pp.id = sm.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                
                WHERE svl.company_id = %s
            """
            
        params = [
            data['date_from'],     # эхний үлдэгдэл хүртэл
            data['date_from'],
            data['date_to'],
            data['date_from'],
            data['date_to'],
            data['company_id']
        ]
        
        if len(location_id)==1:
            query += " AND sm.location_id = %s"
            params.append(location_id[0])
        elif len(location_id)>1:
            query += " AND sm.location_id in %s"
            params.append(tuple(location_id))
        query += """
            GROUP BY pt.name, pp.default_code
        """
        
        self.env.cr.execute(query, params)
        records = self.env.cr.dictfetchall()
        row = 4
        total_open = total_buy = total_possible = total_out = total_close = 0
        
        for i, r in enumerate(records, start=1):
            opening = r['opening_value'] or 0
            purchase = r['purchase_value'] or 0
            out_val = r['out_value'] or 0
        
            possible = opening + purchase
            closing = possible - out_val
        
            turnover = round(out_val / possible, 2) if possible else 0
        
            if turnover >= 6:
                note = "Хурдан эргэлттэй"
            elif turnover >= 3:
                note = "Тогтвортой эргэлттэй"
            else:
                note = "Эргэлт удаан"
        
            sheet.write_row(row, 0, [
                i,
                r['name'],
                r['code'],
                opening,
                purchase,
                possible,
                out_val,
                closing,
                turnover,
                note,
            ], data_right)
        
            total_open += opening
            total_buy += purchase
            total_possible += possible
            total_out += out_val
            total_close += closing
        
            row += 1
        sheet.write_row(row, 0, [
                    "",
                    "Нийт дүн:",
                    "",
                    total_open,
                    total_buy,
                    total_possible,
                    total_out,
                    total_close,
                    "",
                    ""
                ], total_format)
                

       
    
                
   
                  

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()



