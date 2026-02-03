# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import timedelta, datetime
import xlwt, json
from odoo.tools import date_utils
import io
import json
import xlsxwriter

class ProductSummaryReport(models.TransientModel):
    """
        Барааны материалын хураангуй тайлан
    """
    _name = "product.summary.report"
    _description = "Stock summary Report - Mongolia"
    
    
    
    company_id = fields.Many2one('res.company', string=u'Компани', readonly=True,
                                default=lambda self: self.env.user.company_id)
    location_ids = fields.Many2one('stock.location', string=u'Байрлал')
    start_date = fields.Date(string=u'Эхлэх огноо', required=True,
                                    default=fields.Date.context_today)
    end_date = fields.Date(string=u'Дуусах огноо', required=True,
                                    default=fields.Date.context_today)
    categ_id = fields.Many2one('product.category', string=u'Барааны ангилал')
    product_id = fields.Many2one('product.product', string=u'Бараа')
    warehouse_ids = fields.Many2many('stock.warehouse','stock_warehouse_product_summary_rel','report_id','warehouse_ids', string=u'Агуулах')
    type = fields.Selection([('quantity',u'Тоогоор'),
                             ('cost',u'Өртгөөр')], string=u'Төрөл', required=True)
    


    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'date_from': self.start_date,
            'date_to': self.end_date,
            'location_ids':self.location_ids.ids,
            'warehouse_ids': self.warehouse_ids.ids,
            'categ_id':self.categ_id.id,
            'product_id': self.product_id.id,
            'type':self.type,

        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {
                     'model': 'product.summary.report',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'account_move'}
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
                                    'text_wrap': True,
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
        data_left_bold = workbook.add_format({
                                    'align': 'left',
                                    'border': 1,
                                    'font_size': 12,
                                    'text_wrap': True,
                                    'bold': True,
                                    })
        
        data_center = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'font_size': 12,
                                    'text_wrap': True,
                                    'num_format': '#,##0.00'
                                    })
        data_center_bold = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'font_size': 12,
                                    'text_wrap': True,
                                    'bold': True,
                                    })


        
        sheet.merge_range('A1:D1', u'Байгууллагын нэр: %s' %(data['company_name']), head_title)
        sheet.merge_range('A2:I2', u'Барааны материалын товчоо тайлан', head_title)

        rowx = 4
        sheet.set_column(1, 1, 30)
        sheet.set_column(2, 20, 15)
        
        if data['type'] == 'cost':
            sheet.merge_range('J3:M3', u'Тайлант хугацаа: %s - %s'%(data['date_from'],data['date_to']), head_title )
            sheet.merge_range('A%s:A%s'%(rowx, rowx+1), u'Д/д', data_center_bold)
            sheet.merge_range('B%s:B%s'%(rowx, rowx+1), u'Барааны нэр', data_center_bold)
            sheet.merge_range('C%s:C%s'%(rowx, rowx+1), u'Барааны код', data_center_bold)
            sheet.merge_range('D%s:D%s'%(rowx, rowx+1), u'Дотоод код', data_center_bold)
            sheet.merge_range('E%s:E%s'%(rowx, rowx+1), u'Барааны хэмжих нэгж', data_center_bold)
            sheet.merge_range('F%s:G%s'%(rowx, rowx), u'Барааны эхний үлдэгдэл', data_center_bold)
            sheet.write('F%s'%(rowx+1), u'Тоо', data_center_bold)
            sheet.write('G%s'%(rowx+1), u'Нийт өртөг', data_center_bold)
            sheet.merge_range('H%s:I%s'%(rowx, rowx), u'Барааны орлого', data_center_bold)
            sheet.write('H%s'%(rowx+1), u'Тоо', data_center_bold)
            sheet.write('I%s'%(rowx+1), u'Нийт өртөг', data_center_bold)
            sheet.merge_range('J%s:K%s'%(rowx, rowx), u'Барааны зарлага', data_center_bold)
            sheet.write('J%s'%(rowx+1), u'Тоо', data_center_bold)
            sheet.write('K%s'%(rowx+1), u'Нийт өртөг', data_center_bold)
            sheet.merge_range('L%s:M%s'%(rowx, rowx), u'Барааны эцсийн үлдэгдэл', data_center_bold)
            sheet.write('L%s'%(rowx+1), u'Тоо', data_center_bold)
            sheet.write('M%s'%(rowx+1), u'Нийт өртөг', data_center_bold)
            
    
        else:
            sheet.merge_range('F3:I3', u'Тайлант хугацаа: %s - %s'%(data['date_from'],data['date_to']), head_title )
            sheet.merge_range('A%s:A%s'%(rowx, rowx+1), u'Д/д', data_center_bold)
            sheet.merge_range('B%s:B%s'%(rowx, rowx+1), u'Барааны нэр', data_center_bold)
            sheet.merge_range('C%s:C%s'%(rowx, rowx+1), u'Барааны код', data_center_bold)
            sheet.merge_range('D%s:D%s'%(rowx, rowx+1), u'Дотоод код', data_center_bold)
            sheet.merge_range('E%s:E%s'%(rowx, rowx+1), u'Барааны хэмжих нэгж', data_center_bold)
            sheet.merge_range('F%s:F%s'%(rowx, rowx+1), u'Барааны эхний үлдэгдэл', data_center_bold)
            sheet.merge_range('G%s:G%s'%(rowx, rowx+1), u'Барааны орлого', data_center_bold)
            sheet.merge_range('H%s:H%s'%(rowx, rowx+1), u'Барааны зарлага', data_center_bold)
            sheet.merge_range('I%s:I%s'%(rowx, rowx+1), u'Барааны эцсийн үлдэгдэл', data_center_bold)
            
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
                        sw.name AS warehouse,
                        pt.name ->> 'mn_MN' AS product_name,
                        pp.default_code AS product_code,
                        pp.barcode AS internal_code,
                        uom.name ->> 'mn_MN' AS uom,
                
                        SUM(CASE
                            WHEN sm.date < %s
                             AND dest.usage = 'internal'
                            THEN sml.delivered_qty
                            WHEN sm.date < %s
                             AND src.usage = 'internal'
                            THEN -sml.delivered_qty
                            ELSE 0 END
                        ) AS opening_qty,
                
                        SUM(CASE
                            WHEN sm.date BETWEEN %s AND %s
                             AND dest.usage = 'internal'
                            THEN sml.delivered_qty
                            ELSE 0 END
                        ) AS in_qty,
                
                        SUM(CASE
                            WHEN sm.date BETWEEN %s AND %s
                             AND src.usage = 'internal'
                            THEN sml.delivered_qty
                            ELSE 0 END
                        ) AS out_qty
                
                    FROM stock_move_line sml
                    JOIN stock_move sm ON sm.id = sml.move_id
                
                    JOIN stock_location src ON src.id = sml.location_id
                    JOIN stock_location dest ON dest.id = sml.location_dest_id
                
                    JOIN stock_warehouse sw
                        ON dest.id = sw.lot_stock_id
                
                    JOIN product_product pp ON pp.id = sml.product_id
                    JOIN product_template pt ON pt.id = pp.product_tmpl_id
                    JOIN uom_uom uom ON uom.id = sml.product_uom_id
                
                    WHERE sm.state = 'done'
                      AND sml.company_id = %s
                
                    
                """
            params = [
                data['date_from'],
                data['date_from'],
                data['date_from'],
                data['date_to'],
                data['date_from'],
                data['date_to'],
                data['company_id']
            ]
            
            if len(location_id)==1:
                query += " AND sw.lot_stock_id = %s"
                params.append(location_id[0])
            elif len(location_id)>1:
                query += " AND sw.lot_stock_id in %s"
                params.append(tuple(location_id))
            
            query += """
                GROUP BY
                        sw.name,
                        pt.name,
                        pp.default_code,
                        pp.barcode,
                        uom.name
                
                ORDER BY sw.name, pt.name
            """
            
            self.env.cr.execute(query, params)
            rows = self.env.cr.dictfetchall()

            row = 5
            current_wh = None
            index = 1
            
            for r in rows:
                # Warehouse header
                if r['warehouse'] != current_wh:
                    sheet.merge_range(
                        row, 0, row, 8,
                        f"Агуулах: {r['warehouse']}",
                        data_left
                    )
                    row += 1
                    current_wh = r['warehouse']
                    index = 1
            
                opening = r['opening_qty'] or 0
                incoming = r['in_qty'] or 0
                outgoing = r['out_qty'] or 0
                closing = opening + incoming - outgoing
            
                sheet.write_row(row, 0, [
                    f"{index:.2f}",          # Д/д
                    r['product_name'],       # Барааны нэр
                    r['product_code'],       # Барааны код
                    r['internal_code'],      # Дотоод код
                    r['uom'],                # Хэмжих нэгж
                    opening,                 # Эхний үлдэгдэл
                    incoming,                # Орлого
                    outgoing,                # Зарлага
                    closing,                 # Эцсийн үлдэгдэл
                ], data_right)
            
                row += 1
                index += 1


        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()



