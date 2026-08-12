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
    partner_ids = fields.Many2many('res.partner', string="Partners")
    filter_by_issue_date = fields.Boolean(string=u'Олгосон огноогоор шүүх', default=False)
    issue_date_filter = fields.Date(string=u'Олгосон огноо')

    def get_report_data(self):
        data = super(SupplyProductReport, self).get_report_data()
        data.update({
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'date_from': self.start_date,
            'date_to': self.end_date,
            'group_by_partner': self.group_by_partner,
            'partner_ids': self.partner_ids.ids,
            'filter_by_issue_date': self.filter_by_issue_date,
            'issue_date_filter': self.issue_date_filter,
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
        sheet.set_column(1, 1, 14)
        sheet.set_column(2, 2, 16)
        sheet.set_column(3, 3, 60)
        sheet.set_column(4, 20, 18)

        sheet.merge_range('A1:D1', u'Байгууллагын нэр: %s' % (data['company_name']), head_title)
        sheet.merge_range('A2:K2', u'Хангамжийн бараа материалын тайлан', head_title)
        sheet.merge_range('I3:K3', u'Тайлант хугацаа: %s - %s' % (data['date_from'], data['date_to']), head)
        rowx = 4

        sheet.write('A%s' % rowx, u'№', data_center_bold)
        sheet.write('B%s' % rowx, u'Олгосон огноо', data_center_bold)
        sheet.write('C%s' % rowx, u'Барааны код', data_center_bold)
        sheet.write('D%s' % rowx, u'Барааны нэр', data_center_bold)
        sheet.write('E%s' % rowx, u'Хэмжих нэгж', data_center_bold)
        sheet.write('F%s' % rowx, u'Нэгж өртөг', data_center_bold)
        sheet.write('G%s' % rowx, u'Эхний үлдэгдэл', data_center_bold)
        sheet.write('H%s' % rowx, u'Орлого', data_center_bold)
        sheet.write('I%s' % rowx, u'Зарлага', data_center_bold)
        sheet.write('J%s' % rowx, u'Эцсийн үлдэгдэл', data_center_bold)
        sheet.write('K%s' % rowx, u'Нийт өртөг', data_center_bold)

        date_from = data['date_from']
        date_to = data['date_to']

        group_partner = data.get('group_by_partner', False)
        partner_where = ''
        if data.get('partner_ids', False):
            partner_where = 'AND rp.id in (%s) ' % ','.join(str(id) for id in data.get('partner_ids'))

        issue_date_filter = fields.Date.to_date(data.get('issue_date_filter')) if data.get('filter_by_issue_date') and data.get('issue_date_filter') else False

        query = f"""
            WITH moves AS (
                SELECT
                    mv.id AS move_line_id,
                    mv.move_id,
                    mv.product_id,
                    {'COALESCE(mv.partner_id, sm.partner_id, sp.partner_id) AS partner_id, ' if group_partner else ''}
                    mv.date::date AS move_date,
                    mv.quantity,
                    sp.issue_date AS issue_date,

                    sl.supply_location AS src_supply_location,
                    dest.supply_location AS dest_supply_location
            
                FROM stock_move_line mv
                JOIN stock_move sm ON sm.id = mv.move_id
                LEFT JOIN stock_picking sp ON sp.id = sm.picking_id
                JOIN stock_location sl ON sl.id = mv.location_id
                JOIN stock_location dest ON dest.id = mv.location_dest_id
                {'LEFT JOIN res_partner rp on rp.id = mv.partner_id' if group_partner else ''}
                WHERE mv.state = 'done'
                  AND mv.date::date <= '{date_to}'
                  {'AND rp.is_company = False '  if group_partner else ''}
                  {partner_where}
                  AND (
                        sl.supply_location = TRUE
                        OR dest.supply_location = TRUE
                  )
            ),
            
            signed_moves AS (
                SELECT
                    move_line_id,
                    product_id,
                    {'partner_id, ' if group_partner else ''}
                    move_date,
                    issue_date,

                    CASE
                        WHEN src_supply_location = TRUE THEN -quantity
                        WHEN dest_supply_location = TRUE THEN quantity
                        ELSE 0
                    END AS signed_qty
            
                FROM moves
            ),
            
            report AS (
                SELECT
                    sm.product_id,
                    {'sm.partner_id, ' if group_partner else ''}
            
                    SUM(
                        CASE
                            WHEN sm.move_date < '{date_from}'
                            THEN sm.signed_qty
                            ELSE 0
                        END
                    ) AS opening_qty,
            
                    SUM(
                        CASE
                            WHEN sm.move_date BETWEEN '{date_from}' AND '{date_to}'
                             AND sm.signed_qty > 0
                            THEN sm.signed_qty
                            ELSE 0
                        END
                    ) AS debit_quantity,
            
                    SUM(
                        CASE
                            WHEN sm.move_date BETWEEN '{date_from}' AND '{date_to}'
                             AND sm.signed_qty < 0
                            THEN ABS(sm.signed_qty)
                            ELSE 0
                        END
                    ) AS credit_quantity,
            
                    SUM(sm.signed_qty) AS total_quantity,

                    MIN(sm.issue_date) AS first_issue_date

                FROM signed_moves sm
                GROUP BY sm.product_id{', sm.partner_id ' if group_partner else ''}
            )
            
            SELECT
                pp.id AS p_id,
                {"COALESCE(rp.name, 'No Partner') AS partner_name, COALESCE(rp.id, 0) AS partner_id," if group_partner else ''}
                
                COALESCE(r.opening_qty, 0) AS quantity,
                COALESCE(r.debit_quantity, 0) AS debit_quantity,
                COALESCE(r.credit_quantity, 0) AS credit_quantity,
                COALESCE(r.total_quantity, 0) AS total_quantity,
                r.first_issue_date AS issue_date
            
            FROM report r
            LEFT JOIN product_product pp ON pp.id = r.product_id
            {"LEFT JOIN res_partner rp ON rp.id = r.partner_id " if group_partner else ''}
            WHERE
                COALESCE(r.total_quantity, 0) <> 0
            
            ORDER BY {"rp.id," if group_partner else ''} pp.id;
        """

        self._cr.execute(query)
        data = self._cr.dictfetchall()
        if issue_date_filter:
            data = [line for line in data if line.get('issue_date') and line['issue_date'] >= issue_date_filter]
        product_obj = self.env['product.product']
        count = 1

        total_quantity = 0
        total_debit_quantity = 0
        total_credit_quantity = 0
        total_t_quantity = 0
        total_value = 0

        p_total_quantity = 0
        p_total_debit_quantity = 0
        p_total_credit_quantity = 0
        p_total_t_quantity = 0
        p_total_value = 0
        last_group_rowx = False

        partner_total = 0
        last_partner_id = False
        for line in data:
            product = product_obj.browse(line.get('p_id'))
            if group_partner:
                if (isinstance(last_partner_id, bool) and not last_partner_id) or (isinstance(last_partner_id, int) and last_partner_id not in [int(line['partner_id']), 0]):
                    if last_group_rowx:
                        sheet.write(last_group_rowx, 6, p_total_quantity, data_right)
                        sheet.write(last_group_rowx, 7, p_total_debit_quantity, data_right)
                        sheet.write(last_group_rowx, 8, p_total_credit_quantity, data_right)
                        sheet.write(last_group_rowx, 9, p_total_value, data_right)
                        sheet.write(last_group_rowx, 10, p_total_t_quantity, data_right)
                    sheet.merge_range(rowx, 0, rowx, 5, line['partner_name'], data_center_bold)
                    last_partner_id = int(line['partner_id'])
                    last_group_rowx = rowx
                    rowx += 1
            colly = 0
            sheet.write(rowx, colly, count, data_left)
            colly += 1
            sheet.write(rowx, colly, line['issue_date'].strftime('%Y-%m-%d') if line.get('issue_date') else '', data_left)
            colly += 1
            sheet.write(rowx, colly, product.default_code, data_left)
            colly += 1
            sheet.write(rowx, colly, product.name, data_left)
            colly += 1
            sheet.write(rowx, colly, product.uom_id.name, data_left)
            colly += 1
            sheet.write(rowx, colly, round(product.standard_price, 2), data_left)
            colly += 1
            sheet.write(rowx, colly, line['quantity'] if not group_partner else line['quantity']*-1, data_right)
            colly += 1
            sheet.write(rowx, colly, line['debit_quantity'] if not group_partner else line['credit_quantity'], data_right)
            colly += 1
            sheet.write(rowx, colly, line['credit_quantity'] if not group_partner else line['debit_quantity'], data_right)
            colly += 1
            sheet.write(rowx, colly, line['total_quantity'] if not group_partner else line['total_quantity']*-1, data_right)
            colly += 1
            value = line['total_quantity']*product.standard_price if not group_partner else (line['total_quantity']*product.standard_price)*-1
            sheet.write(rowx, colly, str(round(value, 2)), data_right)

            count += 1
            rowx += 1
            if group_partner:
                p_total_quantity += line['quantity']
                p_total_debit_quantity += line['debit_quantity']
                p_total_credit_quantity += line['credit_quantity']
                p_total_t_quantity += line['total_quantity']
                p_total_value += value
            total_quantity += line['quantity']
            total_debit_quantity += line['debit_quantity']
            total_credit_quantity += line['credit_quantity']
            total_t_quantity += line['total_quantity']
            total_value += value

        if last_group_rowx:
            sheet.write(last_group_rowx, 6, p_total_quantity if not group_partner else p_total_quantity*-1, data_right)
            sheet.write(last_group_rowx, 7, p_total_debit_quantity if not group_partner else p_total_credit_quantity, data_right)
            sheet.write(last_group_rowx, 8, p_total_credit_quantity if not group_partner else p_total_debit_quantity, data_right)
            sheet.write(last_group_rowx, 9, p_total_t_quantity if not group_partner else p_total_t_quantity*-1, data_right)
            sheet.write(last_group_rowx, 10, p_total_value, data_right)

        rowx += 1
        sheet.merge_range(f'A%s:F%s' % (rowx, rowx), u'Нийт', data_center_bold)
        sheet.write(f'G%s' % rowx, total_quantity if not group_partner else total_quantity*-1, data_right)
        sheet.write(f'H%s' % rowx, total_debit_quantity if not group_partner else total_credit_quantity, data_right)
        sheet.write(f'I%s' % rowx, total_credit_quantity if not group_partner else total_debit_quantity, data_right)
        sheet.write(f'J%s' % rowx, total_t_quantity if not group_partner else total_t_quantity*-1, data_right)
        sheet.write(f'K%s' % rowx, total_value, data_right)


        workbook.close()
        output.seek(0)
        if get_file:
            return output.read()
        response.stream.write(output.read())
        output.close()
        return


