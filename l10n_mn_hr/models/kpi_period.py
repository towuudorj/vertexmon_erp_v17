# -*- coding: utf-8 -*-
from datetime import date, timedelta

from odoo import api, fields, models

QUARTER_SELECTION = [
    ('1', '1-р улирал'),
    ('2', '2-р улирал'),
    ('3', '3-р улирал'),
    ('4', '4-р улирал'),
]
MONTH_SELECTION = [(str(m), '%s-р сар' % m) for m in range(1, 13)]


def quarter_of_month(month):
    return str((int(month) - 1) // 3 + 1)


def month_bounds(year, month_from, month_to):
    date_from = date(year, month_from, 1)
    next_start = date(year + 1, 1, 1) if month_to == 12 else date(year, month_to + 1, 1)
    return date_from, next_start - timedelta(days=1)


class KpiPeriodMixin(models.AbstractModel):
    """Он / улирал / сарын нийтлэг талбарууд."""
    _name = 'kpi.period.mixin'
    _description = 'KPI хугацааны mixin'

    period_type = fields.Selection([
        ('quarter', 'Улирал'),
        ('month', 'Сар'),
    ], string='Төлөвлөх хугацаа', required=True, default='quarter')
    year = fields.Integer('Он', required=True, default=lambda self: fields.Date.context_today(self).year)
    quarter = fields.Selection(QUARTER_SELECTION, string='Улирал', compute='_compute_quarter', store=True,
                               readonly=False, precompute=True)
    month = fields.Selection(MONTH_SELECTION, string='Сар',
                             default=lambda self: str(fields.Date.context_today(self).month))
    date_from = fields.Date('Эхлэх огноо', compute='_compute_period_dates', store=True)
    date_to = fields.Date('Дуусах огноо', compute='_compute_period_dates', store=True)
    period_label = fields.Char('Хугацаа', compute='_compute_period_dates', store=True)

    @api.depends('period_type', 'month')
    def _compute_quarter(self):
        for rec in self:
            if rec.period_type == 'month' and rec.month:
                rec.quarter = quarter_of_month(rec.month)
            elif not rec.quarter:
                rec.quarter = quarter_of_month(fields.Date.context_today(rec).month)

    @api.depends('period_type', 'year', 'quarter', 'month')
    def _compute_period_dates(self):
        for rec in self:
            if not rec.year:
                rec.date_from = rec.date_to = rec.period_label = False
            elif rec.period_type == 'month' and rec.month:
                m = int(rec.month)
                rec.date_from, rec.date_to = month_bounds(rec.year, m, m)
                rec.period_label = '%s оны %s-р сар' % (rec.year, m)
            elif rec.quarter:
                q = int(rec.quarter)
                rec.date_from, rec.date_to = month_bounds(rec.year, q * 3 - 2, q * 3)
                rec.period_label = '%s оны %s-р улирал' % (rec.year, q)
            else:
                rec.date_from = rec.date_to = rec.period_label = False
