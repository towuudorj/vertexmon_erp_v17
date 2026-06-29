# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import timedelta, datetime, time
import xlwt, json
from odoo.tools import date_utils
import io
import json
import xlsxwriter


class SupplyProductReport(models.TransientModel):
    _name = "supply.product.report"
    _inherit = 'xls.report.base'
    _description = "Supply Product Report - Mongolia"

    company_id = fields.Many2one('res.company', string=u'Компани', readonly=True,
                                 default=lambda self: self.env.user.company_id)
    start_date = fields.Date(string=u'Эхлэх огноо', required=True,
                             default=fields.Date.context_today)
    end_date = fields.Date(string=u'Дуусах огноо', required=True,
                           default=fields.Date.context_today)
    group_by_partner = fields.Boolean('Group by partner', default=False)

    def get_report_data(self):
        data = super(SupplyProductReport, self).get_report_data()
        data.update({
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'date_from': self.start_date,
            'date_to': self.end_date,
            'group_by_partner': self.group_by_partner
        })
        return data

    def action_print_xls_report(self):
        data = self.get_report_data()
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {
                'model': 'supply.product.report',
                'output_format': 'xlsx',
                'options': json.dumps(data,
                                      default=date_utils.json_default),
                'report_name': 'account_move'}
        }

    def get_xlsx_report(self, data, response, get_file=False):
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
            'valign': 'vcenter',
            'num_format': '#,##0.00'
        })

        data_center_bold = workbook.add_format({
            'align': 'center',
            'border': 1,
            'font_size': 12,
            'text_wrap': True,
            'bold': True,
        })

        sheet.set_paper(9)
        sheet.center_horizontally()
        sheet.fit_to_pages(1, 0.5)
        sheet.set_column(0, 0, 5)
        sheet.set_column(1, 1, 16)
        sheet.set_column(2, 2, 60)
        sheet.set_column(3, 20, 18)

        sheet.merge_range('A1:D1', u'Байгууллагын нэр: %s' % (data['company_name']), head_title)
        sheet.merge_range('A2:J2', u'Хангамжийн бараа материалын тайлан', head_title)
        sheet.merge_range('H3:J3', u'Тайлант хугацаа: %s - %s' % (data['date_from'], data['date_to']), head)
        rowx = 4

        sheet.write('A%s' % rowx, u'№', data_center_bold)
        sheet.write('B%s' % rowx, u'Барааны код', data_center_bold)
        sheet.write('C%s' % rowx, u'Барааны нэр', data_center_bold)
        sheet.write('D%s' % rowx, u'Хэмжих нэгж', data_center_bold)
        sheet.write('E%s' % rowx, u'Нэгж өртөг', data_center_bold)
        sheet.write('F%s' % rowx, u'Эхний үлдэгдэл', data_center_bold)
        sheet.write('G%s' % rowx, u'Орлого', data_center_bold)
        sheet.write('H%s' % rowx, u'Зарлага', data_center_bold)
        sheet.write('I%s' % rowx, u'Эцсийн үлдэгдэл', data_center_bold)
        sheet.write('J%s' % rowx, u'Нийт өртөг', data_center_bold)

        date_from = data['date_from']
        date_to = data['date_to']

        group_partner = data.get('group_by_partner', False)

        query = f"""
            WITH svl_sum AS (
            SELECT
                stock_move_id,
                SUM(value) AS value
            FROM stock_valuation_layer
            GROUP BY stock_move_id
        ),
        moves AS (
            SELECT
                mv.product_id,
                {' COALESCE(mv.partner_id, sm.partner_id, sp.partner_id) AS partner_id, ' if group_partner else ''}
                mv.date::date AS move_date,
        
                CASE
                    WHEN sl.supply_location = TRUE
                    THEN -mv.quantity
        
                    WHEN dest.supply_location = TRUE
                    THEN mv.quantity
        
                    ELSE 0
                END AS signed_qty,
        
                CASE
                    WHEN sl.supply_location = TRUE
                    THEN -ABS(COALESCE(svl.value, 0))
        
                    WHEN dest.supply_location = TRUE
                    THEN ABS(COALESCE(svl.value, 0))
        
                    ELSE 0
                END AS signed_value
        
            FROM stock_move_line mv
            JOIN stock_location sl ON sl.id = mv.location_id
            JOIN stock_location dest ON dest.id = mv.location_dest_id
            LEFT JOIN stock_move sm ON sm.id = mv.move_id
            {'LEFT JOIN stock_picking sp ON sp.id = sm.picking_id ' if group_partner else ''}
            LEFT JOIN svl_sum svl ON svl.stock_move_id = sm.id
        
            WHERE mv.state = 'done'
              AND mv.date::date <= '{date_to}'
              AND (sl.supply_location = TRUE OR dest.supply_location = TRUE)
        ),
        report AS (
            SELECT
                product_id,
                {' partner_id, ' if group_partner else ''}
        
                SUM(
                    CASE WHEN move_date < '{date_from}'
                    THEN signed_qty ELSE 0 END
                ) AS opening_qty,
        
                SUM(
                    CASE WHEN move_date BETWEEN '{date_from}' AND '{date_to}'
                     AND signed_qty > 0
                    THEN signed_qty ELSE 0 END
                ) AS debit_quantity,
        
                SUM(
                    CASE WHEN move_date BETWEEN '{date_from}' AND '{date_to}'
                     AND signed_qty < 0
                    THEN ABS(signed_qty) ELSE 0 END
                ) AS credit_quantity,
        
                SUM(signed_qty) AS total_quantity,
                SUM(signed_value) AS total_value
        
            FROM moves
            GROUP BY product_id{', partner_id' if group_partner else ''}
        )
        
        SELECT
            pp.id AS p_id,
            {"COALESCE(rp.name, 'No Partner') AS partner_name," if group_partner else ''}
            {' COALESCE(rp.id, 0) AS partner_id, ' if group_partner else ''}
            r.opening_qty AS quantity,
            r.debit_quantity,
            r.credit_quantity,
            r.total_quantity,
            r.total_value
        FROM report r
        LEFT JOIN product_product pp ON pp.id = r.product_id
       {'LEFT JOIN res_partner rp ON rp.id = r.partner_id' if group_partner else ''}
        
        WHERE r.total_quantity <> 0 OR r.total_value <> 0
        
        {'ORDER BY rp.id' if group_partner else ''}
        """

        self._cr.execute(query)
        data = self._cr.dictfetchall()
        product_obj = self.env['product.product']
        count = 1

        total_quantity = 0
        total_debit_quantity = 0
        total_credit_quantity = 0
        total_t_quantity = 0
        total_value = 0

        partner_total = 0
        last_partner_id = False
        for line in data:
            product = product_obj.browse(line.get('p_id'))
            if group_partner:
                if (isinstance(last_partner_id, bool) and not last_partner_id) or (isinstance(last_partner_id, int) and last_partner_id not in [int(line['partner_id']), 0]):
                    sheet.merge_range(rowx, 0, rowx, 9, line['partner_name'], data_center_bold)
                    last_partner_id = int(line['partner_id'])
                    rowx += 1
            colly = 0
            sheet.write(rowx, colly, count, data_left)
            colly += 1
            sheet.write(rowx, colly, product.default_code, data_left)
            colly += 1
            sheet.write(rowx, colly, product.name, data_left)
            colly += 1
            sheet.write(rowx, colly, product.uom_id.name, data_left)
            colly += 1
            sheet.write(rowx, colly, str(round(product.standard_price, 2)) + product.cost_currency_id.symbol, data_left)
            colly += 1
            sheet.write(rowx, colly, line['quantity'] if not group_partner else line['quantity']*-1, data_right)
            colly += 1
            sheet.write(rowx, colly, line['debit_quantity'] if not group_partner else line['credit_quantity'], data_right)
            colly += 1
            sheet.write(rowx, colly, line['credit_quantity'] if not group_partner else line['debit_quantity'], data_right)
            colly += 1
            sheet.write(rowx, colly, line['total_quantity'] if not group_partner else line['total_quantity']*-1, data_right)
            colly += 1
            sheet.write(rowx, colly, line['total_value'] if not group_partner else line['total_value'], data_right)

            count += 1
            rowx += 1

            total_quantity += line['quantity']
            total_debit_quantity += line['debit_quantity']
            total_credit_quantity += line['credit_quantity']
            total_t_quantity += line['total_quantity']
            total_value += line['total_value']


        sheet.merge_range(f'A%s:E%s' % (rowx, rowx), u'Нийт', data_center_bold)
        sheet.write(f'F%s' % rowx, total_quantity if not group_partner else total_quantity*-1, data_right)
        sheet.write(f'G%s' % rowx, total_debit_quantity if not group_partner else total_credit_quantity, data_right)
        sheet.write(f'H%s' % rowx, total_credit_quantity if not group_partner else total_debit_quantity, data_right)
        sheet.write(f'I%s' % rowx, total_t_quantity if not group_partner else total_t_quantity*-1, data_right)
        sheet.write(f'J%s' % rowx, total_value if not group_partner else total_value, data_right)


        workbook.close()
        output.seek(0)
        if get_file:
            return output.read()
        response.stream.write(output.read())
        output.close()
        return


