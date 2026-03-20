# -*- coding: utf-8 -*-
from odoo import api, fields, models


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



class KpiTemplateLine(models.Model):
    _name = "kpi.template.line"
    _description = "KPI Template Line"
    _order = "id"

    template_id = fields.Many2one("kpi.template", string="KPI Template", required=True, ondelete="cascade")
    name = fields.Many2one("kpi.line.section", string="KPI Section", required=True)
    weight_percentage = fields.Float(string="Weight Percentage", required=True)



class KpiLineSection(models.Model):
    _name = "kpi.line.section"
    _description = "KPI Line Section"
    _order = "name"

    name = fields.Char(string="Section Name", required=True)
