"""
03 — Receipt / Invoice Extractor
Extract structured data from unstructured text using nested schemas.
Demonstrates: nested @generable classes, list fields, complex schemas.

Use case: Process receipts, invoices, or expense reports locally
without sending financial data to any cloud API.

Note: Apple FM is text-only — it cannot read images directly.
In a real app, use Apple's Vision framework (VNRecognizeTextRequest)
or OCR to extract text from the receipt image first, then pass the
text to Apple FM for structured extraction.

Pipeline: Receipt Image → OCR (Vision.framework) → Text → Apple FM → Structured Data
"""

import asyncio

import apple_fm_sdk as fm


@fm.generable("A single line item on a receipt")
class LineItem:
    description: str = fm.guide("Item name or description")
    quantity: int = fm.guide(range=(1, 100))
    unit_price: float = fm.guide(range=(0.01, 10000.0))


@fm.generable("Extracted receipt data")
class Receipt:
    store_name: str = fm.guide("Name of the store or business")
    date: str = fm.guide("Date in YYYY-MM-DD format")
    items: list[LineItem] = fm.guide()  # variable length list
    subtotal: float = fm.guide(range=(0.01, 100000.0))
    tax: float = fm.guide(range=(0.0, 100000.0))
    total: float = fm.guide(range=(0.01, 100000.0))
    payment_method: str = fm.guide(anyOf=["cash", "credit_card", "debit_card", "other"])


# Real receipt text — in production, this comes from OCR (Vision.framework).
# This sample is transcribed from an actual receipt image (Harbor Lane Cafe).
SAMPLE_RECEIPT = """
HARBOR LANE CAFE
3941 GREEN OAKS BLVD
CHICAGO, IL

        SALE
11/20/2019        11:05 AM
BATCH #:01A2A
APPR #:34362
TRACE #: 9
VISA 3483
1  Tacos Del Mal Shrimp        $14.98
1  Especial Salad Chicken      $12.50
1  Fountain Beverage            $1.99

SUBTOTAL:      $29.47
TAX:            $1.92
TOTAL:         $31.39

TIP: _______________
TOTAL: _______________

    APPROVED
    THANK YOU
    CUSTOMER COPY
"""


async def main():
    model = fm.SystemLanguageModel()
    is_available, reason = model.is_available()
    if not is_available:
        print(f"Model not available: {reason}")
        return

    session = fm.LanguageModelSession(
        instructions=(
            "You are a receipt parser. Extract structured data from receipt text. "
            "Use YYYY-MM-DD format for dates. Map payment to the closest category. "
            "Extract each line item with its quantity and price."
        ),
        model=model,
    )

    print("=" * 60)
    print("  RECEIPT EXTRACTOR")
    print("  Pipeline: Image → OCR → Text → Apple FM → Structured")
    print("=" * 60)

    print("\n=== Raw Receipt Text (from OCR) ===")
    print(SAMPLE_RECEIPT)
    print("=== Extracted Structured Data ===\n")

    try:
        result = await session.respond(
            f"Extract all data from this receipt:\n{SAMPLE_RECEIPT}",
            generating=Receipt,
        )

        # The result is a typed Python dataclass — not a string to parse
        print(f"Store:    {result.store_name}")
        print(f"Date:     {result.date}")
        print(f"Payment:  {result.payment_method}")
        print(f"\nLine Items:")

        # Access nested list of LineItem dataclass objects
        for item in result.items:
            print(f"  {item.quantity}x {item.description:<30} ${item.unit_price:.2f}")

        print(f"\nSubtotal: ${result.subtotal:.2f}")
        print(f"Tax:      ${result.tax:.2f}")
        print(f"Total:    ${result.total:.2f}")

        # Validate extracted total against line items
        calculated = sum(item.unit_price * item.quantity for item in result.items)
        print(f"\n--- Validation ---")
        print(f"Sum of items: ${calculated:.2f}")
        print(f"Receipt subtotal: ${result.subtotal:.2f}")
        if abs(calculated - result.subtotal) < 0.02:
            print("Items match subtotal")
        else:
            print(f"Discrepancy: ${abs(calculated - result.subtotal):.2f}")

    except fm.ExceededContextWindowSizeError:
        print("Error: Receipt text exceeds context window. Try a shorter receipt.")
    except fm.GenerationError as e:
        print(f"Error: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(main())
