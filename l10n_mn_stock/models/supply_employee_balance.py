# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools


class SupplyEmployeeBalance(models.Model):
    """Ажилтан дээр байгаа (хаагдаагүй) хангамжийн бараа.

    Олгосон (+): хангамжийн байрлалаас гарсан, эсвэл шилжүүлгээр хүлээн авсан.
    Хаагдсан (-): хангамжийн байрлал руу буцсан, актлагдсан, эсвэл шилжүүлгээр өгсөн.
    Хугацаа дууссан тоо нь өнөөдрийн огноогоор, хаалтыг эртний олголтоос (FIFO) хасч тооцно.
    stock.picking._get_supply_balances-тай ижил дүрэм.
    """
    _name = 'supply.employee.balance'
    _description = 'Ажилтны хангамжийн үлдэгдэл'
    _auto = False
    _order = 'partner_id, product_id'
    _rec_name = 'product_id'

    partner_id = fields.Many2one('res.partner', string='Ажилтан', readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Ажилтан (HR)', readonly=True)
    department_id = fields.Many2one('hr.department', string='Хэлтэс', readonly=True)
    product_id = fields.Many2one('product.product', string='Бараа', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', string='Барааны загвар', readonly=True)
    categ_id = fields.Many2one('product.category', string='Ангилал', readonly=True)
    uom_id = fields.Many2one('uom.uom', string='Хэмжих нэгж', readonly=True)
    issued_qty = fields.Float(string='Олгосон', readonly=True, digits='Product Unit of Measure')
    closed_qty = fields.Float(string='Буцаасан/Хаасан', readonly=True, digits='Product Unit of Measure')
    balance = fields.Float(string='Үлдэгдэл', readonly=True, digits='Product Unit of Measure')
    expired_qty = fields.Float(string='Хугацаа дууссан', readonly=True, digits='Product Unit of Measure')
    is_expired = fields.Boolean(string='Хугацаа дууссан эсэх', readonly=True)
    first_issue_date = fields.Date(string='Анх олгосон огноо', readonly=True)
    last_issue_date = fields.Date(string='Сүүлд олгосон огноо', readonly=True)
    validity_period = fields.Integer(string='Ашиглах хугацаа (сар)', readonly=True, group_operator=False)
    expire_date = fields.Date(string='Дуусах огноо', readonly=True,
                              help='Сүүлд олгосон огноо + ашиглах хугацаа.')
    unit_cost = fields.Float(string='Нэгж өртөг', compute='_compute_value', digits=(16, 2))
    value = fields.Float(string='Нийт өртөг', compute='_compute_value', digits=(16, 2))

    @api.depends('product_id', 'balance')
    def _compute_value(self):
        for rec in self:
            rec.unit_cost = rec.product_id.standard_price
            rec.value = rec.balance * rec.product_id.standard_price

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                WITH lines AS (
                    SELECT COALESCE(mv.partner_id, sm.partner_id, sp.partner_id) AS partner_id,
                           mv.product_id,
                           COALESCE(sp.issue_date, mv.date::date) AS issue_date,
                           -- Агуулах хоорондын (дотоод -> дотоод) шилжүүлэг ажилтанд хамаарахгүй
                           CASE WHEN (COALESCE(sl.supply_location, FALSE) AND dest.usage != 'internal')
                                     OR COALESCE(dest.supply_transfer_location, FALSE)
                                THEN mv.quantity ELSE 0 END AS issued,
                           CASE WHEN sl.usage != 'internal'
                                     AND (COALESCE(dest.supply_location, FALSE)
                                          OR COALESCE(dest.supply_writeoff_location, FALSE))
                                THEN mv.quantity ELSE 0 END AS closed
                    FROM stock_move_line mv
                    JOIN stock_move sm ON sm.id = mv.move_id
                    LEFT JOIN stock_picking sp ON sp.id = sm.picking_id
                    JOIN stock_location sl ON sl.id = mv.location_id
                    JOIN stock_location dest ON dest.id = mv.location_dest_id
                    WHERE mv.state = 'done'
                      AND (sl.supply_location OR dest.supply_location
                           OR dest.supply_writeoff_location OR dest.supply_transfer_location)
                      AND NOT COALESCE(sp.exclude_from_supply, FALSE)

                    UNION ALL

                    SELECT sp.supply_from_partner_id, mv.product_id, mv.date::date, 0, mv.quantity
                    FROM stock_move_line mv
                    JOIN stock_move sm ON sm.id = mv.move_id
                    JOIN stock_picking sp ON sp.id = sm.picking_id
                    JOIN stock_location dest ON dest.id = mv.location_dest_id
                    WHERE mv.state = 'done'
                      AND dest.supply_transfer_location
                      AND sp.supply_from_partner_id IS NOT NULL
                      AND NOT COALESCE(sp.exclude_from_supply, FALSE)
                ),
                agg AS (
                    SELECT l.partner_id,
                           l.product_id,
                           SUM(l.issued) AS issued_qty,
                           SUM(l.closed) AS closed_qty,
                           MIN(l.issue_date) FILTER (WHERE l.issued > 0) AS first_issue_date,
                           MAX(l.issue_date) FILTER (WHERE l.issued > 0) AS last_issue_date,
                           GREATEST(0,
                               SUM(CASE WHEN COALESCE(pt.validity_period, 0) > 0
                                         AND (l.issue_date + pt.validity_period * INTERVAL '1 month')::date <= CURRENT_DATE
                                        THEN l.issued ELSE 0 END)
                               - SUM(l.closed)) AS expired_qty
                    FROM lines l
                    JOIN product_product pp ON pp.id = l.product_id
                    JOIN product_template pt ON pt.id = pp.product_tmpl_id
                    GROUP BY l.partner_id, l.product_id
                    HAVING SUM(l.issued) - SUM(l.closed) > 0
                )
                SELECT ROW_NUMBER() OVER (ORDER BY a.partner_id, a.product_id) AS id,
                       a.partner_id,
                       emp.id AS employee_id,
                       emp.department_id,
                       a.product_id,
                       pt.id AS product_tmpl_id,
                       pt.categ_id,
                       pt.uom_id,
                       a.issued_qty,
                       a.closed_qty,
                       a.issued_qty - a.closed_qty AS balance,
                       a.expired_qty,
                       a.expired_qty > 0 AS is_expired,
                       a.first_issue_date,
                       a.last_issue_date,
                       COALESCE(pt.validity_period, 0) AS validity_period,
                       CASE WHEN COALESCE(pt.validity_period, 0) > 0 AND a.last_issue_date IS NOT NULL
                            THEN (a.last_issue_date + pt.validity_period * INTERVAL '1 month')::date
                       END AS expire_date
                FROM agg a
                JOIN res_partner rp ON rp.id = a.partner_id
                JOIN product_product pp ON pp.id = a.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                LEFT JOIN LATERAL (
                    SELECT e.id, e.department_id
                    FROM hr_employee e
                    WHERE e.work_contact_id = a.partner_id
                    ORDER BY e.active DESC, e.id
                    LIMIT 1
                ) emp ON TRUE
                WHERE rp.is_company = FALSE
            )
        """)
