# -*- coding: utf-8 -*-
import io
import json
from datetime import datetime, time
import pytz
import xlsxwriter

from odoo import api, fields, models
from odoo.tools import date_utils


class PurchaseOrderReport(models.TransientModel):
    """
        Худалдан авалтын захиалгын тайлан
    """
    _name = "purchase.order.report"
    _inherit = 'xls.report.base'
    _description = "Худалдан авалтын захиалгын тайлан"

    company_id = fields.Many2one(
        'res.company', string='Компани', required=True,
        default=lambda self: self.env.company
    )
    date_from = fields.Date(
        string='Эхлэх огноо', required=True,
        default=fields.Date.context_today
    )
    date_to = fields.Date(
        string='Дуусах огноо', required=True,
        default=fields.Date.context_today
    )
    date_type = fields.Selection([
        ('order', 'Захиалгын огноо'),
        ('approve', 'Батлагдсан огноо')
    ], string='Шүүх огноо', default='order', required=True)

    purchase_type = fields.Selection([
        ('all', 'Бүгд'),
        ('local', 'Дотоод'),
        ('foreign', 'Гадаад')
    ], string='Худалдан авалтын төрөл', default='all', required=True)

    receipt_status = fields.Selection([
        ('all', 'Бүгд'),
        ('full', 'Хүргэгдсэн (Бүрэн авсан)'),
        ('partial', 'Хэсэгчлэн хүлээн авсан'),
        ('pending', 'Хүргэгдээгүй (Хүлээгдэж буй)')
    ], string='Хүргэгдсэн эсэх', default='all', required=True)

    partner_id = fields.Many2one('res.partner', string='Нийлүүлэгч / Харилцагч')
    sales_partner_id = fields.Many2one('res.partner', string='Эцсийн хэрэглэгч')
    product_id = fields.Many2one('product.product', string='Бараа')
    category_id = fields.Many2one('product.category', string='Барааны ангилал')
    user_id = fields.Many2one('res.users', string='Худалдан авалтын ажилтан')

    state = fields.Selection([
        ('all', 'Бүгд (Цуцалснаас бусад)'),
        ('purchase', 'Батлагдсан'),
        ('done', 'Түгжигдсэн/Дууссан'),
        ('draft', 'Ноорог')
    ], string='Захиалгын төлөв', default='all', required=True)

    def get_report_data(self):
        data = super(PurchaseOrderReport, self).get_report_data()
        data.update({
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'date_from': str(self.date_from),
            'date_to': str(self.date_to),
            'date_type': self.date_type,
            'purchase_type': self.purchase_type,
            'receipt_status': self.receipt_status,
            'partner_id': self.partner_id.id if self.partner_id else False,
            'partner_name': self.partner_id.name if self.partner_id else False,
            'sales_partner_id': self.sales_partner_id.id if self.sales_partner_id else False,
            'sales_partner_name': self.sales_partner_id.name if self.sales_partner_id else False,
            'product_id': self.product_id.id if self.product_id else False,
            'product_name': self.product_id.display_name if self.product_id else False,
            'category_id': self.category_id.id if self.category_id else False,
            'category_name': self.category_id.name if self.category_id else False,
            'user_id': self.user_id.id if self.user_id else False,
            'state': self.state,
        })
        return data

    def action_print_xls_report(self):
        data = self.get_report_data()
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {
                'model': 'purchase.order.report',
                'output_format': 'xlsx',
                'options': json.dumps(data, default=date_utils.json_default),
                'report_name': 'Худалдан авалтын захиалгын тайлан'
            }
        }

    def get_xlsx_report(self, data, response, get_file=False):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Захиалгын тайлан')

        sheet.set_landscape()
        sheet.set_paper(9)  # A4
        sheet.center_horizontally()
        sheet.fit_to_pages(1, 0)

        # Formats
        title_fmt = workbook.add_format({
            'font_name': 'Times New Roman',
            'font_size': 14,
            'bold': True,
            'align': 'center',
            'valign': 'vcenter'
        })
        sub_fmt = workbook.add_format({
            'font_name': 'Times New Roman',
            'font_size': 10,
            'align': 'left',
            'valign': 'vcenter'
        })
        hdr_fmt = workbook.add_format({
            'font_name': 'Times New Roman',
            'font_size': 9,
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'bg_color': '#D9E1F2',
            'text_wrap': True
        })
        cell_left = workbook.add_format({
            'font_name': 'Times New Roman',
            'font_size': 9,
            'align': 'left',
            'valign': 'vcenter',
            'border': 1,
            'text_wrap': True
        })
        cell_center = workbook.add_format({
            'font_name': 'Times New Roman',
            'font_size': 9,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        cell_right = workbook.add_format({
            'font_name': 'Times New Roman',
            'font_size': 9,
            'align': 'right',
            'valign': 'vcenter',
            'border': 1,
            'num_format': '#,##0.00'
        })
        tot_fmt = workbook.add_format({
            'font_name': 'Times New Roman',
            'font_size': 9,
            'bold': True,
            'align': 'right',
            'valign': 'vcenter',
            'border': 1,
            'bg_color': '#E2EFDA',
            'num_format': '#,##0.00'
        })
        tot_lbl = workbook.add_format({
            'font_name': 'Times New Roman',
            'font_size': 9,
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'bg_color': '#E2EFDA'
        })

        # Set column widths (20 columns: A to T)
        widths = [5, 12, 11, 9, 25, 25, 13, 30, 16, 7, 11, 11, 14, 6, 11, 13, 8, 14, 11, 14]
        for col_idx, w in enumerate(widths):
            sheet.set_column(col_idx, col_idx, w)

        # Build Domain
        user_tz = pytz.timezone(self._context.get('tz') or self.env.user.tz or 'Asia/Ulaanbaatar')
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        if isinstance(date_from, str):
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        if isinstance(date_to, str):
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()

        date_field = 'date_order' if data.get('date_type', 'order') == 'order' else 'date_approve'
        start_dt = user_tz.localize(datetime.combine(date_from, time.min)).astimezone(pytz.utc).replace(tzinfo=None)
        end_dt = user_tz.localize(datetime.combine(date_to, time.max)).astimezone(pytz.utc).replace(tzinfo=None)

        domain = [
            ('company_id', '=', data['company_id']),
            ('display_type', '=', False),
            (f'order_id.{date_field}', '>=', start_dt),
            (f'order_id.{date_field}', '<=', end_dt),
        ]

        # State filter
        st = data.get('state', 'all')
        if st == 'all':
            domain.append(('order_id.state', '!=', 'cancel'))
        else:
            domain.append(('order_id.state', '=', st))

        # Purchase type filter
        ptype = data.get('purchase_type', 'all')
        if ptype and ptype != 'all':
            domain.append(('order_id.purchase_type', '=', ptype))

        # Receipt status filter
        rstat = data.get('receipt_status', 'all')
        if rstat and rstat != 'all':
            if rstat == 'pending':
                domain.append(('order_id.receipt_status', 'in', ['pending', False]))
            else:
                domain.append(('order_id.receipt_status', '=', rstat))

        # Partner filter
        if data.get('partner_id'):
            domain.append(('order_id.partner_id', '=', data['partner_id']))

        # End User filter
        if data.get('sales_partner_id'):
            domain.append(('order_id.sales_partner_id', '=', data['sales_partner_id']))

        # Product filter
        if data.get('product_id'):
            domain.append(('product_id', '=', data['product_id']))

        # Category filter
        if data.get('category_id'):
            domain.append(('product_id.categ_id', 'child_of', data['category_id']))

        # User filter
        if data.get('user_id'):
            domain.append(('order_id.user_id', '=', data['user_id']))

        lines = self.env['purchase.order.line'].search(domain)
        # Sort in python
        lines = sorted(
            lines,
            key=lambda l: (
                l.order_id[date_field] or datetime.min,
                l.order_id.name or '',
                l.sequence or 0
            ),
            reverse=True
        )

        # Header Titles
        type_labels = {'all': 'Бүгд', 'local': 'Дотоод', 'foreign': 'Гадаад'}
        receipt_labels = {
            'all': 'Бүгд',
            'full': 'Хүргэгдсэн',
            'partial': 'Хэсэгчлэн',
            'pending': 'Хүргэгдээгүй'
        }

        sheet.merge_range('A1:T1', 'ХУДАЛДАН АВАЛТЫН ЗАХИАЛГЫН ТАЙЛАН', title_fmt)
        sheet.set_row(0, 24)

        sheet.write('A2', f"Компани: {data.get('company_name', '')}", sub_fmt)
        sub_info = (
            f"Хугацаа: {data.get('date_from')} - {data.get('date_to')} | "
            f"Төрөл: {type_labels.get(ptype, ptype)} | "
            f"Хүргэлт: {receipt_labels.get(rstat, rstat)}"
        )
        if data.get('partner_name'):
            sub_info += f" | Нийлүүлэгч: {data['partner_name']}"
        if data.get('sales_partner_name'):
            sub_info += f" | Эцсийн хэрэглэгч: {data['sales_partner_name']}"
        if data.get('product_name'):
            sub_info += f" | Бараа: {data['product_name']}"
        if data.get('category_name'):
            sub_info += f" | Ангилал: {data['category_name']}"
        sheet.write('A3', sub_info, sub_fmt)

        headers = [
            'Д/д', 'Захиалгын №', 'Огноо', 'Төрөл', 'Нийлүүлэгч / Харилцагч',
            'Эцсийн хэрэглэгч', 'Барааны код', 'Барааны нэр', 'Ангилал', 'Х/н',
            'Захиалсан тоо', 'Хүлээн авсан', 'Хүргэлтийн төлөв',
            'Валют', 'Нэгж үнэ', 'Нийт дүн', 'Ханш', 'Нийт дүн /₮/',
            'Захиалгын төлөв', 'Хариуцагч'
        ]
        rowx = 4
        sheet.set_row(rowx, 28)
        for c_idx, h in enumerate(headers):
            sheet.write(rowx, c_idx, h, hdr_fmt)

        sheet.freeze_panes(5, 0)

        type_map = {'local': 'Дотоод', 'foreign': 'Гадаад'}
        state_map = {
            'draft': 'Ноорог',
            'sent': 'Илгээсэн',
            'to approve': 'Хүлээгдэж буй',
            'purchase': 'Батлагдсан',
            'done': 'Түгжигдсэн',
            'cancel': 'Цуцалсан'
        }

        tot_qty = 0.0
        tot_rec = 0.0
        tot_mnt = 0.0

        for count, line in enumerate(lines, 1):
            rowx += 1
            po = line.order_id
            prod = line.product_id

            # Date formatting with user timezone
            odate = po[date_field]
            date_str = ''
            if odate:
                local_dt = pytz.utc.localize(odate).astimezone(user_tz)
                date_str = local_dt.strftime('%Y-%m-%d')

            p_type = type_map.get(po.purchase_type, po.purchase_type or '')

            # Line delivery status
            if line.qty_received >= line.product_qty and line.product_qty > 0:
                rc_stat = 'Хүргэгдсэн'
            elif line.qty_received > 0:
                rc_stat = 'Хэсэгчлэн'
            else:
                rc_stat = 'Хүргэгдээгүй'

            st_label = state_map.get(po.state, po.state or '')
            uom_name = line.product_uom.name or (prod.uom_id.name if prod else '')
            cat_name = prod.categ_id.name if prod and prod.categ_id else ''
            code = prod.default_code or '' if prod else ''
            p_name = prod.display_name if prod else (line.name or '')

            p_qty = float(line.product_qty or 0.0)
            r_qty = float(line.qty_received or 0.0)
            p_unit = float(line.price_unit or 0.0)
            p_total = float(line.price_total or 0.0)

            c_rate = float(po.currency_rate or 1.0)
            if c_rate <= 0.0:
                c_rate = 1.0
            total_mnt = round(p_total * c_rate, 2)

            end_user = line.sales_partner_id.name or po.sales_partner_id.name or ''

            sheet.write(rowx, 0, count, cell_center)
            sheet.write(rowx, 1, po.name or '', cell_center)
            sheet.write(rowx, 2, date_str, cell_center)
            sheet.write(rowx, 3, p_type, cell_center)
            sheet.write(rowx, 4, po.partner_id.name or '', cell_left)
            sheet.write(rowx, 5, end_user, cell_left)
            sheet.write(rowx, 6, code, cell_left)
            sheet.write(rowx, 7, p_name, cell_left)
            sheet.write(rowx, 8, cat_name, cell_left)
            sheet.write(rowx, 9, uom_name, cell_center)
            sheet.write(rowx, 10, p_qty, cell_right)
            sheet.write(rowx, 11, r_qty, cell_right)
            sheet.write(rowx, 12, rc_stat, cell_center)
            sheet.write(rowx, 13, po.currency_id.name or '', cell_center)
            sheet.write(rowx, 14, p_unit, cell_right)
            sheet.write(rowx, 15, p_total, cell_right)
            sheet.write(rowx, 16, c_rate, cell_right)
            sheet.write(rowx, 17, total_mnt, cell_right)
            sheet.write(rowx, 18, st_label, cell_center)
            sheet.write(rowx, 19, po.user_id.name or '', cell_left)

            tot_qty += p_qty
            tot_rec += r_qty
            tot_mnt += total_mnt

        # Totals row
        rowx += 1
        sheet.merge_range(rowx, 0, rowx, 9, 'Нийт дүн', tot_lbl)
        sheet.write(rowx, 10, tot_qty, tot_fmt)
        sheet.write(rowx, 11, tot_rec, tot_fmt)
        sheet.write(rowx, 12, '', tot_lbl)
        sheet.write(rowx, 13, '', tot_lbl)
        sheet.write(rowx, 14, '', tot_lbl)
        sheet.write(rowx, 15, '', tot_lbl)
        sheet.write(rowx, 16, '', tot_lbl)
        sheet.write(rowx, 17, tot_mnt, tot_fmt)
        sheet.write(rowx, 18, '', tot_lbl)
        sheet.write(rowx, 19, '', tot_lbl)

        workbook.close()

        if get_file:
            output.seek(0)
            return output.getvalue()

        output.seek(0)
        response.stream.write(output.read())
        output.close()
