from odoo import models, fields, api


class ProjectTask(models.Model):
    _inherit = "project.task"

    user_ids = fields.Many2many(comodel_name="res.users", string="Assign To Multi User")

