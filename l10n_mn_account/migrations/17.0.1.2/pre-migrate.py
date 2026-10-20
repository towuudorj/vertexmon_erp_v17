# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)

OLD_REL = 'account_move_purchase_order_rel'
NEW_REL = 'account_move_po_ids_rel'


def migrate(cr, version):
    """account.move.po_ids-ийг purchase.order.invoice_ids-тэй хуваалцдаг байсан хүснэгтээс
    тусдаа хүснэгт рүү шилжүүлнэ.

    Хүснэгтийг ORM-оос өмнө үүсгэснээр шинэ stored compute талбарыг бүх нэхэмжлэл дээр
    дахин тооцоолохгүй. Одоо харагдаж буй холбоосыг хуулж, PO-ийн invoice_ids дахин
    тооцоологдоход устсан холбоосыг чаттерын сүүлийн "Баримтын дугаар" бичлэгээс сэргээнэ.
    """
    cr.execute("SELECT 1 FROM information_schema.tables WHERE table_name = %s", [NEW_REL])
    if cr.fetchone():
        return

    cr.execute(f"""
        CREATE TABLE {NEW_REL} (
            move_id INTEGER NOT NULL,
            purchase_order_id INTEGER NOT NULL,
            PRIMARY KEY (move_id, purchase_order_id)
        );
        COMMENT ON TABLE {NEW_REL} IS 'RELATION BETWEEN account_move AND purchase_order';
        CREATE INDEX ON {NEW_REL} (purchase_order_id, move_id);
    """)

    cr.execute(f"""
        INSERT INTO {NEW_REL} (move_id, purchase_order_id)
        SELECT account_move_id, purchase_order_id FROM {OLD_REL}
        ON CONFLICT DO NOTHING
    """)
    _logger.info("po_ids: copied %s links from %s", cr.rowcount, OLD_REL)

    # Чаттер: <p><strong>Баримтын дугаар: </strong> (P001) -&gt; (P001, P002 (ref))</p>
    cr.execute(f"""
        WITH last_msg AS (
            SELECT DISTINCT ON (res_id) res_id, body
              FROM mail_message
             WHERE model = 'account.move'
               AND body LIKE '%Баримтын дугаар:%'
             ORDER BY res_id, date DESC, id DESC
        ), names AS (
            SELECT res_id, split_part(trim(token), ' ', 1) AS po_name
              FROM last_msg,
                   regexp_split_to_table(substring(body FROM '-&gt; \\((.*)\\)</p>'), ',') AS token
        )
        INSERT INTO {NEW_REL} (move_id, purchase_order_id)
        SELECT DISTINCT n.res_id, po.id
          FROM names n
          JOIN account_move m ON m.id = n.res_id
          JOIN purchase_order po ON po.name = n.po_name
        ON CONFLICT DO NOTHING
        RETURNING move_id
    """)
    restored = cr.fetchall()
    _logger.info("po_ids: restored %s links on %s moves from chatter",
                 len(restored), len({r[0] for r in restored}))

    # Хуучин хүснэгтийг энэ модульд бүртгэсэн бичлэгийг арилгана (purchase модулийнх хэвээр)
    cr.execute("""
        DELETE FROM ir_model_relation
         WHERE name = %s
           AND module = (SELECT id FROM ir_module_module WHERE name = 'l10n_mn_account')
    """, [OLD_REL])
