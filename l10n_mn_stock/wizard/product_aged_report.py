# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import timedelta, datetime
import xlwt, json
from odoo.tools import date_utils
import io
import json
import xlsxwriter

class ProductAgedReport(models.TransientModel):
    """
        Барааны материалын дэлгэрэнгүй тайлан
    """
    _name = "product.aged.report"
    _description = "Product aged Report - Mongolia"
    
    
    
    company_id = fields.Many2one('res.company', string=u'Компани', readonly=True,
                                default=lambda self: self.env.user.company_id)
    start_date = fields.Date(string=u'Эхлэх огноо', required=True,
                                    default=fields.Date.context_today)
    end_date = fields.Date(string=u'Дуусах огноо', required=True,
                                    default=fields.Date.context_today)
    categ_id = fields.Many2one('product.category', string=u'Барааны ангилал')
    product_id = fields.Many2one('product.product', string=u'Бараа')
    warehouse_ids = fields.Many2many('stock.warehouse','product_aged_warehouse_product_rel','report_id','warehouse_ids', string=u'Агуулах')
    


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
                     'model': 'product.aged.report',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'product_aged_report'}
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
        
        data_center = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'font_size': 12,
                                    'text_wrap': True,
                                    'num_format': '#,##0.00'
                                    })
        
        sheet.merge_range('A1:D1', u'Байгууллагын нэр: %s' % (data['company_name']), data_left)
        
        sheet.merge_range('A2:M2', u'Барааны материалын насжилтын тайлан', head_title)
        
        sheet.merge_range('K3:M3', u'Тайлант хугацаа: %s - %s'%(data['start_date'],data['end_date']), data_left )

        rowx = 4
        sheet.set_column(1, 1, 30)
        sheet.set_column(2, 20, 15)
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
        
        
        sheet.write_row(3, 0, [
                        "Д/д",
                        "Барааны нэр",
                        "Барааны код",
                        "Агуулах",
                        "Орлого хийсэн огноо",
                        "Зарлага хийсэн огноо",
                        "Орлогын тоо хэмжээ",
                        "Зарлагын тоо хэмжээ",
                        "Дундаж хадгалсан хоног",
                        "Үлдэгдэл тоо хэмжээ",
                        "Нэгж үнэ (₮)",
                        "Нийт үнэ (₮)",
                        "Насжилтын ангилал"
                    ], head_title)
        
        
        query = """
                SELECT
                    pt.name ->> 'mn_MN' AS name,
                    pp.default_code AS default_code,
                    sw.name AS wh_name,
            
                    MIN(CASE WHEN src.usage = 'supplier' THEN sm.date::date END) AS first_in,
                    MAX(CASE WHEN dest.usage = 'customer' THEN sm.date::date END) AS last_out,
            
                    SUM(CASE WHEN dest.usage = 'internal' THEN sml.delivered_qty ELSE 0 END) AS qty_in,
                    SUM(CASE WHEN src.usage = 'internal' THEN sml.delivered_qty ELSE 0 END) AS qty_out,
            
                    AVG(CURRENT_DATE - sm.date::date)::INT AS avg_age,
            
                    SUM(CASE
                        WHEN dest.usage = 'internal' THEN sml.delivered_qty
                        WHEN src.usage = 'internal' THEN -sml.delivered_qty
                        ELSE 0 END
                    ) AS balance_qty,
            
                    AVG(svl.unit_cost) AS unit_cost
            
                FROM stock_move_line sml
                JOIN stock_move sm ON sm.id = sml.move_id
            
                JOIN stock_location src ON src.id = sml.location_id
                JOIN stock_location dest ON dest.id = sml.location_dest_id
            
                JOIN product_product pp ON pp.id = sml.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
            
                LEFT JOIN stock_warehouse sw ON sw.lot_stock_id = dest.id
                LEFT JOIN stock_valuation_layer svl ON svl.product_id = pp.id
            
                WHERE sm.state = 'done'
                  AND sml.company_id = %s
            """
        params = [data['company_id']]
        
        if len(location_id)==1:
            query += " AND sw.lot_stock_id = %s"
            params.append(location_id[0])
        elif len(location_id)>1:
            query += " AND sw.lot_stock_id in %s"
            params.append(tuple(location_id))
        
        if data.get('product_id'):
            query += " AND pp.id = %s"
            params.append(data['product_id'])
        elif data.get('categ_id'):
            query += " AND pt.categ_id = %s"
            params.append(data['categ_id'])
        
        
        query += """
            GROUP BY
                pt.name,
                pp.default_code,
                sw.name
        """
        
        self.env.cr.execute(query, tuple(params))
        income = self.env.cr.dictfetchall()

        row = 4

        for i, r in enumerate(income, start=1):
            qty_in = r['qty_in'] or 0
            qty_out = r['qty_out'] or 0
            balance_qty = r['balance_qty'] or 0
        
            unit_cost = r['unit_cost'] or 0
            total_value = balance_qty * unit_cost
        
            avg_age = r['avg_age'] or 0
            if avg_age <= 30:
                bucket = "0–30 хоног"
            elif avg_age <= 60:
                bucket = "31–60 хоног"
            elif avg_age <= 90:
                bucket = "61–90 хоног"
            else:
                bucket = "90+ хоног"
        
            sheet.write_row(row, 0, [
                i,                    # Д/д
                r['name'],            # Барааны нэр
                r['default_code'],    # Барааны код
                r['wh_name'],         # Агуулах
                '%s'%r['first_in'],        # Орлого хийсэн огноо
                '%s'%r['last_out'],        # Зарлага хийсэн огноо
                qty_in,               # Орлогын тоо хэмжээ
                qty_out,              # Зарлагын тоо хэмжээ
                avg_age,              # Дундаж хадгалсан хоног
                balance_qty,          # Үлдэгдэл тоо хэмжээ
                unit_cost,            # Нэгж үнэ
                total_value,          # Нийт үнэ
                bucket                # Насжилтын ангилал
            ], data_right)
            row += 1


       
    
                
   
                  

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()



