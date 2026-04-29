from odoo import _, api, fields, models
from markupsafe import Markup

from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare


class StockMoveUpdate(models.TransientModel):
    _name = 'stock.move.update'
    _description = 'Stock Move Update'

    @api.model
    def default_get(self, fields_list):
        res = super(StockMoveUpdate, self).default_get(fields_list)
        context = self.env.context
        move_id = context.get('active_id')
        if 'move_id' in fields_list:
            res['move_id'] = [(4, move_id)]
        return res

    move_id = fields.Many2many('stock.move', 'move_update_main_line', 'move_update_wizard_id', 'move_id')
    new_line_ids = fields.Many2many('stock.move', 'move_update_new_line', 'move_update_wizard_id', 'new_move_id')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    def _run_product_onchange(self, record):
        for method_name in ('_onchange_product_id', 'product_id_change'):
            onchange = getattr(record, method_name, None)
            if onchange:
                try:
                    onchange()
                except TypeError:
                    continue

    def _run_project_line_onchange(self, record):
        for method_name in ('onchange_product_id', 'onchange_product_qty'):
            onchange = getattr(record, method_name, None)
            if onchange:
                onchange()

    def _prepare_purchase_order_line_vals(self, purchase_line, new_product, quantity):
        purchase_line_vals = purchase_line.copy_data()[0]
        for field_name in (
                'move_ids', 'move_dest_ids', 'move_source_ids', 'invoice_lines',
                'qty_received', 'qty_invoiced', 'qty_to_invoice'):
            purchase_line_vals.pop(field_name, None)
        purchase_order_line = self.env['purchase.order.line'].new(purchase_line_vals)
        purchase_order_line.order_id = purchase_line.order_id
        purchase_order_line.product_id = new_product
        if 'product_uom' in purchase_order_line._fields and new_product.uom_po_id:
            purchase_order_line.product_uom = new_product.uom_po_id
        if 'product_qty' in purchase_order_line._fields:
            purchase_order_line.product_qty = quantity
        self._run_product_onchange(purchase_order_line)
        purchase_order_line.order_id = purchase_line.order_id
        purchase_order_line.product_id = new_product
        if 'product_uom' in purchase_order_line._fields and new_product.uom_po_id:
            purchase_order_line.product_uom = new_product.uom_po_id
        if 'product_qty' in purchase_order_line._fields:
            purchase_order_line.product_qty = quantity
        purchase_order_line_vals = purchase_order_line._convert_to_write(purchase_order_line._cache)
        for field_name in (
                'move_ids', 'move_dest_ids', 'move_source_ids', 'invoice_lines',
                'qty_received', 'qty_invoiced', 'qty_to_invoice'):
            purchase_order_line_vals.pop(field_name, None)
        purchase_order_line_vals.update({
            'order_id': purchase_line.order_id.id,
            'product_id': new_product.id,
            'product_qty': quantity,
            'product_uom': new_product.uom_po_id.id if new_product.uom_po_id else False,
        })
        return purchase_order_line_vals

    def _prepare_purchase_stock_move_vals(self, wizard_line, purchase_line_id):
        return {
            'product_uom_qty': wizard_line.quantity,
            'quantity': wizard_line.quantity,
            'purchase_line_id': purchase_line_id.id if purchase_line_id else False,
            'product_uom': wizard_line.product_uom.id if wizard_line.product_uom else wizard_line.product_id.uom_po_id.id,
            'description_picking': wizard_line.description_picking or wizard_line.product_id.display_name,
            'name': wizard_line.name or wizard_line.product_id.display_name,
            'date': wizard_line.date,
            'date_deadline': wizard_line.date_deadline,
            'sale_prices': wizard_line.sale_prices,
        }

    def _prepare_sale_order_line_vals(self, sale_order_line, new_product, quantity):
        sale_line_vals = sale_order_line.copy_data()[0]
        for field_name in (
                'move_ids', 'invoice_lines', 'qty_delivered', 'qty_invoiced',
                'qty_to_invoice', 'untaxed_amount_invoiced', 'untaxed_amount_to_invoice'):
            sale_line_vals.pop(field_name, None)
        new_sale_order_line = self.env['sale.order.line'].new(sale_line_vals)
        new_sale_order_line.order_id = sale_order_line.order_id
        new_sale_order_line.product_id = new_product
        if 'product_uom' in new_sale_order_line._fields and new_product.uom_id:
            new_sale_order_line.product_uom = new_product.uom_id
        new_sale_order_line.product_uom_qty = quantity
        self._run_product_onchange(new_sale_order_line)
        new_sale_order_line.order_id = sale_order_line.order_id
        new_sale_order_line.product_id = new_product
        if 'product_uom' in new_sale_order_line._fields and new_product.uom_id:
            new_sale_order_line.product_uom = new_product.uom_id
        new_sale_order_line.product_uom_qty = quantity
        sale_order_line_vals = new_sale_order_line._convert_to_write(new_sale_order_line._cache)
        for field_name in (
                'move_ids', 'invoice_lines', 'qty_delivered', 'qty_invoiced',
                'qty_to_invoice', 'untaxed_amount_invoiced', 'untaxed_amount_to_invoice'):
            sale_order_line_vals.pop(field_name, None)
        sale_order_line_vals.update({
            'order_id': sale_order_line.order_id.id,
            'product_id': new_product.id,
            'product_uom_qty': quantity,
            'product_uom': new_product.uom_id.id if new_product.uom_id else False,
        })
        return sale_order_line_vals

    def _prepare_sale_stock_move_vals(self, source_move, wizard_line, sale_order_line=False):
        move_vals = source_move.copy_data()[0]
        move_vals.update({
            'location_id': source_move.location_id.id if source_move.location_id else False,
            'location_dest_id': source_move.location_dest_id.id if source_move.location_dest_id else False,
            'description_picking': wizard_line.description_picking or wizard_line.product_id.display_name,
            'product_uom': wizard_line.product_uom.id if wizard_line.product_uom else wizard_line.product_id.uom_id.id,
            'date': source_move.date,
            'date_deadline': source_move.date_deadline,
            'name': wizard_line.name or wizard_line.product_id.display_name,
            'product_uom_qty': wizard_line.quantity,
            'quantity': wizard_line.quantity,
            'product_id': wizard_line.product_id.id,
            'company_id': source_move.company_id.id if source_move.company_id else False,
            'sequence': source_move.sequence + 1 if source_move.sequence else 0,
            'partner_id': source_move.partner_id.id if source_move.partner_id else False,
            'scrap_id': source_move.scrap_id.id if source_move.scrap_id else False,
            'group_id': source_move.group_id.id if source_move.group_id else False,
            'rule_id': source_move.rule_id.id if source_move.rule_id else False,
            'picking_type_id': source_move.picking_type_id.id if source_move.picking_type_id else False,
            'restrict_partner_id': source_move.restrict_partner_id.id if source_move.restrict_partner_id else False,
            'warehouse_id': source_move.warehouse_id.id if source_move.warehouse_id else False,
            'package_level_id': source_move.package_level_id.id if source_move.package_level_id else False,
            'state': source_move.state,
            'origin': source_move.origin,
            'procure_method': source_move.procure_method,
            'reference': source_move.reference,
            'reservation_date': source_move.reservation_date,
            'price_unit': source_move.price_unit,
            'sale_prices': source_move.sale_prices,
            'inventory_id': source_move.inventory_id.id if source_move.inventory_id else False,
            'picking_id': source_move.picking_id.id,
            'sale_line_id': sale_order_line.id if sale_order_line else False,
        })
        return move_vals

    def _prepare_project_product_line_vals(self, project_line, new_product, quantity):
        project_line_vals = project_line.copy_data()[0]
        for field_name in (
                'qty_available', 'qty_delivered', 'price_total', 'cost_total', 'delivery_cost',
                'qty_available_cost', 'last_qty', 'change_cost', 'picking_ids'):
            project_line_vals.pop(field_name, None)
        new_project_line = self.env['project.products.line'].new(project_line_vals)
        new_project_line.project_id = project_line.project_id
        new_project_line.product_id = new_product
        new_project_line.product_qty = quantity
        self._run_project_line_onchange(new_project_line)
        new_project_line.project_id = project_line.project_id
        new_project_line.product_id = new_product
        new_project_line.product_qty = quantity
        project_line_vals = new_project_line._convert_to_write(new_project_line._cache)
        for field_name in (
                'qty_available', 'qty_delivered', 'price_total', 'cost_total', 'delivery_cost',
                'qty_available_cost', 'last_qty', 'change_cost', 'picking_ids'):
            project_line_vals.pop(field_name, None)
        project_line_vals.update({
            'project_id': project_line.project_id.id,
            'product_id': new_product.id,
            'product_qty': quantity,
            'price_unit': project_line.price_unit if project_line else 0,
            'product_uom': (new_project_line.product_uom or new_product.uom_po_id or new_product.uom_id).id,
        })
        return project_line_vals

    def _prepare_project_stock_move_vals(self, source_move, wizard_line):
        move_vals = source_move.copy_data()[0]
        move_vals.update({
            'location_id': source_move.location_id.id if source_move.location_id else False,
            'location_dest_id': source_move.location_dest_id.id if source_move.location_dest_id else False,
            'description_picking': wizard_line.description_picking or wizard_line.product_id.display_name,
            'product_uom': wizard_line.product_uom.id if wizard_line.product_uom else wizard_line.product_id.uom_id.id,
            'date': source_move.date,
            'date_deadline': source_move.date_deadline,
            'name': wizard_line.name or wizard_line.product_id.display_name,
            'product_uom_qty': wizard_line.quantity,
            'quantity': wizard_line.quantity,
            'product_id': wizard_line.product_id.id,
            'company_id': source_move.company_id.id if source_move.company_id else False,
            'sequence': source_move.sequence + 1 if source_move.sequence else 0,
            'partner_id': source_move.partner_id.id if source_move.partner_id else False,
            'scrap_id': source_move.scrap_id.id if source_move.scrap_id else False,
            'group_id': source_move.group_id.id if source_move.group_id else False,
            'rule_id': source_move.rule_id.id if source_move.rule_id else False,
            'picking_type_id': source_move.picking_type_id.id if source_move.picking_type_id else False,
            'restrict_partner_id': source_move.restrict_partner_id.id if source_move.restrict_partner_id else False,
            'warehouse_id': source_move.warehouse_id.id if source_move.warehouse_id else False,
            'package_level_id': source_move.package_level_id.id if source_move.package_level_id else False,
            'state': source_move.state,
            'origin': source_move.origin,
            'procure_method': source_move.procure_method,
            'reference': source_move.reference,
            'reservation_date': source_move.reservation_date,
            'price_unit': source_move.price_unit,
            'sale_prices': source_move.sale_prices,
            'inventory_id': source_move.inventory_id.id if source_move.inventory_id else False,
            'picking_id': source_move.picking_id.id,
            'sale_line_id': False,
            'purchase_line_id': False,
        })
        return move_vals

    def _get_related_crm_lead(self, move, purchase_id=False):
        purchase_order = purchase_id or move.purchase_line_id.order_id
        if purchase_order and purchase_order.requisition_id and purchase_order.requisition_id.crm_lead_id:
            return purchase_order.requisition_id.crm_lead_id
        return self.env['crm.lead']

    def _get_project_picking_ids(self, project):
        if not project:
            return self.env['stock.picking']
        return project.picking_ids.filtered(
            lambda picking: not getattr(picking, 'is_dropship', False) and picking.state not in ['cancel', 'done']
        )

    def _get_related_sale_move(self, move, purchase_id=False):
        sale_moves = (
            move.move_dest_ids
            | move.purchase_line_id.move_dest_ids
            | move.move_dest_ids.move_dest_ids
        ).filtered(lambda line: line.sale_line_id and line.state not in ['cancel', 'done'])
        same_product_sale_moves = sale_moves.filtered(lambda line: line.product_id.id == move.product_id.id)
        if len(same_product_sale_moves) == 1:
            return same_product_sale_moves[:1]

        lead_id = self._get_related_crm_lead(move, purchase_id)
        if lead_id:
            sale_orders = lead_id.order_ids.filtered_domain(lead_id._get_lead_sale_order_domain())
            if sale_orders and len(sale_orders) == 1:
                sale_picking_ids = sale_orders.picking_ids.filtered(lambda p: p.state not in ['cancel', 'done'])
                same_product_lines = sale_picking_ids.mapped('move_ids_without_package').filtered(
                    lambda line: line.product_id.id == move.product_id.id
                )
                if len(same_product_lines) == 1:
                    return same_product_lines[:1]
        return self.env['stock.move']

    def _get_related_project_records(self, move, purchase_id=False):
        project = self.env['project.project']
        lead_id = self._get_related_crm_lead(move, purchase_id)
        if lead_id and lead_id.crm_type == 'stock' and lead_id.project_id:
            project = lead_id.project_id
        if not project:
            return project, self.env['project.products.line'], self.env['stock.move']
        project_product_line = project.products_line.filtered(lambda line: line.product_id.id == move.product_id.id)[:1]
        project_picking_ids = self._get_project_picking_ids(project)
        project_stock_move = project_picking_ids.mapped('move_ids_without_package').filtered(
            lambda line: line.product_id.id == move.product_id.id
        )[:1]
        return project, project_product_line, project_stock_move

    def send_update_mail(self, purchase_name, html, user_ids=False, ):
        emails = []
        if user_ids:
            emails = []
            for user in user_ids:
                if user.employee_id:
                    emails.append(user.employee_id.work_email)
                else:
                    if user.partner_id:
                        emails.append(user.partner_id.email)
        if emails:
            picking = self.move_id.picking_id
            picking_url = f'/web#id={picking.id}&model=stock.picking&view_type=form'

            self.env['mail.mail'].create({
                'email_to': ', '.join(emails),
                'subject': u'%s хүлээн авах баримтын мөрд өөрчлөлт орлоо' % picking.name,
                'body_html': html + f'</br> Дэлгэрэнгүй мэдээллийг харна уу. <a href="{picking_url}">{picking.name}</a>',
            }).send()

    def update(self):
        mail_users = self.env['res.users']
        purchase_name = False
        move = self.move_id[:1]

        rounding = move.product_uom.rounding or move.product_id.uom_id.rounding or 0.01
        original_qty = move.quantity
        if not self.new_line_ids:
            raise ValidationError(_('Шинэ мөр оруулсны дараа хадгална уу.'))

        if any(float_compare(line.quantity, 0.0, precision_rounding=rounding) <= 0 for line in self.new_line_ids):
            raise ValidationError(_('Тоо хэмжээ 0-ээс их байх ёстой.'))

        total_new_qty = sum(self.new_line_ids.mapped('quantity'))
        if float_compare(total_new_qty, original_qty, precision_rounding=rounding) != 0:
            raise ValidationError(_('Салгасан мөрүүдийн нийт тоо нь эх мөрийн тоотой тэнцүү байх ёстой.'))

        picking_id = move.picking_id
        purchase_id = self.env['purchase.order'].search([
            ('partner_id', '=', picking_id.partner_id.id),
            ('name', '=', picking_id.origin),
            ('picking_type_id', '=', picking_id.picking_type_id.id)
        ], limit=1)
        if purchase_id.requisition_id:
            mail_users |= purchase_id.requisition_id.user_id
            mail_users |= purchase_id.requisition_id.purchase_user_id
            purchase_name = purchase_id.name

        same_product_new_lines = self.new_line_ids.filtered(lambda line: line.product_id == move.product_id)
        same_product_qty = sum(same_product_new_lines.mapped('quantity'))
        quantity_delta = same_product_qty - original_qty

        move.sudo().write({
            'quantity': same_product_qty,
            'product_uom_qty': same_product_qty,
        })
        if move.purchase_line_id:
            move.purchase_line_id.with_context(
                skip_split_purchase_picking=True
            ).sudo().write({
                'product_qty': move.purchase_line_id.product_qty + quantity_delta,
            })

        message_body = f'<ul><li>{move.product_id.name}:{original_qty}</li><li>→</li>'
        new_lines_to_unlink = self.env['stock.move']
        for new_line in self.new_line_ids:
            if move.product_id != new_line.product_id:
                purchase_line_id = False
                purchase_move_id = False
                if move.purchase_line_id:
                    purchase_order_line_vals = self._prepare_purchase_order_line_vals(
                        move.purchase_line_id, new_line.product_id, new_line.quantity
                    )
                    purchase_line_id = self.env['purchase.order.line'].with_context(
                        skip_split_purchase_picking=True
                    ).sudo().create(purchase_order_line_vals)
                    purchase_move_id = purchase_line_id.move_ids.filtered(
                        lambda line: line.picking_id == picking_id and line.state not in ['done', 'cancel']
                    )[:1]
                if purchase_move_id:
                    purchase_move_id.sudo().write(
                        self._prepare_purchase_stock_move_vals(new_line, purchase_line_id)
                    )
                    new_lines_to_unlink |= new_line
                else:
                    new_line.sudo().write({
                        'picking_id': picking_id.id,
                        'product_uom_qty': new_line.quantity,
                        'purchase_line_id': purchase_line_id.id if purchase_line_id else False,
                    })
            message_body += f'<li>{new_line.product_id.name}:{new_line.quantity}</li>'
        message_body += '</ul>'
        picking_id.message_post(author_id=self.env.user.partner_id.id,
                                body=Markup(message_body))
        if new_lines_to_unlink:
            new_lines_to_unlink.sudo().unlink()

        project_id, project_product_line, project_stock_move = self._get_related_project_records(move, purchase_id)
        if project_id:
            if quantity_delta and project_product_line:
                project_product_line.sudo().write({
                    'product_qty': project_product_line.product_qty + quantity_delta,
                })

            if quantity_delta and project_stock_move:
                project_stock_move.sudo().write({
                    'product_uom_qty': project_stock_move.product_uom_qty + quantity_delta,
                })

            for new_line in self.new_line_ids.filtered(lambda line: line.product_id != move.product_id):
                if project_product_line:
                    self.env['project.products.line'].sudo().create(
                        self._prepare_project_product_line_vals(
                            project_product_line, new_line.product_id, new_line.quantity
                        )
                    )
                if project_stock_move:
                    self.env['stock.move'].sudo().create(
                        self._prepare_project_stock_move_vals(project_stock_move, new_line)
                    )
        else:
            same_product_sale_move = self._get_related_sale_move(move, purchase_id)
            if quantity_delta and (
                    len(same_product_sale_move) != 1 or
                    float_compare(same_product_sale_move.product_uom_qty + quantity_delta, 0.0,
                                  precision_rounding=rounding) < 0):
                raise ValidationError(u'Борлуулалтын хүргэлтийн мөрөөс шалтгаалж салгах боломжгүй байна')
            if quantity_delta and same_product_sale_move:
                updated_sale_qty = same_product_sale_move.quantity + quantity_delta
                sale_message_body = (
                    f'<ul><li>{same_product_sale_move.product_id.name}:{same_product_sale_move.quantity}</li><li>→</li>'
                )
                same_product_sale_move.sudo().write({
                    'product_uom_qty': same_product_sale_move.product_uom_qty + quantity_delta,
                })
                sale_message_body += (
                    f'<li>{same_product_sale_move.product_id.name}:{updated_sale_qty}</li></ul>'
                )
                if same_product_sale_move.sale_line_id:
                    same_product_sale_move.sale_line_id.with_context(
                        skip_split_stock_rule=True
                    ).write({
                        'product_uom_qty': same_product_sale_move.sale_line_id.product_uom_qty + quantity_delta,
                    })
                same_product_sale_move.picking_id.message_post(
                    author_id=self.env.user.partner_id.id,
                    body=Markup(sale_message_body))

            source_sale_line = same_product_sale_move.sale_line_id[:1]
            if self.new_line_ids.filtered(lambda line: line.product_id != move.product_id) and not source_sale_line:
                raise ValidationError(u'Үндсэн бараатай холбоотой борлуулалтын мөр олдсонгүй.')

            for new_line in self.new_line_ids.filtered(lambda line: line.product_id != move.product_id):
                if len(same_product_sale_move) != 1:
                    raise ValidationError(u'Борлуулалтын хүргэлтийн мөрөөс шалтгаалж салгах боломжгүй байна')

                sale_picking_id = same_product_sale_move.picking_id
                sale_order_line_vals = self._prepare_sale_order_line_vals(
                    source_sale_line, new_line.product_id, new_line.quantity
                )
                sale_order_line_id = self.env['sale.order.line'].with_context(
                    skip_split_stock_rule=True
                ).sudo().create(sale_order_line_vals)
                self.env['stock.move'].sudo().create(
                    self._prepare_sale_stock_move_vals(
                        same_product_sale_move, new_line, sale_order_line_id
                    )
                )
                sale_message_body = f'<ul><li>{new_line.product_id.name}:{new_line.quantity}</li></ul>'
                sale_picking_id.message_post(
                    author_id=self.env.user.partner_id.id,
                    body=Markup(sale_message_body))
        if mail_users:
            new_lines = ''
            total_count = 0
            for new_line in self.new_line_ids:
                new_lines += '''
                <tr style="background-color:#53c988;">
                    <td>Шинэ мөр</td>
                    <td>%s</td>
                    <td>%s</td>
                </tr>''' % (new_line.product_id.name, str(new_line.quantity))
                total_count += new_line.quantity
            change_html = f"""
                <table style="width:50%;border:1px solid black;">
                    <tr>
                        <th>Төрөл</th>
                        <th>Бараа</th>
                        <th>Тоо хэмжээ</th>
                    </tr>
                    <tr style="background-color:#e06960;">
                        <td>Өмнөх мөр</td>
                        <td>{self.move_id.product_id.name}</td>
                        <td>{total_count}</td>
                    </tr>
                    {new_lines}
                </table>
            """
            self.send_update_mail(purchase_name, change_html, user_ids=mail_users)
        return {'type': 'ir.actions.act_window_close'}

    def cancel(self):
        for obj in self:
            if obj.new_line_ids:
                obj.new_line_ids.sudo().unlink()
        return {'type': 'ir.actions.act_window_close'}
