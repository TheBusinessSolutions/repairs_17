import logging

from odoo import api, fields, models
from odoo.tools.float_utils import float_compare, float_is_zero

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    repair_invoiceable = fields.Boolean(
        string="Invoiceable",
        default=True,
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

        _logger.warning("==== REPAIR SYNC MOVES ====")

        for move in moves:
            _logger.warning(
                "MOVE %s | product=%s | qty=%s | repair=%s | so=%s",
                move.id,
                move.product_id.display_name,
                move.product_uom_qty,
                move.repair_id.name,
                move.repair_id.sale_order_id.name,
            )

        if not moves:
            _logger.warning("NO MOVES TO SYNC")
            return True

        result = super()._create_repair_sale_order_line()

        for move in moves:
            _logger.warning(
                "AFTER SYNC move=%s sale_line=%s",
                move.id,
                move.sale_line_id.id,
            )

        return result