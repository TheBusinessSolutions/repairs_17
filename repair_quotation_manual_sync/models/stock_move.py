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
                move.repair_id.sale_order_id
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
                move.repair_invoiceable
                and move.repair_id
                and move.repair_id.sale_order_id
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

    def _create_repair_sale_order_line(self):
        moves = self.filtered(
            lambda m:
            m.repair_create_sync
            and m.repair_id
            and m.repair_id.sale_order_id
        )

        if not moves:
            return True

        return super(StockMove, moves)._create_repair_sale_order_line()

    def _update_repair_sale_order_line(self):
        moves = self.filtered("repair_update_sync")

        if not moves:
            return True

        super(StockMove, moves)._update_repair_sale_order_line()

        unlink_moves = moves.filtered(
            lambda m:
            m.sale_line_id
            and (
                not m.repair_invoiceable
                or float_is_zero(
                    m.product_uom_qty,
                    precision_rounding=m.product_uom.rounding,
                )
            )
        )

        if unlink_moves:
            unlink_moves._clean_repair_sale_order_line()

        return True