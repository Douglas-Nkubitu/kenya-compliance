import deprecation
import frappe

from ... import __version__
from ..doctype.doctype_names_mapping import (
    BRANCH_ID_DOCTYPE_NAME,
    ITEM_CLASSIFICATIONS_DOCTYPE_NAME,
    NOTICES_DOCTYPE_NAME,
    REGISTERED_IMPORTED_ITEM_DOCTYPE_NAME,
    REGISTERED_PURCHASES_DOCTYPE_NAME,
    REGISTERED_PURCHASES_DOCTYPE_NAME_ITEM,
    REGISTERED_STOCK_MOVEMENTS_DOCTYPE_NAME,
    SETTINGS_DOCTYPE_NAME,
    USER_DOCTYPE_NAME,
)
from ..handlers import handle_errors
from ..utils import get_curr_env_etims_settings


def on_error(
    response: dict | str,
    url: str | None = None,
    doctype: str | None = None,
    document_name: str | None = None,
) -> None:
    """Base "on-error" callback.

    Args:
        response (dict | str): The remote response
        url (str | None, optional): The remote address. Defaults to None.
        doctype (str | None, optional): The doctype calling the remote address. Defaults to None.
        document_name (str | None, optional): The document calling the remote address. Defaults to None.
        integration_reqeust_name (str | None, optional): The created Integration Request document name. Defaults to None.
    """
    handle_errors(
        response,
        route=url,
        doctype=doctype,
        document_name=document_name,
    )


"""
These functions are required as serialising lambda expressions is a bit involving.
"""


def customer_search_on_success(
    response: dict,
    document_name: str,
) -> None:
    frappe.db.set_value(
        "Customer",
        document_name,
        {
            "custom_tax_payers_name": response["taxprNm"],
            "custom_tax_payers_status": response["taxprSttsCd"],
            "custom_county_name": response["prvncNm"],
            "custom_subcounty_name": response["dstrtNm"],
            "custom_tax_locality_name": response["sctrNm"],
            "custom_location_name": response["locDesc"],
            "custom_is_validated": 1,
        },
    )


def item_registration_on_success(response: dict, document_name: str) -> None:
    frappe.db.set_value("Item", document_name, {"custom_item_registered": 1})


def customer_insurance_details_submission_on_success(
    response: dict, document_name: str
) -> None:
    frappe.db.set_value(
        "Customer",
        document_name,
        {"custom_insurance_details_submitted_successfully": 1},
    )


def customer_branch_details_submission_on_success(
    response: dict, document_name: str
) -> None:
    frappe.db.set_value(
        "Customer",
        document_name,
        {"custom_details_submitted_successfully": 1},
    )


def user_details_submission_on_success(response: dict, document_name: str) -> None:
    frappe.db.set_value(
        USER_DOCTYPE_NAME, document_name, {"submitted_successfully_to_etims": 1}
    )


@deprecation.deprecated(
    deprecated_in="0.6.6",
    removed_in="1.0.0",
    current_version=__version__,
    details="Callback became redundant due to changes in the Item doctype rendering the field obsolete",
)
def inventory_submission_on_success(response: dict, document_name) -> None:
    frappe.db.set_value("Item", document_name, {"custom_inventory_submitted": 1})


def imported_item_submission_on_success(response: dict, document_name: str) -> None:
    frappe.db.set_value("Item", document_name, {"custom_imported_item_submitted": 1})


def sales_information_submission_on_success(
    response: dict,
    invoice_type: str,
    document_name: str,
    company_name: str,
    invoice_number: int | str,
) -> None:
    response_data = response["data"]

    frappe.db.set_value(
        invoice_type,
        document_name,
        {
            "custom_current_receipt_number": response_data["curRcptNo"],
            "custom_total_receipt_number": response_data["totRcptNo"],
            "custom_internal_data": response_data["intrlData"],
            "custom_receipt_signature": response_data["rcptSign"],
            "custom_control_unit_date_time": response_data["sdcDateTime"],
            "custom_successfully_submitted": 1,
        },
    )

    current_env_setting_record = get_curr_env_etims_settings(company_name)

    if current_env_setting_record:
        frappe.db.set_value(
            SETTINGS_DOCTYPE_NAME,
            current_env_setting_record.name,
            "most_recent_sales_number",
            invoice_number,
        )


def item_composition_submission_on_success(response: dict, document_name: str) -> None:
    frappe.db.set_value(
        "BOM", document_name, {"custom_item_composition_submitted_successfully": 1}
    )


def purchase_invoice_submission_on_success(response: dict, document_name: str) -> None:
    # Update Invoice fields from KRA's response
    frappe.db.set_value(
        "Purchase Invoice",
        document_name,
        {
            "custom_submitted_successfully": 1,
        },
    )


def stock_mvt_submission_on_success(response: dict, document_name: str) -> None:
    frappe.db.set_value(
        "Stock Ledger Entry", document_name, {"custom_submitted_successfully": 1}
    )


def purchase_search_on_success(reponse: dict) -> None:
    sales_list = reponse["data"]["saleList"]

    for sale in sales_list:
        created_record = create_purchase_from_search_details(sale)

        for item in sale["itemList"]:
            create_and_link_purchase_item(item, created_record)


def create_purchase_from_search_details(fetched_purchase: dict) -> str:
    doc = frappe.new_doc(REGISTERED_PURCHASES_DOCTYPE_NAME)

    doc.supplier_name = fetched_purchase["spplrNm"]
    doc.supplier_pin = fetched_purchase["spplrTin"]
    doc.supplier_branch_id = fetched_purchase["spplrBhfId"]
    doc.supplier_invoice_number = fetched_purchase["spplrInvcNo"]

    doc.receipt_type_code = fetched_purchase["rcptTyCd"]
    doc.payment_type_code = frappe.get_doc(
        "Navari KRA eTims Payment Type", {"code": fetched_purchase["pmtTyCd"]}, ["name"]
    ).name
    doc.remarks = fetched_purchase["remark"]
    doc.validated_date = fetched_purchase["cfmDt"]
    doc.sales_date = fetched_purchase["salesDt"]
    doc.stock_released_date = fetched_purchase["stockRlsDt"]
    doc.total_item_count = fetched_purchase["totItemCnt"]
    doc.taxable_amount_a = fetched_purchase["taxblAmtA"]
    doc.taxable_amount_b = fetched_purchase["taxblAmtB"]
    doc.taxable_amount_c = fetched_purchase["taxblAmtC"]
    doc.taxable_amount_d = fetched_purchase["taxblAmtD"]
    doc.taxable_amount_e = fetched_purchase["taxblAmtE"]

    doc.tax_rate_a = fetched_purchase["taxRtA"]
    doc.tax_rate_b = fetched_purchase["taxRtB"]
    doc.tax_rate_c = fetched_purchase["taxRtC"]
    doc.tax_rate_d = fetched_purchase["taxRtD"]
    doc.tax_rate_e = fetched_purchase["taxRtE"]

    doc.tax_amount_a = fetched_purchase["taxAmtA"]
    doc.tax_amount_b = fetched_purchase["taxAmtB"]
    doc.tax_amount_c = fetched_purchase["taxAmtC"]
    doc.tax_amount_d = fetched_purchase["taxAmtD"]
    doc.tax_amount_e = fetched_purchase["taxAmtE"]

    doc.total_taxable_amount = fetched_purchase["totTaxblAmt"]
    doc.total_tax_amount = fetched_purchase["totTaxAmt"]
    doc.total_amount = fetched_purchase["totAmt"]

    try:
        doc.submit()

    except frappe.exceptions.DuplicateEntryError:
        # TODO: suppress duplicate error message occurring even after catching exception
        frappe.log_error(title="Duplicate entries")

    return doc.name


def create_and_link_purchase_item(item: dict, parent_record: str) -> None:
    item_cls_code = item["itemClsCd"]

    if not frappe.db.exists(ITEM_CLASSIFICATIONS_DOCTYPE_NAME, item_cls_code):
        doc = frappe.new_doc(ITEM_CLASSIFICATIONS_DOCTYPE_NAME)
        doc.itemclscd = item_cls_code
        doc.taxtycd = item["taxTyCd"]
        doc.save()

        item_cls_code = doc.name

    registered_item = frappe.new_doc(REGISTERED_PURCHASES_DOCTYPE_NAME_ITEM)

    registered_item.parent = parent_record
    registered_item.parentfield = "items"
    registered_item.parenttype = "Navari eTims Registered Purchases"

    registered_item.item_name = item["itemNm"]
    registered_item.item_code = item["itemCd"]
    registered_item.item_sequence = item["itemSeq"]
    registered_item.item_classification_code = item_cls_code
    registered_item.barcode = item["bcd"]
    registered_item.package = item["pkg"]
    registered_item.packaging_unit_code = item["pkgUnitCd"]
    registered_item.quantity = item["qty"]
    registered_item.quantity_unit_code = item["qtyUnitCd"]
    registered_item.unit_price = item["prc"]
    registered_item.supply_amount = item["splyAmt"]
    registered_item.discount_rate = item["dcRt"]
    registered_item.discount_amount = item["dcAmt"]
    registered_item.taxation_type_code = item["taxTyCd"]
    registered_item.taxable_amount = item["taxblAmt"]
    registered_item.tax_amount = item["taxAmt"]
    registered_item.total_amount = item["totAmt"]

    registered_item.save()


def notices_search_on_success(response: dict) -> None:
    notices_list = response["data"]["noticeList"]

    for notice in notices_list:
        doc = frappe.new_doc(NOTICES_DOCTYPE_NAME)

        doc.notice_number = notice["noticeNo"]
        doc.title = notice["title"]
        doc.registration_name = notice["regrNm"]
        doc.details_url = notice["dtlUrl"]
        doc.registration_datetime = notice["regDt"]
        doc.contents = notice["cont"]

        try:
            doc.submit()

        except frappe.exceptions.DuplicateEntryError:
            # TODO: suppress duplicate error message occurring even after catching exception
            frappe.log_error(title="Duplicate entries")


def stock_mvt_search_on_success(response: dict) -> None:
    stock_list = response["data"]["stockList"]

    for stock in stock_list:
        doc = frappe.new_doc(REGISTERED_STOCK_MOVEMENTS_DOCTYPE_NAME)

        doc.customer_pin = stock["custTin"]
        doc.customer_branch_id = stock["custBhfId"]
        doc.stored_and_released_number = stock["sarNo"]
        doc.occurred_date = stock["ocrnDt"]
        doc.total_item_count = stock["totItemCnt"]
        doc.total_supply_price = stock["totTaxblAmt"]
        doc.total_vat = stock["totTaxAmt"]
        doc.total_amount = stock["totAmt"]
        doc.remark = stock["remark"]

        doc.set("items", [])

        for item in stock["itemList"]:
            doc.append(
                "items",
                {
                    "item_name": item["itemNm"],
                    "item_sequence": item["itemSeq"],
                    "item_code": item["itemCd"],
                    "barcode": item["bcd"],
                    "item_classification_code": item["itemClsCd"],
                    "packaging_unit_code": item["pkgUnitCd"],
                    "unit_of_quantity_code": item["qtyUnitCd"],
                    "package": item["pkg"],
                    "quantity": item["qty"],
                    "itemExprDt": item["item_expiry_date"],
                    "unit_price": item["prc"],
                    "supply_amount": item["splyAmt"],
                    "discount_rate": item["totDcAmt"],
                    "taxable_amount": item["taxblAmt"],
                    "tax_amount": item["taxAmt"],
                    "taxation_type_code": item["taxTyCd"],
                    "total_amount": item["totAmt"],
                },
            )

        doc.save()


def imported_items_search_on_success(response: dict) -> None:
    items = response["data"]["itemList"]

    for item in items:
        doc = frappe.new_doc(REGISTERED_IMPORTED_ITEM_DOCTYPE_NAME)

        doc.item_name = item["itemNm"]
        doc.task_code = item["taskCd"]
        doc.declaration_date = item["dclDe"]
        doc.item_sequence = item["itemSeq"]
        doc.declaration_number = item["dclNo"]
        doc.hs_code = item["hsCd"]
        doc.origin_nation_code = item["orgnNatCd"]
        doc.export_nation_code = item["exptNatCd"]
        doc.package = item["pkg"]
        doc.packaging_unit_code = item["pkgUnitCd"]
        doc.quantity = item["qty"]
        doc.quantity_unit_code = item["qtyUnitCd"]
        doc.gross_weight = item["totWt"]
        doc.net_weight = item["netWt"]
        doc.suppliers_name = item["spplrNm"]
        doc.agent_name = item["agntNm"]
        doc.invoice_foreign_currency_amount = item["invcFcurAmt"]
        doc.invoice_foreign_currency = item["invcFcurCd"]
        doc.invoice_foreign_currency_rate = item["invcFcurExcrt"]

        doc.save()


def search_branch_request_on_success(response: dict) -> None:
    for branch in response["data"]["bhfList"]:
        doc = None

        try:
            doc = frappe.get_doc(
                BRANCH_ID_DOCTYPE_NAME, branch["bhfId"], for_update=True
            )

        except frappe.exceptions.DoesNotExistError:
            doc = frappe.new_doc(BRANCH_ID_DOCTYPE_NAME)

        finally:
            doc.pin = branch["tin"]
            doc.branch_name = branch["bhfNm"]
            doc.branch_code = branch["bhfId"]
            doc.branch_status_code = branch["bhfSttsCd"]
            doc.county_name = branch["prvncNm"]
            doc.sub_county_name = branch["dstrtNm"]
            doc.tax_locality_name = branch["sctrNm"]
            doc.location_description = branch["locDesc"]
            doc.manager_name = branch["mgrNm"]
            doc.manager_contact = branch["mgrTelNo"]
            doc.manager_email = branch["mgrEmail"]
            doc.is_head_office = branch["hqYn"]

            doc.save()
