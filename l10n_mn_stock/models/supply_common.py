# -*- coding: utf-8 -*-
"""Ажилтны хангамжийн хөдөлгөөний нэгдсэн SQL.

Үлдэгдэл, "Ажилтны хангамж" цонх, хангамжийн тайлан (ажилтнаар бүлэглэх) бүгд
энэ нэг дүрмийг ашиглана.

Мөр бүр: partner_id, product_id, move_date, issue_date, issued, closed
  issued (+): хангамжийн байрлалаас ажилтанд олгосон; шилжүүлгээр хүлээн авсан;
              хаалт (актлах) буцаагдсан; өгсөн шилжүүлэг буцаагдсан.
  closed (-): ажилтнаас хангамжийн байрлал руу буцаасан; актлагдсан;
              шилжүүлгээр өгсөн; хүлээн авсан шилжүүлэг буцаагдсан.

Буцаалтын баримт (origin_returned_move_id) дээр ажилтныг анхны баримтаас авна.
Олголт/буцаалт нь зөвхөн Харилцагч (customer) байрлалтай хөдөлгөөн; агуулах хоорондын
шилжүүлэг, нийлүүлэгчийн орлого, тооллого, transit ажилтанд хамаарахгүй.
Хадгалагч: хувь хүн, эсвэл компанийн өөрийн харилцагч (жишээ нь ажилтан гарахад
Вертексмон ХХК-д шилжүүлж, дараа нь өөр ажилтанд өгөх).
"Хангамжид тооцохгүй" сонгосон баримт болон түүний буцаалтыг алгасна.
"""


def supply_lines_sql(extra_where=''):
    """:param extra_where: нэмэлт нөхцөл (mv, sm, sp alias ашиглаж болно), жишээ нь огнооны хязгаар."""
    return f"""
        SELECT COALESCE(om.partner_id, osp.partner_id, mv.partner_id, sm.partner_id, sp.partner_id) AS partner_id,
               mv.product_id,
               mv.date::date AS move_date,
               COALESCE(sp.issue_date, mv.date::date) AS issue_date,
               CASE WHEN (COALESCE(sl.supply_location, FALSE) AND dest.usage = 'customer')
                         OR COALESCE(dest.supply_transfer_location, FALSE)
                         OR COALESCE(sl.supply_writeoff_location, FALSE)
                    THEN mv.quantity ELSE 0 END AS issued,
               CASE WHEN (sl.usage = 'customer'
                          AND (COALESCE(dest.supply_location, FALSE)
                               OR COALESCE(dest.supply_writeoff_location, FALSE)))
                         OR COALESCE(sl.supply_transfer_location, FALSE)
                    THEN mv.quantity ELSE 0 END AS closed
        FROM stock_move_line mv
        JOIN stock_move sm ON sm.id = mv.move_id
        LEFT JOIN stock_picking sp ON sp.id = sm.picking_id
        LEFT JOIN stock_move om ON om.id = sm.origin_returned_move_id
        LEFT JOIN stock_picking osp ON osp.id = om.picking_id
        JOIN stock_location sl ON sl.id = mv.location_id
        JOIN stock_location dest ON dest.id = mv.location_dest_id
        WHERE mv.state = 'done'
          AND (sl.supply_location OR dest.supply_location
               OR dest.supply_writeoff_location OR sl.supply_writeoff_location
               OR dest.supply_transfer_location OR sl.supply_transfer_location)
          AND NOT COALESCE(sp.exclude_from_supply, FALSE)
          AND NOT COALESCE(osp.exclude_from_supply, FALSE)
          {extra_where}

        UNION ALL

        -- Хангамж шилжүүлэх: өгсөн ажилтны тал (буцаалт бол эргүүлж нэмнэ)
        SELECT COALESCE(sp.supply_from_partner_id, osp.supply_from_partner_id),
               mv.product_id,
               mv.date::date,
               mv.date::date,
               CASE WHEN COALESCE(sl.supply_transfer_location, FALSE) THEN mv.quantity ELSE 0 END,
               CASE WHEN COALESCE(dest.supply_transfer_location, FALSE) THEN mv.quantity ELSE 0 END
        FROM stock_move_line mv
        JOIN stock_move sm ON sm.id = mv.move_id
        JOIN stock_picking sp ON sp.id = sm.picking_id
        LEFT JOIN stock_move om ON om.id = sm.origin_returned_move_id
        LEFT JOIN stock_picking osp ON osp.id = om.picking_id
        JOIN stock_location sl ON sl.id = mv.location_id
        JOIN stock_location dest ON dest.id = mv.location_dest_id
        WHERE mv.state = 'done'
          AND (dest.supply_transfer_location OR sl.supply_transfer_location)
          AND COALESCE(sp.supply_from_partner_id, osp.supply_from_partner_id) IS NOT NULL
          AND NOT COALESCE(sp.exclude_from_supply, FALSE)
          AND NOT COALESCE(osp.exclude_from_supply, FALSE)
          {extra_where}
    """


# Хангамж хадгалагч байж болох харилцагч: хувь хүн, эсвэл компанийн өөрийн харилцагч.
SUPPLY_HOLDER_WHERE = "(rp.is_company = FALSE OR rp.id IN (SELECT partner_id FROM res_company))"
