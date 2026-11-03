# -*- coding: utf-8 -*-
from odoo import fields, http
from odoo.http import content_disposition, request

OWNER_CARD_REPORTS = {
    'account.asset.asset': 'report.l10n_mn_asset.asset_owner_card_template',
    'hr.employee': 'report.l10n_mn_asset.employee_asset_owner_card_template',
}


class AssetOwnerCardController(http.Controller):

    @http.route('/l10n_mn_asset/asset_owner_card/xlsx/<string:model>', type='http', auth='user')
    def asset_owner_card_xlsx(self, model, ids='', **kw):
        if model not in OWNER_CARD_REPORTS:
            return request.not_found()
        records = request.env[model].browse([int(i) for i in ids.split(',') if i.isdigit()]).exists()
        records.check_access_rights('read')
        records.check_access_rule('read')
        content = request.env[OWNER_CARD_REPORTS[model]]._get_xlsx(records.ids)
        now = fields.Datetime.context_timestamp(request.env.user, fields.Datetime.now())
        filename = 'Хөрөнгө эзэмшигчийн карт_%s.xlsx' % now.strftime('%Y%m%d_%H%M')
        return request.make_response(content, headers=[
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('Content-Disposition', content_disposition(filename)),
        ])
