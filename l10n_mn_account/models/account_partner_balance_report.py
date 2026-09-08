# -*- coding: utf-8 -*-
from odoo import _, fields, models, tools


class AccountPartnerBalanceReport(models.Model):
    """
        Компани тус бүрийн хамгийн их (Топ 20) авлага/өглөгтэй харилцагчдыг
        баганан график (bar chart)-аар хурдан харах зориулалттай SQL view
        загварын модель. Удирдлагад 7 хоног бүр шалгахад тохиромжтой.
    """
    _name = "account.partner.balance.report"
    _description = "Top partner balance report"
    _auto = False
    _order = "abs_balance desc"

    partner_id = fields.Many2one('res.partner', string=u'Харилцагч', readonly=True)
    company_id = fields.Many2one('res.company', string=u'Компани', readonly=True)
    currency_id = fields.Many2one('res.currency', string=u'Валют', readonly=True)
    balance_type = fields.Selection([
        ('receivable', u'Авлага'),
        ('payable', u'Өглөг'),
    ], string=u'Төрөл', readonly=True)
    balance = fields.Float(string=u'Үлдэгдэл', readonly=True, group_operator='sum')
    abs_balance = fields.Float(string=u'Үлдэгдэл (үнэмлэхүй дүн)', readonly=True, group_operator='sum')
    rank = fields.Integer(string=u'Эрэмбэ', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                WITH ar_ap_lines AS (
                    SELECT
                        aml.partner_id AS partner_id,
                        aml.company_id AS company_id,
                        aml.account_id AS account_id,
                        aml.balance AS balance,
                        aml.date AS date,
                        (j.type = 'opening') AS is_opening
                    FROM account_move_line aml
                    JOIN account_account aa ON aa.id = aml.account_id
                    JOIN account_journal j ON j.id = aml.journal_id
                    WHERE aml.parent_state = 'posted'
                      AND aml.partner_id IS NOT NULL
                      AND aa.account_type IN ('asset_receivable', 'asset_prepayments', 'liability_payable')
                ),
                last_opening AS (
                    SELECT partner_id, company_id, account_id, MAX(date) AS opening_date
                    FROM ar_ap_lines
                    WHERE is_opening
                    GROUP BY partner_id, company_id, account_id
                ),
                effective_lines AS (
                    SELECT l.partner_id AS partner_id, l.company_id AS company_id, l.balance AS balance
                    FROM ar_ap_lines l
                    LEFT JOIN last_opening o
                        ON o.partner_id = l.partner_id
                       AND o.company_id = l.company_id
                       AND o.account_id = l.account_id
                    WHERE o.opening_date IS NULL
                       OR l.date >= o.opening_date
                ),
                ranked AS (
                    SELECT
                        partner_id,
                        company_id,
                        SUM(balance) AS balance,
                        ROW_NUMBER() OVER (
                            PARTITION BY company_id
                            ORDER BY ABS(SUM(balance)) DESC
                        ) AS rn
                    FROM effective_lines
                    GROUP BY partner_id, company_id
                )
                SELECT
                    ROW_NUMBER() OVER (ORDER BY ranked.company_id, ranked.rn) AS id,
                    ranked.partner_id AS partner_id,
                    ranked.company_id AS company_id,
                    rc.currency_id AS currency_id,
                    CASE WHEN ranked.balance >= 0 THEN 'receivable' ELSE 'payable' END AS balance_type,
                    ranked.balance AS balance,
                    ABS(ranked.balance) AS abs_balance,
                    ranked.rn AS rank
                FROM ranked
                JOIN res_company rc ON rc.id = ranked.company_id
                WHERE ABS(ranked.balance) > 0.01
            )
        """ % self._table)

    def action_view_move_lines(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('%s - Өглөг, авлагын дэлгэрэнгүй') % self.partner_id.name,
            'res_model': 'account.move.line',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [
                ('partner_id', '=', self.partner_id.id),
                ('company_id', '=', self.company_id.id),
                ('parent_state', '=', 'posted'),
                ('account_id.account_type', 'in', ['asset_receivable', 'asset_prepayments', 'liability_payable']),
            ],
            'context': {'group_by': ['account_id']},
        }
