# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero


class StockToAssetWizard(models.TransientModel):
    _name = 'stock.to.asset.wizard'
    _description = 'Агуулахын барааг хөрөнгөд шилжүүлэх'

    @api.model
    def _default_location_id(self):
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        return warehouse.lot_stock_id.id if warehouse else False

    @api.model
    def _default_asset_dest_location_id(self):
        return self.env.ref('l10n_mn_asset.stock_location_asset_transfer', raise_if_not_found=False)

    location_id = fields.Many2one(
        'stock.location', string='Агуулах', required=True,
        domain=[('usage', '=', 'internal')], default=_default_location_id)
    asset_dest_location_id = fields.Many2one(
        'stock.location', string='Хүлээн авах байршил', required=True,
        default=_default_asset_dest_location_id)
    category_id = fields.Many2one('account.asset.category', string='Хөрөнгийн ангилал', required=True)
    date = fields.Date(string='Огноо', required=True, default=fields.Date.context_today)
    note = fields.Text(string='Тэмдэглэл')
    company_id = fields.Many2one('res.company', string='Компани', default=lambda self: self.env.company)
    line_ids = fields.One2many('stock.to.asset.wizard.line', 'wizard_id', string='Мөрүүд')

    def button_transfer(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('Шилжүүлэх бараагаа мөрөнд нэмнэ үү.'))
        if not self.category_id.account_asset_id:
            raise UserError(_('Сонгосон хөрөнгийн ангилалд Хөрөнгийн данс тохируулаагүй байна.'))

        assets = self.env['account.asset.asset']
        for line in self.line_ids:
            line._check_quantity()
            move = line._create_and_validate_move(self)
            asset = line._create_asset(self, move)
            assets |= asset

        return {
            'name': _('Хөрөнгө'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.asset.asset',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', assets.ids)],
        }


class StockToAssetWizardLine(models.TransientModel):
    _name = 'stock.to.asset.wizard.line'
    _description = 'Агуулахын барааг хөрөнгөд шилжүүлэх мөр'

    wizard_id = fields.Many2one('stock.to.asset.wizard', required=True, ondelete='cascade')
    product_id = fields.Many2one(
        'product.product', string='Бараа', required=True,
        domain=[('type', '=', 'product')])
    available_qty = fields.Float(string='Боломжит үлдэгдэл', compute='_compute_available_qty')
    quantity = fields.Float(string='Шилжүүлэх тоо хэмжээ', required=True, default=1.0)
    asset_name = fields.Char(string='Хөрөнгийн нэр', required=True)

    @api.depends('product_id', 'wizard_id.location_id')
    def _compute_available_qty(self):
        for line in self:
            if line.product_id and line.wizard_id.location_id:
                line.available_qty = self.env['stock.quant']._get_available_quantity(
                    line.product_id, line.wizard_id.location_id)
            else:
                line.available_qty = 0.0

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id and not self.asset_name:
            self.asset_name = self.product_id.display_name

    def _check_quantity(self):
        self.ensure_one()
        if float_is_zero(self.quantity, precision_rounding=self.product_id.uom_id.rounding) or self.quantity < 0:
            raise UserError(_('%s барааны тоо хэмжээ 0-ээс их байх ёстой.') % self.product_id.display_name)
        if float_compare(self.quantity, self.available_qty, precision_rounding=self.product_id.uom_id.rounding) > 0:
            raise UserError(_(
                '%(product)s барааны боломжит үлдэгдэл (%(available)s) хүрэлцэхгүй байна.'
            ) % {'product': self.product_id.display_name, 'available': self.available_qty})
        if self.product_id.valuation != 'real_time':
            raise UserError(_(
                '%s бараа автомат нөөцийн үнэлгээгүй (үнэлгээ бодит цагийн бус) тул шууд хөрөнгөд шилжүүлэх боломжгүй.'
            ) % self.product_id.display_name)

    def _create_and_validate_move(self, wizard):
        self.ensure_one()
        move_vals = {
            'name': self.asset_name,
            'origin': _('Хөрөнгөд шилжүүлэх'),
            'company_id': wizard.company_id.id,
            'product_id': self.product_id.id,
            'product_uom': self.product_id.uom_id.id,
            'state': 'draft',
            'location_id': wizard.location_id.id,
            'location_dest_id': wizard.asset_dest_location_id.id,
            'date': wizard.date,
            'move_line_ids': [(0, 0, {
                'product_id': self.product_id.id,
                'product_uom_id': self.product_id.uom_id.id,
                'quantity': self.quantity,
                'location_id': wizard.location_id.id,
                'location_dest_id': wizard.asset_dest_location_id.id,
            })],
            'picked': True,
        }
        move = self.env['stock.move'].create(move_vals)
        move.with_context(
            force_stock_dest_account_id=wizard.category_id.account_asset_id.id,
        )._action_done()
        return move

    def _create_asset(self, wizard, move):
        self.ensure_one()
        svl = move.stock_valuation_layer_ids[:1]
        value = abs(svl.value) if svl else self.quantity * self.product_id.standard_price

        vals = {
            'name': self.asset_name,
            'category_id': wizard.category_id.id,
            'value': value,
            'date': wizard.date,
            'note': wizard.note,
            'company_id': wizard.company_id.id,
            'product_id': self.product_id.id,
            'uom_id': self.product_id.uom_id.id,
            'asset_qty': self.quantity,
            'stock_move_id': move.id,
        }
        changed_vals = self.env['account.asset.asset'].onchange_category_id_values(wizard.category_id.id)
        vals.update(changed_vals['value'])
        asset = self.env['account.asset.asset'].create(vals)
        if wizard.category_id.open_asset:
            if asset.date_first_depreciation == 'manual':
                asset.first_depreciation_manual_date = asset.date
            asset.validate()
        return asset
