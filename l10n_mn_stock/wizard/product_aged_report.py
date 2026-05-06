# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools import date_utils
import io
import json
import xlsxwriter


class ProductAgedReport(models.TransientModel):
    _name = "product.aged.report"
    _description = "Product aged Report - Mongolia"

    company_id = fields.Many2one(
        'res.company',
        string='Компани',
        readonly=True,
        default=lambda self: self.env.user.company_id
    )
    start_date = fields.Date(
        string='Эхлэх огноо',
        required=True,
        default=fields.Date.context_today
    )
    end_date = fields.Date(
        string='Дуусах огноо',
        required=True,
        default=fields.Date.context_today
    )
    categ_id = fields.Many2one('product.category', string='Барааны ангилал')
    product_id = fields.Many2one('product.product', string='Бараа')
    warehouse_ids = fields.Many2many(
        'stock.warehouse',
        'product_aged_warehouse_product_rel',
        'report_id',
        'warehouse_ids',
        string='Агуулах'
    )

    # ---------------------------------------------------------
    # ACTION
    # ---------------------------------------------------------
    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'warehouse_ids': self.warehouse_ids.ids,
            'categ_id': self.categ_id.id if self.categ_id else False,
            'product_id': self.product_id.id if self.product_id else False,
        }

        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {
                'model': 'product.aged.report',
                'output_format': 'xlsx',
                'options': json.dumps(data, default=date_utils.json_default),
                'report_name': 'product_aged_report'
            }
        }

    # ---------------------------------------------------------
    # REPORT
    # ---------------------------------------------------------
    def get_xlsx_report(self, data, response):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()

        # ── Formats ──────────────────────────────────────────
        title_fmt = workbook.add_format({
            'align': 'center', 'bold': True, 'font_size': 14,
            'font_name': 'Arial',
        })
        header_fmt = workbook.add_format({
            'align': 'center', 'bold': True, 'border': 1,
            'bg_color': '#D9E1F2', 'font_name': 'Arial', 'font_size': 10,
        })
        text_fmt = workbook.add_format({
            'border': 1, 'font_name': 'Arial', 'font_size': 10,
        })
        number_fmt = workbook.add_format({
            'border': 1, 'num_format': '#,##0.00',
            'font_name': 'Arial', 'font_size': 10,
        })
        int_fmt = workbook.add_format({
            'border': 1, 'num_format': '#,##0',
            'font_name': 'Arial', 'font_size': 10,
        })
        meta_fmt = workbook.add_format({
            'border': 1, 'font_name': 'Arial', 'font_size': 10,
        })

        # ── Column widths ─────────────────────────────────────
        col_widths = [5, 30, 15, 20, 14, 14, 12, 12, 14, 12, 14, 16, 12]
        for col, w in enumerate(col_widths):
            sheet.set_column(col, col, w)

        # ── Header rows ───────────────────────────────────────
        sheet.merge_range('A1:D1', f"Байгууллага: {data['company_name']}", meta_fmt)
        sheet.merge_range('A2:M2', "Барааны насжилтын тайлан", title_fmt)
        sheet.merge_range(
            'K3:M3',
            f"{data['start_date']} - {data['end_date']}",
            meta_fmt
        )

        headers = [
            "№", "Бараа", "Код", "Агуулах",
            "Орлого огноо", "Зарлага огноо",
            "Орлого Qty", "Зарлага Qty",
            "Дундаж хоног", "Үлдэгдэл",
            "Үнэ", "Нийт үнэ", "Ангилал"
        ]
        for col, h in enumerate(headers):
            sheet.write(3, col, h, header_fmt)

        # ---------------------------------------------------------
        # BUILD QUERY
        # ---------------------------------------------------------
        query = """
            SELECT
                COALESCE(
                    pt.name->>'mn_MN',
                    pt.name->>'en_US',
                    pt.name->>'en_GB',
                    pt.name::text
                ) AS name,
                pt.default_code,
                COALESCE(sw.name, 'N/A') AS warehouse,

                -- First receipt date (filtered range)
                MIN(CASE WHEN svl.quantity > 0 THEN svl.create_date::date END) AS first_in,

                -- Last issue date — from stock_move.date within the same filtered range
                MAX(
                    CASE WHEN svl.quantity < 0
                         AND sm.date::date BETWEEN %(start_date)s AND %(end_date)s
                    THEN sm.date::date END
                ) AS last_out,

                -- Total in / out across the period
                SUM(CASE WHEN svl.quantity > 0 THEN svl.quantity  ELSE 0 END) AS qty_in,
                SUM(CASE WHEN svl.quantity < 0 THEN -svl.quantity ELSE 0 END) AS qty_out,

                -- Remaining stock (open layers)
                SUM(CASE WHEN svl.remaining_qty > 0 THEN svl.remaining_qty ELSE 0 END) AS balance_qty,

                -- Weighted-average age in days for remaining stock only
                CASE
                    WHEN SUM(CASE WHEN svl.remaining_qty > 0 THEN svl.remaining_qty ELSE 0 END) > 0
                    THEN SUM(
                             (CURRENT_DATE - svl.create_date::date)
                             * CASE WHEN svl.remaining_qty > 0 THEN svl.remaining_qty ELSE 0 END
                         )
                         /
                         SUM(CASE WHEN svl.remaining_qty > 0 THEN svl.remaining_qty ELSE 0 END)
                    ELSE 0
                END AS avg_age,

                AVG(svl.unit_cost) AS unit_cost

            FROM stock_valuation_layer svl

            JOIN product_product pp        ON pp.id  = svl.product_id
            JOIN product_template pt       ON pt.id  = pp.product_tmpl_id

            LEFT JOIN stock_move sm              ON sm.id  = svl.stock_move_id
            LEFT JOIN stock_picking_type spt     ON spt.id = sm.picking_type_id
            LEFT JOIN stock_warehouse sw         ON sw.id  = spt.warehouse_id

            WHERE svl.company_id = %(company_id)s
              AND svl.create_date >= %(start_date)s
              AND svl.create_date  < %(end_date)s::date + INTERVAL '1 day'
        """

        params = {
            'company_id': data['company_id'],
            'start_date': data['start_date'],
            'end_date':   data['end_date'],
        }

        # ── Optional filters ──────────────────────────────────
        if data.get('warehouse_ids'):
            wh_ids = tuple(data['warehouse_ids'])
            # Ensure tuple has at least 2 elements for valid SQL IN syntax
            if len(wh_ids) == 1:
                wh_ids = (wh_ids[0], wh_ids[0])
            query += " AND sw.id IN %(warehouse_ids)s"
            params['warehouse_ids'] = wh_ids

        if data.get('product_id'):
            query += " AND pp.id = %(product_id)s"
            params['product_id'] = data['product_id']
        elif data.get('categ_id'):
            # Include the selected category AND all its descendants
            root_categ = self.env['product.category'].browse(data['categ_id'])
            child_ids = self.env['product.category'].search(
                [('id', 'child_of', root_categ.id)]
            ).ids
            if len(child_ids) == 1:
                child_ids = child_ids * 2  # duplicate for valid IN tuple
            query += " AND pt.categ_id IN %(categ_ids)s"
            params['categ_ids'] = tuple(child_ids)

        query += """
            GROUP BY pt.name, pt.default_code, sw.name
            ORDER BY pt.name
        """

        self.env.cr.execute(query, params)
        results = self.env.cr.dictfetchall()

        # ---------------------------------------------------------
        # WRITE ROWS
        # ---------------------------------------------------------
        row = 4
        for i, r in enumerate(results, start=1):
            balance = r['balance_qty'] or 0
            cost    = r['unit_cost']   or 0
            total   = balance * cost
            age     = int(r['avg_age'] or 0)

            if age <= 30:
                bucket = "0–30"
            elif age <= 60:
                bucket = "31–60"
            elif age <= 90:
                bucket = "61–90"
            else:
                bucket = "90+"

            first_in  = str(r['first_in'])  if r['first_in']  else ''
            last_out  = str(r['last_out'])  if r['last_out']  else ''

            # Text columns
            sheet.write(row, 0,  i,                    int_fmt)
            sheet.write(row, 1,  r['name'] or '',      text_fmt)
            sheet.write(row, 2,  r['default_code'] or '', text_fmt)
            sheet.write(row, 3,  r['warehouse'] or '', text_fmt)
            sheet.write(row, 4,  first_in,             text_fmt)
            sheet.write(row, 5,  last_out,             text_fmt)

            # Numeric columns
            sheet.write(row, 6,  r['qty_in']  or 0,   number_fmt)
            sheet.write(row, 7,  r['qty_out'] or 0,   number_fmt)
            sheet.write(row, 8,  age,                  int_fmt)
            sheet.write(row, 9,  balance,              number_fmt)
            sheet.write(row, 10, cost,                 number_fmt)
            sheet.write(row, 11, total,                number_fmt)

            # Bucket / category
            sheet.write(row, 12, bucket,               text_fmt)

            row += 1

        # ── Totals row ────────────────────────────────────────
        if results:
            total_row_fmt = workbook.add_format({
                'bold': True, 'border': 1,
                'num_format': '#,##0.00', 'font_name': 'Arial',
            })
            total_label_fmt = workbook.add_format({
                'bold': True, 'border': 1, 'font_name': 'Arial',
            })
            data_start = 5   # Excel row index of first data row (0-based → row 5 = row 4+1)
            data_end   = row  # exclusive

            sheet.write(row, 0, 'Нийт', total_label_fmt)
            sheet.write(row, 1, '', total_label_fmt)
            sheet.write(row, 2, '', total_label_fmt)
            sheet.write(row, 3, '', total_label_fmt)
            sheet.write(row, 4, '', total_label_fmt)
            sheet.write(row, 5, '', total_label_fmt)
            sheet.write(row, 6,  f'=SUM(G5:G{data_end})', total_row_fmt)
            sheet.write(row, 7,  f'=SUM(H5:H{data_end})', total_row_fmt)
            sheet.write(row, 8,  '',                       total_label_fmt)
            sheet.write(row, 9,  f'=SUM(J5:J{data_end})', total_row_fmt)
            sheet.write(row, 10, '',                       total_label_fmt)
            sheet.write(row, 11, f'=SUM(L5:L{data_end})', total_row_fmt)
            sheet.write(row, 12, '',                       total_label_fmt)

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()