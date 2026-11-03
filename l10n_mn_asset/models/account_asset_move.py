# -*- coding: utf-8 -*-
from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountAssetMove(models.Model):
    """Хөрөнгө шилжүүлэг: нэг эзэмшигчээс нөгөөд хөрөнгө шилжүүлж, батлахад хөрөнгийн эзэмшигчийг солино."""
    _name = 'account.asset.move'
    _description = 'Хөрөнгө шилжүүлэг'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company)
    name = fields.Char(string='Дугаар', required=True, readonly=True, copy=False, default='/')
    date = fields.Date(string='Шилжүүлсэн огноо', required=True,
                       default=fields.Date.context_today, tracking=True)
    from_owner_id = fields.Many2one('hr.employee', string='Хүлээлгэн өгөгч', tracking=True,
                                    help='Хоосон бол эзэмшигчгүй хөрөнгийг анх олгож байна гэж үзнэ.')
    to_owner_id = fields.Many2one('hr.employee', string='Хүлээн авагч', required=True, tracking=True)
    department_id = fields.Many2one('hr.department', string='Хүлээн авагчийн хэлтэс',
                                    compute='_compute_department_id', store=True, readonly=False)
    asset_ids = fields.Many2many('account.asset.asset', 'account_asset_move_asset_rel',
                                 'move_id', 'asset_id', string='Хөрөнгө', required=True)
    asset_out_location_id = fields.Many2one('asset.location', string='Гарах байршил')
    asset_in_location_id = fields.Many2one('asset.location', string='Хүрэх байршил')
    user_id = fields.Many2one('res.users', string='Бүртгэсэн', required=True,
                              default=lambda self: self.env.user)
    approved_user_id = fields.Many2one('res.users', string='Баталсан', readonly=True, copy=False)
    note = fields.Text(string='Тайлбар')
    asset_count = fields.Integer(string='Хөрөнгийн тоо', compute='_compute_asset_count')
    state = fields.Selection([
        ('draft', 'Ноорог'),
        ('confirm', 'Батлагдсан'),
        ('cancel', 'Цуцлагдсан'),
    ], string='Төлөв', default='draft', required=True, copy=False, tracking=True)

    @api.depends('to_owner_id')
    def _compute_department_id(self):
        for move in self:
            move.department_id = move.to_owner_id.department_id

    @api.depends('asset_ids')
    def _compute_asset_count(self):
        for move in self:
            move.asset_count = len(move.asset_ids)

    @api.onchange('from_owner_id')
    def _onchange_from_owner_id(self):
        # Өөр эзэмшигчийн хөрөнгө үлдэхгүйн тулд
        self.asset_ids = self.asset_ids.filtered(lambda a: a.owner_id == self.from_owner_id)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('account.asset.move') or '/'
        return super().create(vals_list)

    def unlink(self):
        if any(move.state == 'confirm' for move in self):
            raise UserError(_('Батлагдсан шилжүүлгийг устгах боломжгүй. Эхлээд цуцална уу.'))
        return super().unlink()

    def _check_before_confirm(self):
        for move in self:
            if not move.asset_ids:
                raise UserError(_('%s: шилжүүлэх хөрөнгө сонгоно уу.') % move.name)
            if move.from_owner_id == move.to_owner_id:
                raise UserError(_('%s: хүлээлгэн өгөгч, хүлээн авагч ижил байна.') % move.name)
            wrong_owner = move.asset_ids.filtered(lambda a: a.owner_id != move.from_owner_id)
            if wrong_owner:
                raise UserError(_(
                    '%s: дараах хөрөнгө одоо "%s"-ийн эзэмшилд биш байна:\n%s'
                ) % (move.name, move.from_owner_id.name or _('Эзэмшигчгүй'),
                     '\n'.join('- %s (%s)' % (a.name, a.owner_id.name or '-') for a in wrong_owner)))
            closed = move.asset_ids.filtered(lambda a: a.state not in ('draft', 'open'))
            if closed:
                raise UserError(_('%s: хаагдсан/актлагдсан хөрөнгийг шилжүүлэх боломжгүй:\n%s')
                                % (move.name, '\n'.join('- %s' % a.name for a in closed)))

    def _apply_to_assets(self, owner, location):
        self.ensure_one()
        vals = {'owner_id': owner.id}
        if location:
            vals['asset_location_id'] = location.id
        self.asset_ids.with_context(asset_move_transfer=True).write(vals)
        for asset in self.asset_ids:
            asset.message_post(body=Markup('%s: %s') % (_('Хөрөнгө шилжүүлэг'), self._get_html_link()))

    def action_asset_move_confirm(self):
        self._check_before_confirm()
        for move in self:
            move._apply_to_assets(move.to_owner_id, move.asset_in_location_id)
            move.write({'state': 'confirm', 'approved_user_id': self.env.user.id})

    def action_asset_move_cancel(self):
        for move in self.filtered(lambda m: m.state == 'confirm'):
            # Дараа нь дахин шилжсэн хөрөнгийг буцааж болохгүй
            moved_again = move.asset_ids.filtered(lambda a: a.owner_id != move.to_owner_id)
            if moved_again:
                raise UserError(_(
                    '%s: дараах хөрөнгө энэ шилжүүлгээс хойш дахин шилжсэн тул цуцлах боломжгүй:\n%s'
                ) % (move.name, '\n'.join('- %s (%s)' % (a.name, a.owner_id.name or '-') for a in moved_again)))
            move._apply_to_assets(move.from_owner_id, move.asset_out_location_id)
        self.write({'state': 'cancel'})

    def action_asset_move_draft(self):
        self.filtered(lambda m: m.state == 'cancel').write({'state': 'draft', 'approved_user_id': False})

    def action_view_assets(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Хөрөнгө'),
            'res_model': 'account.asset.asset',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.asset_ids.ids)],
        }


class AccountAssetAsset(models.Model):
    _inherit = 'account.asset.asset'

    asset_move_ids = fields.Many2many('account.asset.move', 'account_asset_move_asset_rel',
                                      'asset_id', 'move_id', string='Шилжүүлэг', readonly=True)
    asset_move_count = fields.Integer(string='Шилжүүлгийн тоо', compute='_compute_asset_move_count')

    def write(self, vals):
        # Ноорог биш хөрөнгийн эзэмшигчийг зөвхөн Хөрөнгө шилжүүлгээр солино
        if 'owner_id' in vals and not self.env.context.get('asset_move_transfer'):
            locked = self.filtered(lambda a: a.state != 'draft' and a.owner_id.id != (vals['owner_id'] or False))
            if locked:
                raise UserError(_(
                    'Ашиглагдаж буй хөрөнгийн эзэмшигчийг шууд солих боломжгүй. '
                    '"Шилжүүлэх" товч эсвэл Санхүү → Хөрөнгө шилжүүлэг ашиглана уу.\n%s'
                ) % '\n'.join('- %s' % a.name for a in locked))
        return super().write(vals)

    def _compute_asset_move_count(self):
        for asset in self:
            asset.asset_move_count = len(asset.asset_move_ids)

    def action_asset_transfer(self):
        """Хөрөнгийн маягт/жагсаалтаас шинэ шилжүүлэг үүсгэх."""
        owners = self.mapped('owner_id')
        if len(owners) > 1:
            raise UserError(_('Нэг шилжүүлэгт зөвхөн нэг эзэмшигчийн хөрөнгийг сонгоно уу.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Хөрөнгө шилжүүлэх'),
            'res_model': 'account.asset.move',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_from_owner_id': owners.id,
                'default_asset_ids': [(6, 0, self.ids)],
                'default_asset_out_location_id': self[:1].asset_location_id.id,
            },
        }

    def action_view_asset_moves(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Шилжүүлэг'),
            'res_model': 'account.asset.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.asset_move_ids.ids)],
            'context': {'default_from_owner_id': self.owner_id.id,
                        'default_asset_ids': [(6, 0, self.ids)]},
        }
