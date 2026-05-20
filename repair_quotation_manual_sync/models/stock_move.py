from odoo import api, fields, models
from odoo.tools.float_utils import float_compare, float_is_zero


class StockMove(models.Model):
    _inherit = "stock.move"

    repair_invoiceable = fields.Boolean(
        string="Invoiceable",
        default=True,
        help="Only invoiceable products will be included in the quotation.",
    )

    repair_create_sync = fields.Boolean(
        compute="_compute_sync_flags",
    )

    repair_update_sync = fields.Boolean(
        compute="_compute_sync_flags",
    )

    is_repair_sale_confirmed = fields.Boolean(
        compute="_compute_is_repair_sale_confirmed",
    )

    @api.depends("repair_id.sale_order_id.state")
    def _compute_is_repair_sale_confirmed(self):
        for move in self:
            move.is_repair_sale_confirmed = bool(
                move.repair_id
                and move.repair_id.sale_order_id
                and move.repair_id.sale_order_id.state == "sale"
            )

    @api.depends(
        "repair_invoiceable",
        "sale_line_id",
        "product_uom_qty",
        "sale_line_id.product_uom_qty",
    )
    def _compute_sync_flags(self):
        for move in self:
            rounding = move.product_uom.rounding

            move.repair_create_sync = bool(
                move.repair_id
                and move.repair_id.sale_order_id
                and move.repair_invoiceable
                and not move.sale_line_id
                and not float_is_zero(
                    move.product_uom_qty,
                    precision_rounding=rounding,
                )
            )

            move.repair_update_sync = bool(
                move.sale_line_id
                and (
                    float_compare(
                        move.product_uom_qty,
                        move.sale_line_id.product_uom_qty,
                        precision_rounding=rounding,
                    ) != 0
                    or not move.repair_invoiceable
                )
            )

    # ---------------------------
    # MANUAL SYNC ONLY (GATED)
    # ---------------------------

    def _create_repair_sale_order_line(self):
        if not self.env.context.get("repair_lines_manual_sync"):
            return True

        moves = self.filtered("repair_create_sync")

        if not moves:
            return True

        SaleOrderLine = self.env["sale.order.line"]

        for move in moves:
            sale = move.repair_id.sale_order_id

            if not sale:
                continue

            line_vals = {
                "order_id": sale.id,
                "product_id": move.product_id.id,
                "name": move.name or move.product_id.display_name,
                "product_uom_qty": move.product_uom_qty,
                "product_uom": move.product_uom.id,
                "price_unit": move.product_id.lst_price,
            }

            so_line = SaleOrderLine.create(line_vals)
            move.sale_line_id = so_line.id

        return True

    def _update_repair_sale_order_line(self):
        if not self.env.context.get("repair_lines_manual_sync"):
            return True

        moves = self.filtered("repair_update_sync")

        for move in moves:
            if not move.sale_line_id:
                continue

            if (
                not move.repair_invoiceable
                or float_is_zero(
                    move.product_uom_qty,
                    precision_rounding=move.product_uom.rounding,
                )
            ):
                move.sale_line_id.unlink()
                move.sale_line_id = False
            else:
                move.sale_line_id.write({
                    "product_uom_qty": move.product_uom_qty,
                })

        return True