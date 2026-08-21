from odoo import api, fields, models, _


class UserRole(models.Model):
    _name = 'user.role'
    _description = 'User Role'

    name = fields.Char(string="Name")
    hide_menu_ids = fields.Many2many('ir.ui.menu', 'user_role_menu_rel', 'role_id', 'menu_id', string="Hide Menus")
    group_ids = fields.Many2many('res.groups', 'user_role_group_rel', 'role_id', 'menu_id', string="Groups")
