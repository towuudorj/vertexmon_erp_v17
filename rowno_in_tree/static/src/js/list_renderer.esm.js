/* @odoo-module */

import {ListRenderer} from "@web/views/list/list_renderer";
import {patch} from "@web/core/utils/patch";

patch(ListRenderer.prototype, {
    freezeColumnWidths() {
        const table = this.tableRef.el;
        // Толгой мөргүй (thead > tr байхгүй) хүснэгт дээр унахгүй байх
        const headerRow = table && table.querySelector(":scope > thead > tr");
        if (headerRow && !headerRow.querySelector(":scope > th.o_list_row_count_sheliya")) {
            // Тогтмол нарийн өргөн: хувиар (4%) өгвөл өргөн хүснэгтэд дугаарын багана хэт өргөсдөг
            const th = document.createElement("th");
            th.className = "o_list_row_number_header o_list_row_count_sheliya";
            th.style.cssText = "width: 40px; min-width: 40px; max-width: 40px;";
            th.textContent = "###";
            headerRow.prepend(th);
        }
        return super.freezeColumnWidths();
    },

    /**
     * Odoo-гийн setDefaultColumnWidths багана бүрийн өргөнийг th:nth-child(i + offset)-оор
     * онооно. Дээр нэмсэн "###" багана эхэнд орсноор бүх өргөн нэг багана хойш шилжиж
     * (жишээ нь handle баганын 33px дугаарын баганад, дараагийн баганын өргөн handle-д очих)
     * байсан тул offset-ийг нэгээр нэмж засна.
     */
    setDefaultColumnWidths() {
        const table = this.tableRef.el;
        if (!table || !table.querySelector(":scope > thead > tr > th.o_list_row_count_sheliya")) {
            return super.setDefaultColumnWidths();
        }
        const widths = this.state.columns.map((col) => this.calculateColumnWidth(col));
        const sumOfRelativeWidths = widths
            .filter(({type}) => type === "relative")
            .reduce((sum, {value}) => sum + value, 0);
        // +1: "###" багана; +1: сонгох checkbox багана байвал
        const columnOffset = (this.hasSelectors ? 2 : 1) + 1;
        widths.forEach(({type, value}, i) => {
            const headerEl = table.querySelector(`thead th:nth-child(${i + columnOffset})`);
            if (!headerEl) {
                return;
            }
            if (type === "absolute") {
                if (this.isEmpty) {
                    headerEl.style.width = value;
                } else {
                    headerEl.style.minWidth = value;
                }
            } else if (type === "relative" && this.isEmpty) {
                headerEl.style.width = `${((value / sumOfRelativeWidths) * 100).toFixed(2)}%`;
            }
        });
    },
});
