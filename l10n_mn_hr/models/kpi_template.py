# -*- coding: utf-8 -*-
from odoo import api, fields, models

# Ажлын гүйцэтгэлийг дүгнэх хуудас (KPI)-ны тохиргоо
SOURCE_TYPE = [
    ('manual', 'Гараар оруулна'),
    ('work_plan', 'Ажлын төлөвлөгөөний үнэлгээ'),
    ('extra', 'Төлөвлөгөөнөөс бусад ажлын үнэлгээ'),
]
CALC_METHOD = [
    ('direct', 'Гүйцэтгэлээр шууд'),
    ('scale', 'Шатлалаар (80%+ бол гүйцэтгэлээр, 60-79% бол 50%, 59%-с бага бол 0%)'),
]


def effective_achievement(value, method):
    """value: бутархай (0.8 = 80%)"""
    if method == 'scale':
        if value >= 0.8:
            return min(value, 1.0)
        return 0.5 if value >= 0.6 else 0.0
    return min(value, 1.0)


class KpiTemplate(models.Model):
    _name = "kpi.template"
    _description = "KPI Template"
    _order = "name"

    name = fields.Char(string="Template Name", required=True)
    active = fields.Boolean(default=True)
    date_type = fields.Selection([
        ("month", "Month"),
        ("session", "Session"),
        ("half_year", "Half Year"),
    ], string="Period Type", default="month", required=True)
    note = fields.Text(string="Description")
    line_ids = fields.One2many("kpi.template.line", "template_id", string="Template Lines")
    job_id = fields.Many2one("hr.job", string="Албан тушаал")
    approver_id = fields.Many2one("hr.employee", string="Батлах удирдлага")
    approver_title = fields.Char(string="Батлах удирдлагын албан тушаал", default="Гүйцэтгэх захирал")
    kpi_amount_note = fields.Char(string="KPI 100%-д ногдох мөнгөн дүн", default="Үндсэн цалингийн 50% хүртэлх дүн")
    min_score = fields.Float(string="KPI олгох босго үнэлгээ", default=0.8)



class KpiTemplateLine(models.Model):
    _name = "kpi.template.line"
    _description = "KPI Template Line"
    _order = "sequence, id"

    template_id = fields.Many2one("kpi.template", string="KPI Template", required=True, ondelete="cascade")
    name = fields.Many2one("kpi.line.section", string="KPI Section", required=True)
    weight_percentage = fields.Float(string="Weight Percentage", required=True)
    sequence = fields.Integer(default=10)
    criteria = fields.Html(string="Шалгуур үзүүлэлт")
    source = fields.Char(string="Гүйцэтгэл тооцох эх сурвалж")
    target = fields.Text(string="Зорилтот үр дүн / Хэмжүүр")
    source_type = fields.Selection(SOURCE_TYPE, string="Гүйцэтгэл авах", default="manual", required=True)
    calc_method = fields.Selection(CALC_METHOD, string="Тооцох арга", default="direct", required=True)
    evaluator = fields.Char(string="Үнэлэх хэлтэс, албан тушаалтан", default="Шууд удирдлага")



class KpiLineSection(models.Model):
    _name = "kpi.line.section"
    _description = "KPI Line Section"
    _order = "name"

    name = fields.Char(string="Section Name", required=True)
