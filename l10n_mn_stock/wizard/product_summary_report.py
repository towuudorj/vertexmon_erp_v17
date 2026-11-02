# -*- coding: utf-8 -*-
import io
import json
from datetime import datetime, time
import xlsxwriter

from odoo import api, fields, models
from odoo.tools import date_utils


class ProductSummaryReport(models.TransientModel):
    """
        Барааны материалын хураангуй тайлан
    """
    _name = "product.summary.report"
    _inherit = 'xls.report.base'
    _description = "Stock summary Report - Mongolia"

    company_id = fields.Many2one('res.company', string=u'Компани', readonly=True,
                                 default=lambda self: self.env.company)
    location_ids = fields.Many2one('stock.location', string=u'Байрлал')
    start_date = fields.Date(string=u'Эхлэх огноо', required=True,
                             default=fields.Date.context_today)
    end_date = fields.Date(string=u'Дуусах огноо', required=True,
                           default=fields.Date.context_today)
    categ_id = fields.Many2one('product.category', string=u'Барааны ангилал')
    product_id = fields.Many2one('product.product', string=u'Бараа')
    brand_id = fields.Many2one('product.brand', string=u'Брэнд')
    is_transaction = fields.Boolean(string='Is transaction')
    warehouse_ids = fields.Many2many('stock.warehouse', 'stock_warehouse_product_summary_rel', 'report_id',
                                     'warehouse_ids', string=u'Агуулах')
    type = fields.Selection([('quantity', u'Тоогоор'),
                             ('cost', u'Өртгөөр')], string=u'Төрөл', required=True)
    dont_show_inventory_count = fields.Boolean(default=False, string=u'Тооллогын хөдөлгөөн харуулахгүй')
    hide_zero_qty = fields.Boolean(string=u'Хөдөлгөөнгүй эхний үлдэгдэл 0 барааг харуулахгүй')

    def get_report_data(self):
        data = super(ProductSummaryReport, self).get_report_data()
        data.update({
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'date_from': self.start_date,
            'date_to': self.end_date,
            'location_ids': self.location_ids.ids if self.location_ids else [],
            'warehouse_ids': self.warehouse_ids.ids,
            'categ_id': self.categ_id.id,
            'product_id': self.product_id.id,
            'brand_id': self.brand_id.id,
            'type': self.type,
            'is_transaction': self.is_transaction,
            'dont_show_inventory_count': self.dont_show_inventory_count,
            'hide_zero_qty': self.hide_zero_qty,
        })
        return data

    def action_print_xls_report(self):
        data = self.get_report_data()
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
            'valign': 'vcenter',
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
        })
        data_center_bold = workbook.add_format({
            'align': 'center',
            'border': 1,
            'font_size': 12,
            'text_wrap': True,
            'bold': True
        })

        sheet.merge_range('A1:D1', u'Байгууллагын нэр: %s' % (data['company_name']), head_title)
        sheet.merge_range('A2:I2', u'Барааны материалын товчоо тайлан', head_title)

        rowx = 4
        sheet.set_paper(9)
        sheet.center_horizontally()
        sheet.fit_to_pages(1, 0.5)
        sheet.set_column(1, 1, 60)
        sheet.set_column(2, 20, 15)

        location_ids = []
        if data.get('location_ids'):
            location_ids = self.env['stock.location'].search([('id', 'child_of', data['location_ids'])]).ids
        else:
            warehouse_ids = data.get('warehouse_ids') or []
            if isinstance(warehouse_ids, (list, tuple)) and warehouse_ids:
                warehouses = self.env['stock.warehouse'].browse(warehouse_ids)
            else:
                warehouses = self.env['stock.warehouse'].search([('company_id', '=', data['company_id'])])
            if warehouses:
                locations = self.env['stock.location'].search([
                    ('warehouse_id', 'in', warehouses.ids)
                ])
                location_ids = locations.ids

        product_obj = self.env['product.product']
        domain = [('detailed_type', '=', 'product')]
        if data.get('product_id'):
            domain.append(('id', '=', data['product_id']))
        if data.get('categ_id'):
            domain.append(('categ_id', '=', data['categ_id']))
        if data.get('is_transaction'):
            domain.append(
                ('id', 'in', self.env['stock.move'].search([
                    ('state', '=', 'done'),
                    ('company_id', '=', data['company_id']),
                    '|',
                    ('location_id', 'in', tuple(location_ids)),
                    ('location_dest_id', 'in', tuple(location_ids))
                ]).mapped('product_id').ids)
            )
        if data.get('brand_id'):
            domain.append(('brand_id', '=', data['brand_id']))
        product_ids = product_obj.sudo().search(domain)

        date_from = data['date_from']
        if isinstance(date_from, str):
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        date_from_dt_min = datetime.combine(date_from, time.min)

        date_to = data['date_to']
        if isinstance(date_to, str):
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        date_to_dt_max = datetime.combine(date_to, time.max)

        # Batch loading for performance & consistency
        f_income_dict = {}
        f_expense_dict = {}
        income_dict = {}
        expense_dict = {}
        svl_beg_dict = {}
        svl_end_dict = {}
        svl_in_dict = {}

        if product_ids:
            product_pids = tuple(product_ids.ids)
            prod_cond = f"AND mv.product_id IN {product_pids}" if len(product_pids) > 1 else f"AND mv.product_id = {product_pids[0]}"
            loc_dest_cond = f"AND dest.id IN {tuple(location_ids)}" if len(location_ids) > 1 else (f"AND dest.id = {location_ids[0]}" if location_ids else "")
            loc_src_cond = f"AND sl.id IN {tuple(location_ids)}" if len(location_ids) > 1 else (f"AND sl.id = {location_ids[0]}" if location_ids else "")
            inv_count_cond = "AND mv.picking_id IS NOT NULL" if data.get('dont_show_inventory_count') else ""
            sm_inv_count_cond = "AND sm.picking_id IS NOT NULL" if data.get('dont_show_inventory_count') else ""

            # 1. Beginning Move Lines (date < date_from)
            self._cr.execute(f'''
                SELECT mv.product_id, SUM(mv.quantity) AS qty
                FROM stock_move_line mv
                JOIN stock_location sl ON mv.location_id = sl.id
                JOIN stock_location dest ON mv.location_dest_id = dest.id
                WHERE mv.state = 'done'
                  AND mv.date < %s
                  AND mv.company_id = %s
                  {prod_cond}
                  AND sl.usage NOT IN ('internal', 'transit')
                  AND dest.usage IN ('internal', 'transit')
                  {loc_dest_cond}
                  {inv_count_cond}
                GROUP BY mv.product_id
            ''', (date_from_dt_min, data['company_id']))
            f_income_dict = dict(self._cr.fetchall())

            self._cr.execute(f'''
                SELECT mv.product_id, SUM(mv.quantity) AS qty
                FROM stock_move_line mv
                JOIN stock_location sl ON mv.location_id = sl.id
                JOIN stock_location dest ON mv.location_dest_id = dest.id
                WHERE mv.state = 'done'
                  AND mv.date < %s
                  AND mv.company_id = %s
                  {prod_cond}
                  AND sl.usage IN ('internal', 'transit')
                  AND dest.usage NOT IN ('internal', 'transit')
                  {loc_src_cond}
                  {inv_count_cond}
                GROUP BY mv.product_id
            ''', (date_from_dt_min, data['company_id']))
            f_expense_dict = dict(self._cr.fetchall())

            # 2. Period Move Lines (date_from <= date <= date_to)
            self._cr.execute(f'''
                SELECT mv.product_id, SUM(mv.quantity) AS qty
                FROM stock_move_line mv
                JOIN stock_location sl ON mv.location_id = sl.id
                JOIN stock_location dest ON mv.location_dest_id = dest.id
                WHERE mv.state = 'done'
                  AND mv.date >= %s AND mv.date <= %s
                  AND mv.company_id = %s
                  {prod_cond}
                  AND sl.usage NOT IN ('internal', 'transit')
                  AND dest.usage IN ('internal', 'transit')
                  {loc_dest_cond}
                  {inv_count_cond}
                GROUP BY mv.product_id
            ''', (date_from_dt_min, date_to_dt_max, data['company_id']))
            income_dict = dict(self._cr.fetchall())

            self._cr.execute(f'''
                SELECT mv.product_id, SUM(mv.quantity) AS qty
                FROM stock_move_line mv
                JOIN stock_location sl ON mv.location_id = sl.id
                JOIN stock_location dest ON mv.location_dest_id = dest.id
                WHERE mv.state = 'done'
                  AND mv.date >= %s AND mv.date <= %s
                  AND mv.company_id = %s
                  {prod_cond}
                  AND sl.usage IN ('internal', 'transit')
                  AND dest.usage NOT IN ('internal', 'transit')
                  {loc_src_cond}
                  {inv_count_cond}
                GROUP BY mv.product_id
            ''', (date_from_dt_min, date_to_dt_max, data['company_id']))
            expense_dict = dict(self._cr.fetchall())

            # 3. Beginning SVL values (date < date_from) for cost mode
            if data['type'] == 'cost':
                svl_prod_cond = f"AND svl.product_id IN {product_pids}" if len(product_pids) > 1 else f"AND svl.product_id = {product_pids[0]}"
                self._cr.execute(f'''
                    SELECT svl.product_id, SUM(svl.value), SUM(svl.quantity)
                    FROM stock_valuation_layer svl
                    LEFT JOIN stock_move sm ON svl.stock_move_id = sm.id
                    WHERE svl.company_id = %s
                      {svl_prod_cond}
                      AND COALESCE(sm.date, svl.create_date) < %s
                    GROUP BY svl.product_id
                ''', (data['company_id'], date_from_dt_min))
                svl_beg_dict = {r[0]: (float(r[1] or 0), float(r[2] or 0)) for r in self._cr.fetchall()}

                # Ending SVL values (date <= date_to) for cost mode (ending balance depends ONLY on date_to)
                self._cr.execute(f'''
                    SELECT svl.product_id, SUM(svl.value), SUM(svl.quantity)
                    FROM stock_valuation_layer svl
                    LEFT JOIN stock_move sm ON svl.stock_move_id = sm.id
                    WHERE svl.company_id = %s
                      {svl_prod_cond}
                      AND COALESCE(sm.date, svl.create_date) <= %s
                    GROUP BY svl.product_id
                ''', (data['company_id'], date_to_dt_max))
                svl_end_dict = {r[0]: (float(r[1] or 0), float(r[2] or 0)) for r in self._cr.fetchall()}

                # 4. Period incoming SVL values (date_from <= date <= date_to)
                sm_prod_cond = f"AND sm.product_id IN {product_pids}" if len(product_pids) > 1 else f"AND sm.product_id = {product_pids[0]}"
                self._cr.execute(f'''
                    SELECT sm.product_id, SUM(svl.value)
                    FROM stock_valuation_layer svl
                    JOIN stock_move sm ON svl.stock_move_id = sm.id
                    JOIN stock_location sl ON sm.location_id = sl.id
                    JOIN stock_location dest ON sm.location_dest_id = dest.id
                    WHERE sm.state = 'done'
                      AND svl.company_id = %s
                      {sm_prod_cond}
                      AND sm.date >= %s AND sm.date <= %s
                      AND sl.usage NOT IN ('internal', 'transit')
                      AND dest.usage IN ('internal', 'transit')
                      {loc_dest_cond}
                      {sm_inv_count_cond}
                    GROUP BY sm.product_id
                ''', (data['company_id'], date_from_dt_min, date_to_dt_max))
                svl_in_dict = dict(self._cr.fetchall())

        if data['type'] == 'cost':
            sheet.merge_range('J3:M3', u'Тайлант хугацаа: %s - %s' % (data['date_from'], data['date_to']), head_title)
            sheet.merge_range('A%s:A%s' % (rowx, rowx + 1), u'Д/д', data_center_bold)
            sheet.merge_range('B%s:B%s' % (rowx, rowx + 1), u'Барааны нэр', data_center_bold)
            sheet.merge_range('C%s:C%s' % (rowx, rowx + 1), u'Барааны код', data_center_bold)
            sheet.merge_range('D%s:D%s' % (rowx, rowx + 1), u'Дотоод код', data_center_bold)
            sheet.merge_range('E%s:E%s' % (rowx, rowx + 1), u'Барааны хэмжих нэгж', data_center_bold)
            sheet.merge_range('F%s:G%s' % (rowx, rowx), u'Барааны эхний үлдэгдэл', data_center_bold)
            sheet.write('F%s' % (rowx + 1), u'Тоо', data_center_bold)
            sheet.write('G%s' % (rowx + 1), u'Нийт өртөг', data_center_bold)
            sheet.merge_range('H%s:I%s' % (rowx, rowx), u'Барааны орлого', data_center_bold)
            sheet.write('H%s' % (rowx + 1), u'Тоо', data_center_bold)
            sheet.write('I%s' % (rowx + 1), u'Нийт өртөг', data_center_bold)
            sheet.merge_range('J%s:K%s' % (rowx, rowx), u'Барааны зарлага', data_center_bold)
            sheet.write('J%s' % (rowx + 1), u'Тоо', data_center_bold)
            sheet.write('K%s' % (rowx + 1), u'Нийт өртөг', data_center_bold)
            sheet.merge_range('L%s:M%s' % (rowx, rowx), u'Барааны эцсийн үлдэгдэл', data_center_bold)
            sheet.write('L%s' % (rowx + 1), u'Тоо', data_center_bold)
            sheet.write('M%s' % (rowx + 1), u'Нийт өртөг', data_center_bold)

            count = 1
            rowx += 2

            total_f_bal_qty = 0.0
            total_f_bal_price = 0.0
            total_in_qty = 0.0
            total_in_price = 0.0
            total_ex_qty = 0.0
            total_ex_price = 0.0
            total_last_qty = 0.0
            total_last_price = 0.0

            cost_dict = {p.id: (float(p.avg_cost or 0.0), float(p.standard_price or 0.0)) for p in product_ids}

            for pro in product_ids:
                f_in_qty = f_income_dict.get(pro.id, 0.0)
                f_ex_qty = f_expense_dict.get(pro.id, 0.0)
                in_qty = income_dict.get(pro.id, 0.0)
                ex_qty = expense_dict.get(pro.id, 0.0)

                f_bal_qty = f_in_qty - f_ex_qty
                last_qty = f_bal_qty + in_qty - ex_qty

                avg_c, std_c = cost_dict.get(pro.id, (0.0, 0.0))
                fallback_cost = avg_c or std_c or 0.0

                end_val, end_svl_qty = svl_end_dict.get(pro.id, (0.0, 0.0))
                if last_qty <= 0.0:
                    last_price = 0.0
                else:
                    if end_svl_qty > 0.0 and end_val > 0.0:
                        end_unit_cost = end_val / end_svl_qty
                        last_price = round(last_qty * end_unit_cost, 2)
                    else:
                        last_price = round(last_qty * fallback_cost, 2)

                beg_val, beg_svl_qty = svl_beg_dict.get(pro.id, (0.0, 0.0))
                if f_bal_qty <= 0.0:
                    f_bal_price = 0.0
                else:
                    if beg_svl_qty > 0.0 and beg_val > 0.0:
                        beg_unit_cost = beg_val / beg_svl_qty
                        f_bal_price = round(f_bal_qty * beg_unit_cost, 2)
                    else:
                        f_bal_price = round(f_bal_qty * fallback_cost, 2)

                if in_qty <= 0.0 and ex_qty <= 0.0:
                    in_price = 0.0
                    ex_price = 0.0
                    f_bal_price = last_price
                elif ex_qty <= 0.0 and in_qty > 0.0:
                    ex_price = 0.0
                    in_price = round(last_price - f_bal_price, 2)
                    if in_price < 0.0:
                        svl_in = round(float(svl_in_dict.get(pro.id, 0.0)), 2)
                        in_price = svl_in if svl_in > 0.0 else round(in_qty * fallback_cost, 2)
                        f_bal_price = round(last_price - in_price, 2)
                elif in_qty <= 0.0 and ex_qty > 0.0:
                    in_price = 0.0
                    ex_price = round(f_bal_price - last_price, 2)
                    if ex_price < 0.0:
                        ex_price = round(ex_qty * fallback_cost, 2)
                        f_bal_price = round(last_price + ex_price, 2)
                else:
                    svl_in = round(float(svl_in_dict.get(pro.id, 0.0)), 2)
                    if svl_in > 0.0:
                        in_price = svl_in
                    else:
                        if end_svl_qty > 0.0 and end_val > 0.0:
                            in_price = round(in_qty * (end_val / end_svl_qty), 2)
                        else:
                            in_price = round(in_qty * fallback_cost, 2)

                    ex_price = round(f_bal_price + in_price - last_price, 2)
                    if ex_price < 0.0:
                        in_price = round(in_price + abs(ex_price), 2)
                        ex_price = 0.0

                if data.get('hide_zero_qty') and f_bal_qty == 0.0 and in_qty == 0.0 and ex_qty == 0.0:
                    continue

                sheet.write(f'A%s' % rowx, count, data_left)
                sheet.write(f'B%s' % rowx, u'%s' % pro.name, data_left)
                sheet.write(f'C%s' % rowx, u'%s' % (pro.barcode or ''), data_left)
                sheet.write(f'D%s' % rowx, u'%s' % (pro.default_code or ''), data_left)
                sheet.write(f'E%s' % rowx, u'%s' % (pro.uom_id.name or ''), data_left)
                sheet.write(f'F%s' % rowx, f_bal_qty, data_right)
                sheet.write(f'G%s' % rowx, f_bal_price, data_right)
                sheet.write(f'H%s' % rowx, in_qty, data_right)
                sheet.write(f'I%s' % rowx, in_price, data_right)
                sheet.write(f'J%s' % rowx, ex_qty, data_right)
                sheet.write(f'K%s' % rowx, ex_price, data_right)
                sheet.write(f'L%s' % rowx, last_qty, data_right)
                sheet.write(f'M%s' % rowx, last_price, data_right)

                count += 1
                rowx += 1

                total_f_bal_qty += f_bal_qty
                total_f_bal_price += f_bal_price
                total_in_qty += in_qty
                total_in_price += in_price
                total_ex_qty += ex_qty
                total_ex_price += ex_price
                total_last_qty += last_qty
                total_last_price += last_price

            sheet.merge_range(f'A%s:E%s' % (rowx, rowx), u'Нийт', data_center_bold)
            sheet.write(f'F%s' % rowx, total_f_bal_qty, data_right)
            sheet.write(f'G%s' % rowx, total_f_bal_price, data_right)
            sheet.write(f'H%s' % rowx, total_in_qty, data_right)
            sheet.write(f'I%s' % rowx, total_in_price, data_right)
            sheet.write(f'J%s' % rowx, total_ex_qty, data_right)
            sheet.write(f'K%s' % rowx, total_ex_price, data_right)
            sheet.write(f'L%s' % rowx, total_last_qty, data_right)
            sheet.write(f'M%s' % rowx, total_last_price, data_right)

        else:
            rowx = 5

            sheet.merge_range(
                'F3:I3',
                u'Тайлант хугацаа: %s - %s' % (data.get('date_from'), data.get('date_to')),
                head_title
            )

            sheet.merge_range(f'A{rowx}:A{rowx + 1}', u'Д/д', data_center_bold)
            sheet.merge_range(f'B{rowx}:B{rowx + 1}', u'Барааны нэр', data_center_bold)
            sheet.merge_range(f'C{rowx}:C{rowx + 1}', u'Барааны код', data_center_bold)
            sheet.merge_range(f'D{rowx}:D{rowx + 1}', u'Дотоод код', data_center_bold)
            sheet.merge_range(f'E{rowx}:E{rowx + 1}', u'Хэмжих нэгж', data_center_bold)
            sheet.merge_range(f'F{rowx}:F{rowx + 1}', u'Эхний үлдэгдэл', data_center_bold)
            sheet.merge_range(f'G{rowx}:G{rowx + 1}', u'Орлого', data_center_bold)
            sheet.merge_range(f'H{rowx}:H{rowx + 1}', u'Зарлага', data_center_bold)
            sheet.merge_range(f'I{rowx}:I{rowx + 1}', u'Эцсийн үлдэгдэл', data_center_bold)

            count = 1
            rowx += 2

            total_f_bal_qty = 0.0
            total_in_qty = 0.0
            total_ex_qty = 0.0
            total_last_qty = 0.0

            for pro in product_ids:
                f_in_qty = f_income_dict.get(pro.id, 0.0)
                f_ex_qty = f_expense_dict.get(pro.id, 0.0)
                in_qty = income_dict.get(pro.id, 0.0)
                ex_qty = expense_dict.get(pro.id, 0.0)

                f_bal_qty = f_in_qty - f_ex_qty
                last_qty = f_bal_qty + in_qty - ex_qty

                if data.get('hide_zero_qty') and f_bal_qty == 0.0 and in_qty == 0.0 and ex_qty == 0.0:
                    continue

                sheet.write(f'A%s' % rowx, count, data_left)
                sheet.write(f'B%s' % rowx, u'%s' % pro.name, data_left)
                sheet.write(f'C%s' % rowx, u'%s' % (pro.barcode or ''), data_left)
                sheet.write(f'D%s' % rowx, u'%s' % (pro.default_code or ''), data_left)
                sheet.write(f'E%s' % rowx, u'%s' % (pro.uom_id.name or ''), data_left)
                sheet.write(f'F%s' % rowx, f_bal_qty, data_right)
                sheet.write(f'G%s' % rowx, in_qty, data_right)
                sheet.write(f'H%s' % rowx, ex_qty, data_right)
                sheet.write(f'I%s' % rowx, last_qty, data_right)

                count += 1
                rowx += 1
                total_f_bal_qty += f_bal_qty
                total_in_qty += in_qty
                total_ex_qty += ex_qty
                total_last_qty += last_qty

            sheet.merge_range(f'A%s:E%s' % (rowx, rowx), u'Нийт', data_center_bold)
            sheet.write(f'F%s' % rowx, total_f_bal_qty, data_right)
            sheet.write(f'G%s' % rowx, total_in_qty, data_right)
            sheet.write(f'H%s' % rowx, total_ex_qty, data_right)
            sheet.write(f'I%s' % rowx, total_last_qty, data_right)

        workbook.close()
        output.seek(0)
        if get_file:
            return output.read()
        response.stream.write(output.read())
        output.close()
        return
