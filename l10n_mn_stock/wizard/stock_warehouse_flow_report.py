# -*- coding: utf-8 -*-
from urllib.parse import urlencode

from odoo import fields, models


class StockWarehouseFlowReport(models.TransientModel):
    """
        Агуулах, харилцагчдын хоорондох тодорхой барааны урсгалыг
        зангилаа-судал (node-edge) диаграм хэлбэрээр шинэ таб дээр нээж
        харуулах цонх.
    """
    _name = "stock.warehouse.flow.report"
    _description = "Stock warehouse flow diagram wizard"

    company_id = fields.Many2one('res.company', string=u'Компани', readonly=True,
                                 default=lambda self: self.env.company)
    product_id = fields.Many2one('product.product', string=u'Бараа', required=True)
    start_date = fields.Date(string=u'Эхлэх огноо', required=True,
                             default=fields.Date.context_today)
    end_date = fields.Date(string=u'Дуусах огноо', required=True,
                           default=fields.Date.context_today)
    warehouse_ids = fields.Many2many('stock.warehouse', string=u'Агуулах',
                                     help=u'Хоосон орхивол холбогдох бүх агуулахыг харуулна.')

    def action_view_flow_diagram(self):
        self.ensure_one()
        params = {
            'product_id': self.product_id.id,
            'date_from': str(self.start_date),
            'date_to': str(self.end_date),
            'company_id': self.company_id.id,
        }
        if self.warehouse_ids:
            params['warehouse_ids'] = ','.join(str(i) for i in self.warehouse_ids.ids)
        url = '/l10n_mn_stock/warehouse_flow?%s' % urlencode(params)
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }
