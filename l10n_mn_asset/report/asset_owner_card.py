# -*- coding: utf-8 -*-
import base64
import io

import xlsxwriter

from odoo import api, models

ASSET_STATE_LABELS = {
    'draft': 'Ноорог',
    'open': 'Ашиглагдаж буй',
    'close': 'Хаагдсан',
    'scrap': 'Актлагдсан',
}


class AssetOwnerCardMixin(models.AbstractModel):
    _name = 'report.l10n_mn_asset.asset_owner_card_mixin'
    _description = 'Asset owner card helper'

    @api.model
    def _group_by_owner(self, assets):
        """Хөрөнгийг эзэмшигчээр бүлэглэнэ: [(owner, assets), ...]"""
        groups = []
        for owner in assets.mapped('owner_id').sorted('name'):
            groups.append((owner, assets.filtered(lambda a: a.owner_id == owner)))
        no_owner = assets.filtered(lambda a: not a.owner_id)
        if no_owner:
            groups.append((self.env['hr.employee'], no_owner))
        return groups

    @api.model
    def _get_previous_owners(self, assets):
        """Chatter-ийн owner_id түүхээс {asset_id: (өмнөх эзэмшигч, шилжсэн огноо)}.

        Шилжсэн огноо: одоогийн эзэмшигч хөрөнгийг хүлээж авсан хамгийн сүүлийн өөрчлөлт.
        Өмнөх эзэмшигч: тэр үеэс өмнөх хамгийн сүүлийн хоосон биш эзэмшигч.
        """
        result = {}
        if not assets:
            return result
        field = self.env['ir.model.fields']._get('account.asset.asset', 'owner_id')
        # mail.tracking.value-г зөвхөн админ уншдаг тул sudo
        trackings = self.env['mail.tracking.value'].sudo().search([
            ('field_id', '=', field.id),
            ('mail_message_id.model', '=', 'account.asset.asset'),
            ('mail_message_id.res_id', 'in', assets.ids),
        ]).sorted(lambda t: (t.mail_message_id.date, t.id), reverse=True)
        by_asset = {}
        for tracking in trackings:
            by_asset.setdefault(tracking.mail_message_id.res_id, []).append(tracking)
        for asset in assets:
            transfer_date = False
            for tracking in by_asset.get(asset.id, []):
                if not transfer_date:
                    if asset.owner_id and tracking.new_value_integer != asset.owner_id.id:
                        continue
                    transfer_date = tracking.mail_message_id.date.date()
                if tracking.old_value_integer:
                    result[asset.id] = (tracking.old_value_char or '', transfer_date)
                    break
        return result

    @api.model
    def _prepare_values(self, docs, assets):
        assets = assets.sorted(lambda a: (a.date or False, a.id))
        return {
            'docs': docs,
            'groups': self._group_by_owner(assets),
            'previous_owners': self._get_previous_owners(assets),
            'state_labels': ASSET_STATE_LABELS,
            'company': assets[:1].company_id or self.env.company,
        }

    @api.model
    def _get_xlsx_logo(self, company):
        """Компанийн логог 60px өндөрт багтаан xlsxwriter insert_image-д бэлдэнэ."""
        if not company.logo:
            return False
        data = base64.b64decode(company.logo)
        scale = 1.0
        try:
            from PIL import Image
            image = Image.open(io.BytesIO(data))
            # xlsxwriter зургийг 96/DPI-гаар багасгадаг тул түүнийг тооцно
            dpi_x, dpi_y = image.info.get('dpi') or (96, 96)
            width = image.width * 96.0 / (dpi_x or 96)
            height = image.height * 96.0 / (dpi_y or 96)
            scale = min(60.0 / height, 190.0 / width)
        except Exception:
            pass
        return {'image_data': io.BytesIO(data), 'x_scale': scale, 'y_scale': scale}

    @api.model
    def _get_xlsx(self, docids):
        """PDF-тэй ижил агуулгыг Excel-ээр: эзэмшигч бүрт нэг sheet."""
        values = self._get_report_values(docids)
        state_labels = values['state_labels']
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        base = {'font_name': 'Times New Roman', 'font_size': 11, 'bold': True}
        head = workbook.add_format(dict(base, font_size=14))
        title = workbook.add_format(dict(base, border=1, align='center', valign='vcenter',
                                         text_wrap=True, bg_color='#F2F2F2'))
        cell = workbook.add_format(dict(base, border=1, align='center', valign='vcenter', text_wrap=True))
        amount = workbook.add_format(dict(base, border=1, align='right', valign='vcenter',
                                          num_format='#,##0.00'))
        sign = workbook.add_format(base)

        previous_owners = values['previous_owners']
        headers = ['№', 'Төлөв', 'Ангилал', 'Нийт дүн', 'Огноо', 'Хөрөнгийн код',
                   'Хөрөнгийн нэр', 'Хөрөнгө эзэмшигч', 'Өмнөх эзэмшигч', 'Шилжсэн огноо', 'Үлдэгдэл дүн']
        widths = [5, 16, 26, 16, 12, 22, 34, 24, 24, 12, 16]
        logo = self._get_xlsx_logo(values['company'])
        used_names = set()
        groups = values['groups'] or [(self.env['hr.employee'], self.env['account.asset.asset'])]
        for owner, assets in groups:
            sheet_name = (owner.name or 'Эзэмшигчгүй')[:28]
            for ch in '[]:*?/\\':
                sheet_name = sheet_name.replace(ch, ' ')
            unique_name, i = sheet_name, 1
            while unique_name.lower() in used_names:
                i += 1
                unique_name = '%s %s' % (sheet_name, i)
            used_names.add(unique_name.lower())
            sheet = workbook.add_worksheet(unique_name)
            sheet.set_landscape()
            sheet.set_paper(9)
            sheet.fit_to_pages(1, 0)
            sheet.repeat_rows(2)  # хэвлэхэд толгой мөр хуудас бүрт давтагдана
            for col, width in enumerate(widths):
                sheet.set_column(col, col, width)

            name_col = 0
            if logo:
                sheet.set_row(0, 50)
                sheet.insert_image(0, 0, 'logo.png', dict(logo, x_offset=2, y_offset=4, object_position=3))
                name_col = 2
            sheet.write(0, name_col, values['company'].name, head)
            sheet.write(0, 4, 'Хөрөнгө эзэмшигч' + (': %s' % owner.name if owner else ''), head)
            row = 2
            for col, label in enumerate(headers):
                sheet.write(row, col, label, title)
            for idx, asset in enumerate(assets, 1):
                row += 1
                sheet.write(row, 0, idx, cell)
                sheet.write(row, 1, state_labels.get(asset.state, asset.state), cell)
                sheet.write(row, 2, asset.category_id.name or '', cell)
                sheet.write_number(row, 3, asset.value, amount)
                sheet.write(row, 4, asset.date.strftime('%Y.%m.%d') if asset.date else '', cell)
                sheet.write(row, 5, asset.code or '', cell)
                sheet.write(row, 6, asset.name or '', cell)
                sheet.write(row, 7, asset.owner_id.name or '', cell)
                prev_owner, transfer_date = previous_owners.get(asset.id, ('', False))
                sheet.write(row, 8, prev_owner, cell)
                sheet.write(row, 9, transfer_date.strftime('%Y.%m.%d') if transfer_date else '', cell)
                sheet.write_number(row, 10, asset.value_residual, amount)
            if len(assets) > 1:
                row += 1
                sheet.merge_range(row, 0, row, 2, 'Нийт', amount)
                sheet.write_number(row, 3, sum(assets.mapped('value')), amount)
                sheet.merge_range(row, 4, row, 9, '', cell)
                sheet.write_number(row, 10, sum(assets.mapped('value_residual')), amount)

            row += 3
            line = '/................................/........................................./'
            for label in ('ХӨРӨНГӨ ОЛГОХЫГ ЗӨВШӨӨРСӨН:', 'ХӨРӨНГӨ ХҮЛЭЭЛГЭЖ ӨГСӨН:', 'ХӨРӨНГӨ ХҮЛЭЭН АВСАН:'):
                sheet.write(row, 1, label, sign)
                sheet.write(row, 5, line, sign)
                row += 2
        workbook.close()
        return output.getvalue()


class ReportAssetOwnerCard(models.AbstractModel):
    """Үндсэн хөрөнгө дээрээс: сонгосон хөрөнгүүдийг эзэмшигчээр нь хэвлэнэ."""
    _name = 'report.l10n_mn_asset.asset_owner_card_template'
    _inherit = 'report.l10n_mn_asset.asset_owner_card_mixin'
    _description = 'Asset owner card'

    @api.model
    def _get_report_values(self, docids, data=None):
        assets = self.env['account.asset.asset'].browse(docids)
        return self._prepare_values(assets, assets)


class ReportEmployeeAssetOwnerCard(models.AbstractModel):
    """Ажилтан дээрээс: тухайн ажилтны эзэмшиж буй хөрөнгүүдийг хэвлэнэ."""
    _name = 'report.l10n_mn_asset.employee_asset_owner_card_template'
    _inherit = 'report.l10n_mn_asset.asset_owner_card_mixin'
    _description = 'Employee asset owner card'

    @api.model
    def _get_report_values(self, docids, data=None):
        employees = self.env['hr.employee'].browse(docids)
        assets = self.env['account.asset.asset'].search([
            ('owner_id', 'in', employees.ids),
            ('state', 'in', ('draft', 'open')),
        ])
        return self._prepare_values(employees, assets)
