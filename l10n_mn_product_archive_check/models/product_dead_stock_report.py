# -*- coding: utf-8 -*-
from odoo import fields, models, tools


class ProductDeadStockReport(models.Model):
    """
        Сүүлийн 1 жил хөдөлгөөнгүй байгаа идэвхтэй барааг (үлдэгдэлтэй эсэхээс
        үл хамааран) илрүүлж, архивлах эсэхийг шийдэхэд хялбар болгох SQL view.
    """
    _name = "product.dead.stock.report"
    _description = "Идэвхгүй барааны жагсаалт"
    _auto = False
    _order = "last_move_date asc"

    product_id = fields.Many2one('product.product', string=u'Бараа', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', string=u'Бараа (загвар)', readonly=True)
    categ_id = fields.Many2one('product.category', string=u'Ангилал', readonly=True)
    last_move_date = fields.Date(string=u'Сүүлийн хөдөлгөөний огноо', readonly=True)
    qty_available = fields.Float(string=u'Одоогийн үлдэгдэл', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                WITH last_move AS (
                    SELECT sml.product_id AS product_id, MAX(sm.date) AS last_move_date
                    FROM stock_move_line sml
                    JOIN stock_move sm ON sm.id = sml.move_id
                    WHERE sm.state = 'done'
                    GROUP BY sml.product_id
                ),
                qty AS (
                    SELECT sq.product_id AS product_id, SUM(sq.quantity) AS qty_available
                    FROM stock_quant sq
                    JOIN stock_location sl ON sl.id = sq.location_id
                    WHERE sl.usage = 'internal'
                    GROUP BY sq.product_id
                )
                SELECT
                    pp.id AS id,
                    pp.id AS product_id,
                    pt.id AS product_tmpl_id,
                    pt.categ_id AS categ_id,
                    lm.last_move_date AS last_move_date,
                    COALESCE(q.qty_available, 0) AS qty_available
                FROM product_product pp
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                LEFT JOIN last_move lm ON lm.product_id = pp.id
                LEFT JOIN qty q ON q.product_id = pp.id
                WHERE pp.active = true
                  AND (lm.last_move_date IS NULL OR lm.last_move_date < CURRENT_DATE - INTERVAL '1 year')
            )
        """ % self._table)

    def action_archive_product(self):
        self.ensure_one()
        self.product_id.action_archive()

    def action_view_product_template(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'res_id': self.product_tmpl_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
