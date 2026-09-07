# ©  2015-2022 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

import io
import json

import xlsxwriter

from odoo import _, api, fields, models
from odoo.tools import date_utils
from odoo.tools.safe_eval import safe_eval


class StockInventory(models.Model):
    _inherit = "stock.inventory"

    name = fields.Char(string="Name", copy=False)
    date = fields.Datetime(
        string="Inventory Date",
        required=True,
    )
    note = fields.Text(string="Note")
    filterbyrack = fields.Char("Rack")

    def _get_inventory_lines_values(self):
        lines = super()._get_inventory_lines_values()
        for line in lines:
            product = self.env["product.product"].browse(line["product_id"])
            price = product.standard_price
            line["standard_price"] = price

        for line in lines:
            line["is_ok"] = False
        return lines

    def action_check(self):
        for inventory in self:
            date = inventory.date
            values = {"date": date}
            if inventory.name in ("/", _("New")):
                sequence = self.env.ref("deltatech_stock_inventory.sequence_inventory_doc")
                if sequence:
                    values["name"] = sequence.next_by_id()

            inventory.write(values)
            # for line in inventory.line_ids:
            #     line.write({'standard_price': line.get_price()})
        res = super().action_check()
        return res

    def _action_done(self):
        super()._action_done()
        for inv in self:
            for move in inv.move_ids:
                if move.date != inv.date:
                    move.write({"date": inv.date})
        return True

    def action_remove_not_ok(self):
        for line in self.line_ids:
            if not line.is_ok:
                line.unlink()

    def action_new_for_not_ok(self):
        new_inv = self.copy({"line_ids": False, "state": "confirm"})
        for line in self.line_ids:
            if not line.is_ok:
                line.write({"inventory_id": new_inv.id})

    def action_print_inventory_xlsx(self):
        self.ensure_one()
        return {
            "type": "ir.actions.report",
            "report_type": "xlsx",
            "data": {
                "model": "stock.inventory",
                "output_format": "xlsx",
                "options": json.dumps({"inventory_id": self.id}, default=date_utils.json_default),
                "report_name": "report_inventory_position",
            },
        }

    def get_xlsx_report(self, data, response):
        inventory = self.browse(data["inventory_id"])

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet()

        title_fmt = workbook.add_format({"align": "center", "font_size": 16, "bold": True})
        info_fmt = workbook.add_format({"align": "left", "font_size": 11, "bold": True})
        head_fmt = workbook.add_format(
            {"align": "center", "border": 1, "font_size": 10, "bold": True, "text_wrap": True, "bg_color": "#EEEEEE"}
        )
        text_fmt = workbook.add_format({"align": "left", "border": 1, "font_size": 10, "text_wrap": True})
        num_fmt = workbook.add_format(
            {"align": "right", "border": 1, "font_size": 10, "num_format": "#,##0.00"}
        )
        total_label_fmt = workbook.add_format({"align": "left", "border": 1, "font_size": 10, "bold": True})
        total_num_fmt = workbook.add_format(
            {"align": "right", "border": 1, "font_size": 10, "bold": True, "num_format": "#,##0.00"}
        )

        sheet.set_column(0, 0, 5)
        sheet.set_column(1, 1, 30)
        sheet.set_column(2, 4, 16)
        sheet.set_column(5, 8, 14)

        rowx = 0
        sheet.merge_range(rowx, 0, rowx, 8, _("Бараа материалын тооллого"), title_fmt)
        rowx += 2

        headers = [
            _("№"),
            _("Бараа"),
            _("Бүртгэлтэй тоо хэмжээ"),
            _("Зөрүү тоо хэмжээ"),
            _("Бодит тоо хэмжээ"),
            _("Хэмжих нэгж"),
            _("Дүн"),
            _("Илүү дүн"),
            _("Дутуу дүн"),
        ]

        locations = inventory.line_ids.mapped("location_id")
        for location in locations:
            sheet.write(rowx, 0, _("Тооллого: %s") % (inventory.name or ""), info_fmt)
            date_str = "%s - %s" % (
                inventory.start_date.strftime("%Y/%m/%d") if inventory.start_date else "",
                inventory.date.strftime("%Y/%m/%d") if inventory.date else "",
            )
            sheet.write(rowx, 2, _("Огноо: %s") % date_str, info_fmt)
            sheet.write(rowx, 5, _("Байршил: %s") % location.display_name, info_fmt)
            rowx += 1

            for col, label in enumerate(headers):
                sheet.write(rowx, col, label, head_fmt)
            rowx += 1

            total_plus = total_minus = total_amount = total_before = 0.0
            counter = 0
            lines = inventory.line_ids.filtered(lambda l: l.location_id == location)
            for line in lines:
                if not (line.theoretical_qty > 0 or line.product_qty > 0):
                    continue
                counter += 1
                price = line.standard_price or line.product_id.standard_price
                diff = line.product_qty - line.theoretical_qty
                amount = round(line.product_qty * price, 2) if line.state == "done" else 0.0
                total_amount += line.product_qty * price
                total_before += line.theoretical_qty * price
                plus_amount = diff * price if diff > 0 else 0.0
                minus_amount = -diff * price if diff < 0 else 0.0
                total_plus += plus_amount
                total_minus += minus_amount

                sheet.write(rowx, 0, counter, text_fmt)
                sheet.write(rowx, 1, line.product_id.display_name or "", text_fmt)
                sheet.write(rowx, 2, line.theoretical_qty, num_fmt)
                sheet.write(rowx, 3, round(diff) if diff else "", num_fmt)
                sheet.write(rowx, 4, line.product_qty if line.state == "done" else "", num_fmt)
                sheet.write(rowx, 5, line.product_uom_id.name or "", text_fmt)
                sheet.write(rowx, 6, amount, num_fmt)
                sheet.write(rowx, 7, round(plus_amount, 2) if diff > 0 else "", num_fmt)
                sheet.write(rowx, 8, round(minus_amount, 2) if diff < 0 else "", num_fmt)
                rowx += 1

            sheet.write(rowx, 0, _("Нийт дүн"), total_label_fmt)
            for col in (1, 2, 3, 4):
                sheet.write(rowx, col, "", total_label_fmt)
            sheet.write(rowx, 5, _("Өмнөх:"), total_label_fmt)
            sheet.write(rowx, 6, round(total_before, 2), total_num_fmt)
            sheet.write(rowx, 7, round(total_plus, 2), total_num_fmt)
            sheet.write(rowx, 8, round(total_minus, 2), total_num_fmt)
            rowx += 1
            sheet.write(rowx, 5, _("Дараах:"), total_label_fmt)
            sheet.write(rowx, 6, round(total_before + total_plus - total_minus, 2), total_num_fmt)
            rowx += 2

        if inventory.note:
            sheet.write(rowx, 0, inventory.note, workbook.add_format({"text_wrap": True}))
            rowx += 2

        rowx += 1
        signature_fmt = workbook.add_format({"align": "right"})
        for label in (
            _("Тооллого хийсэн Бараа материалын нярав"),
            _("Тооллого хянасан Бараа материалын нягтлан"),
            _("Тооллого хянасан Ахлах нягтлан"),
            _("Тооллого хянасан СЭЗахирал"),
        ):
            sheet.merge_range(rowx, 0, rowx, 8, "%s: ................................................../..................................../" % label, signature_fmt)
            rowx += 1

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()


class StockInventoryLine(models.Model):
    _inherit = "stock.inventory.line"
    _order = "inventory_id, location_id, categ_id, product_id, prod_lot_id"

    categ_id = fields.Many2one("product.category", string="Category", related="product_id.categ_id", store=True)
    standard_price = fields.Float(string="Price")
    difference_price = fields.Float(string="Difference Price", compute='_compute_difference_price', store=True)
    loc_rack = fields.Char("Rack Name", size=16, compute="_compute_loc", store=True)
    loc_row = fields.Char("Row Name", size=16, compute="_compute_loc", store=True)
    loc_case = fields.Char("Case Name", size=16, compute="_compute_loc", store=True)
    is_ok = fields.Boolean("Is Ok", default=True)

    @api.depends("location_id", "product_id")
    def _compute_loc(self):
        for line in self:
            warehouse = line.location_id.warehouse_id
            product = line.product_id.with_context(warehouse=warehouse.id)
            line.loc_rack = product.loc_rack
            line.loc_row = product.loc_row
            line.loc_case = product.loc_case

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if "standard_price" not in values:
                if "product_id" in values:
                    product = self.env["product.product"].browse(values["product_id"])
                    values["standard_price"] = product.standard_price
                elif self.env.context.get("default_product_id", False):
                    product = self.env["product.product"].browse(self.env.context.get("default_product_id", False))
                    values["standard_price"] = product.standard_price
        return super().create(vals_list)

    @api.onchange(
        "product_id",
        "location_id",
        "product_uom_id",
        "prod_lot_id",
        "partner_id",
        "package_id",
    )
    def _onchange_quantity_context(self):
        res = super()._onchange_quantity_context()
        self.standard_price = self.get_price()
        return res

    # todo: nu sunt sigur ca e bine ??? e posibil ca self sa fie gol

    @api.model
    def get_price(self):
        price = self.product_id.standard_price
        # if self.product_id.cost_method == 'fifo':
        #     if self.theoretical_qty:
        #         price = self.product_id.stock_value / self.theoretical_qty
        #         #price = self.product_id.with_context(to_date=self.accounting_date).stock_value / self.theoretical_qty
        return price

    def _generate_moves(self):
        config_parameter = self.env["ir.config_parameter"].sudo()
        use_inventory_price = config_parameter.get_param(key="stock.use_inventory_price", default="True")
        use_inventory_price = safe_eval(use_inventory_price)

        # actualizare pret in produs
        for inventory_line in self:
            if (
                not inventory_line.theoretical_qty
                or (
                    inventory_line.product_id.cost_method == "fifo"
                    or inventory_line.product_id.cost_method == "average"
                )
                and use_inventory_price
            ):
                inventory_line.product_id.sudo().with_context(disable_auto_svl=True).write(
                    {"standard_price": inventory_line.standard_price}
                )
        moves = super()._generate_moves()
        # self.set_last_last_inventory()
        return moves

    # def set_last_last_inventory(self):
    #     for inventory_line in self:
    #         prod_last_inventory_date = inventory_line.product_id.last_inventory_date
    #         product_tmpl_inventory_date = inventory_line.product_id.product_tmpl_id.last_inventory_date
    #         inventory_date = inventory_line.inventory_id.date.date()
    #         if not prod_last_inventory_date or prod_last_inventory_date < inventory_date:
    #             inventory_line.product_id.write(
    #                 {"last_inventory_date": inventory_date, "last_inventory_id": inventory_line.inventory_id.id}
    #             )
    #             if not product_tmpl_inventory_date or product_tmpl_inventory_date < inventory_date:
    #                 inventory_line.product_id.product_tmpl_id.write(
    #                     {"last_inventory_date": inventory_date, "last_inventory_id": inventory_line.inventory_id.id}
    #                 )

    @api.onchange("product_qty")
    def onchange_product_qty(self):
        self.is_ok = True

    @api.depends('standard_price', 'difference_qty')
    def _compute_difference_price(self):
        for obj in self:
            obj.difference_price = obj.standard_price * obj.difference_qty