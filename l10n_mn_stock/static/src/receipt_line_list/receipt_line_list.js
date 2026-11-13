/** @odoo-module **/
// Бараагаар хүлээн авах жагсаалт.
// Сонголт нь мөрийн "Сонгох" талбарт хадгалагдах тул шүүлт өөрчлөгдсөн ч алга болохгүй.
// Дээд хэсэгт бүх сонгосон мөрийн (шүүлтээс үл хамааран) нийт тоо, дүнг шууд харуулна.
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { formatFloat, formatMonetary } from "@web/views/fields/formatters";
import { onWillStart, useState } from "@odoo/owl";

const LINE_MODEL = "purchase.product.receipt.wizard.line";

export class PurchaseReceiptLineListController extends ListController {
    static template = "l10n_mn_stock.PurchaseReceiptLineListView";

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.receiptState = useState({ count: 0, qty: "0.00", amounts: [] });
        onWillStart(() => this.refreshReceiptSummary());
        // Жагсаалт дахин ачаалагдах бүрт (жишээ нь "Салгах" цонх хаагдсаны дараа) нийлбэрийг шинэчилнэ
        const originalLoad = this.model.load.bind(this.model);
        this.model.load = async (...args) => {
            const result = await originalLoad(...args);
            await this.refreshReceiptSummary();
            return result;
        };
    }

    get receiptWizardId() {
        return this.props.context.receipt_wizard_id;
    }

    async refreshReceiptSummary() {
        if (!this.receiptWizardId) {
            return;
        }
        const res = await this.orm.call(LINE_MODEL, "get_receipt_summary", [this.receiptWizardId]);
        this.receiptState.count = res.count;
        this.receiptState.qty = formatFloat(res.qty, { digits: [16, 2] });
        this.receiptState.amounts = res.amounts.map(([currencyId, amount]) => ({
            key: String(currencyId),
            value: formatMonetary(amount, { currencyId }),
        }));
    }

    async onRecordSaved(record) {
        await super.onRecordSaved(...arguments);
        await this.refreshReceiptSummary();
    }

    async setSelection(selected) {
        // Засварлаж буй мөр байвал эхлээд хадгална
        if (this.model.root.editedRecord && !(await this.model.root.editedRecord.save())) {
            return;
        }
        // Одоогийн шүүлтэд (хайлт, шүүлтүүр) таарах бүх мөрийг сонгох / цуцлах
        await this.orm.call(LINE_MODEL, "set_receipt_selection", [
            this.receiptWizardId,
            this.model.root.domain,
            selected,
        ]);
        await this.model.load();
    }

    async onClickReceive() {
        // Засварлаж буй мөр байвал эхлээд хадгална
        if (this.model.root.editedRecord) {
            const saved = await this.model.root.editedRecord.save();
            if (!saved) {
                return;
            }
        }
        const action = await this.orm.call(
            "purchase.product.receipt.wizard",
            "action_open_receive_dialog",
            [[this.receiptWizardId]]
        );
        await this.actionService.doAction(action, {
            onClose: async () => {
                await this.model.load();
                await this.refreshReceiptSummary();
            },
        });
    }
}

registry.category("views").add("purchase_receipt_line_list", {
    ...listView,
    Controller: PurchaseReceiptLineListController,
    props: (genericProps, view) => ({
        ...listView.props(genericProps, view),
        // Odoo-гийн түр сонголтын checkbox-ыг хааж, хайлт/шүүлт үргэлж харагдана
        allowSelectors: false,
    }),
});
