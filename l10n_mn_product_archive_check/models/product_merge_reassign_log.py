# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductMergeReassignLog(models.Model):
    """
        Барааны давхардал шилжүүлэх wizard ажиллуулах бүрт нэг лог бичлэг
        үүсгэж, аль баримтуудыг өөрчилснийг мөрчлөн хадгална (аудитад зориулав).
    """
    _name = 'product.merge.reassign.log'
    _description = 'Барааны давхардал шилжүүлсэн лог'
    _order = 'create_date desc'

    source_product_id = fields.Many2one('product.product', string=u'Хуучин/Давхардсан бараа', readonly=True)
    target_product_id = fields.Many2one('product.product', string=u'Шилжүүлсэн бараа', readonly=True)
    user_id = fields.Many2one('res.users', string=u'Гүйцэтгэсэн хэрэглэгч', readonly=True,
                               default=lambda self: self.env.user)
    date = fields.Datetime(string=u'Огноо', readonly=True, default=fields.Datetime.now)
    line_ids = fields.One2many('product.merge.reassign.log.line', 'log_id', string=u'Өөрчлөгдсөн баримтууд', readonly=True)
    line_count = fields.Integer(string=u'Баримтын тоо', compute='_compute_line_count')

    def _compute_line_count(self):
        for log in self:
            log.line_count = len(log.line_ids)


class ProductMergeReassignLogLine(models.Model):
    _name = 'product.merge.reassign.log.line'
    _description = 'Барааны давхардал шилжүүлсэн баримтын мөр'
    _order = 'create_date desc'

    log_id = fields.Many2one('product.merge.reassign.log', string=u'Лог', required=True, ondelete='cascade')
    category = fields.Char(string=u'Төрөл', readonly=True)
    document_name = fields.Char(string=u'Баримт', readonly=True)
    res_model = fields.Char(string=u'Res Model', readonly=True)
    res_id = fields.Integer(string=u'Res Id', readonly=True)
    source_product_id = fields.Many2one(related='log_id.source_product_id', string=u'Хуучин/Давхардсан бараа', store=True)
    target_product_id = fields.Many2one(related='log_id.target_product_id', string=u'Шилжүүлсэн бараа', store=True)
    date = fields.Datetime(related='log_id.date', string=u'Огноо', store=True)
    user_id = fields.Many2one(related='log_id.user_id', string=u'Гүйцэтгэсэн хэрэглэгч', store=True)

    def action_open_document(self):
        self.ensure_one()
        if not self.res_model or not self.res_id:
            return {'type': 'ir.actions.act_window_close'}
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'view_mode': 'form',
            'target': 'current',
        }
