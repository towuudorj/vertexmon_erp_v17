/** @odoo-module **/
// Зөвхөн харж шалгах жагсаалтууд: Actions цэсэнд Экспортоос бусад үйлдлийг (Move to Account, Тулгалт г.м.) харуулахгүй.
// Web client view ачаалахдаа серверт context дамжуулдаггүй тул энэ шийдлийг client талд хийсэн.
import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";

export class ReadonlyCheckListController extends ListController {
    get actionMenuItems() {
        const items = super.actionMenuItems;
        return {
            action: items.action.filter((item) => item.key === "export"),
            print: [],
        };
    }
}

registry.category("views").add("mn_readonly_check_list", {
    ...listView,
    Controller: ReadonlyCheckListController,
});
