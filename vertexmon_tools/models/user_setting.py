from odoo import api, fields, models, _


class UserSetting(models.Model):
    _name = 'user.setting'
    _description = 'User Setting'

    user_ids = fields.Many2many('res.users', 'user_setting_user_rel', 'setting_id', 'user_id', string="Users")
    role_id = fields.Many2one('user.role', 'Role')
    hide_menu_ids = fields.Many2many('ir.ui.menu', 'user_setting_menu_rel', 'setting_id', 'menu_id', string="Hide Menus")
    group_ids = fields.Many2many('res.groups', 'user_setting_group_rel', 'setting_id', 'group_id', string="Groups")


    @api.model
    def create(self, vals):
        res = super(UserSetting, self).create(vals)
        for obj in res:
            for user in obj.user_ids:
                if obj.role_id:
                    if obj.role_id.group_ids:
                        user.groups_id = [(6, 0, obj.role_id.group_ids.ids)]
                    if obj.role_id.hide_menu_ids:
                        user.hide_menu_ids = [(6, 0, obj.role_id.hide_menu_ids.ids)]
                if obj.group_ids:
                    user.groups_id = ([(4, group.id)] for group in obj.group_ids)
                if obj.hide_menu_ids:
                    user.hide_menu_ids = ([(4, menu.id)] for menu in obj.hide_menu_ids)
        self.env.registry.clear_cache()
        return res

    def write(self, vals):
        res = super(UserSetting, self).write(vals)
        for obj in self:
            for user in obj.user_ids:
                if obj.role_id:
                    if obj.role_id.group_ids:
                        user.groups_id = [(6, 0, obj.role_id.group_ids.ids)]
                    if obj.role_id.hide_menu_ids:
                        user.hide_menu_ids = [(6, 0, obj.role_id.hide_menu_ids.ids)]
                if obj.group_ids:
                    user.groups_id = ([(4, group.id)] for group in obj.group_ids)
                if obj.hide_menu_ids:
                    user.hide_menu_ids = ([(4, menu.id)] for menu in obj.hide_menu_ids)
        self.env.registry.clear_cache()
        return res


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    hide_user_ids = fields.Many2many('res.users', 'hide_menu_user_rel', 'menu_id', 'user_id', string="Hide Users")

    @api.returns('self')
    def _filter_visible_menus(self):
        menus = super()._filter_visible_menus()
        user = self.env.user
        return menus.filtered(
            lambda menu: menu.id not in user.hide_menu_ids.ids
        )


class ResUsers(models.Model):
    _inherit = 'res.users'

    hide_menu_ids = fields.Many2many('ir.ui.menu', 'hide_menu_user_rel', 'user_id', 'menu_id', string="Hide Menus")

    def write(self, vals):
        result = super(ResUsers, self).write(vals)
        if "hide_menu_ids" in vals:
            self.env.registry.clear_cache()
        return result