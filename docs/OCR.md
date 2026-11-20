# Receipt OCR implementation notes

## Provider status

KBZPay is verified against the supplied English/Myanmar transfer and utility receipts.
WavePay Send Money and Receive Money are now verified against the two supplied Myanmar-interface receipts with English customer names and masked phones. The supplied Wave Channel Cash In and Receive Money layouts are also verified separately. Other WavePay layouts still need samples and validation.
Keep KBZPay-only recognition rules behind the explicit provider check.

## Local pipeline

1. Authenticated upload accepts PNG/JPEG up to 5 MB.
2. `LEDGER_OCR_BACKEND=auto` selects Apple Vision on macOS or native Tesseract on Linux. Explicit `vision`/`tesseract` settings are supported. Both read locally; Tesseract uses Pillow and zxing-cpp, without Swift or Node.
3. counter/receipts/parser.py extracts receipt fields without trusting a QR as payment proof.
4. If the Customer Name value is missing, the native reader crops the value next to that label. counter/receipts/myanmar.py calls tools/ocr/read-name.cjs with the bundled Myanmar model.
5. The server returns extracted fields without storing a picture, draft or raw OCR text.
6. The owner chooses a wallet, reviews the editable form and presses Confirm. Extraction alone does not post money.

For the Mac Vision Myanmar-name fallback, install Node.js and run npm ci --prefix tools/ocr. For Linux/cloud, install requirements.txt with Python 3.12 and native Tesseract 4+; see DEPLOY_PYTHONANYWHERE.md. Linux uses bundled English/Myanmar models and needs no npm install.
The OCR engine and Myanmar model run locally. OCR does not send receipt images to an external service.
The model source and license are in counter/receipts/tessdata/.

## KBZPay layouts verified

- English transfer receipt, with positive/negative amount and sender/recipient name.
- Transfer receipt with masked phone on the same line or the following line.
- Transfer receipt with verification QR. Decode the KPRSC transaction ID as unverified data, preserving leading zeroes.
- Utility e-receipt with Amount, Fees and Total Amount. Prefer Total Amount. Provider fees in the receipt are separate from the shop's collected fee.
- Utility e-receipt with compact YYYYMMDD transaction date and a Myanmar customer name.
- Myanmar-interface transfer receipt where Apple Vision misses Burmese labels but reads the English customer name and adjacent masked phone. Use the unique name/contact pair and unique standalone 20-digit transaction ID, for KBZPay only.

## Customer contact rules

Keep the complete customer phone in phone.
Keep a masked contact in masked_phone in the temporary extraction and customer_phone_masked on the posted entry.
Do not invent missing digits or use a masked contact as a unique customer identity.
History displays the complete phone when supplied, otherwise the stored masked phone.
A missing/ambiguous name stays editable. The local Myanmar fallback rejects low-confidence results.

## Accounting and review

These receipts are interpreted from the shop wallet perspective.
A negative wallet amount suggests agent Cash In. A positive wallet amount suggests agent Cash Out.
Unsigned or ambiguous receipts leave direction for the operator to select.
The operator always selects the wallet account.
Manual and imported postings share the same agent cash/float rules.
Receipt time is evidence. Business date is the current open Myanmar day.
Provider transaction IDs are optional for manual entry and deduplicated per wallet when supplied.
The source image is temporary only. Confirm stores the reviewed transaction fields; there is no retained receipt evidence.

## WavePay Send/Receive Money rules

The provider-specific dispatcher and Normal parser are in counter/receipts/wavepay.py; Channel row interpretation is in counter/receipts/wave_channel.py. It requires a recognizable Send Money or Receive Money heading before applying unlabelled-field recognition. Send Money suggests agent Cash In. Receive Money suggests agent Cash Out. Conflicting printed signs require manual direction selection. The supplied photos expose a 10-digit transaction ID, sometimes followed by an OCR copy-icon artifact. Preserve it as a string. Read adjacent customer/contact rows without inferring masked digits. Combine the English date with the AM/PM time and return a 24-hour receipt timestamp. Use the last explicit currency amount as the total in this verified layout. Provider receipt fees remain separate from the shop fee.

Tests include both real-photo browser flows and synthetic fixtures in tests/test_wavepay_ocr.py. Blank or ambiguous fields remain editable for owner review.

## Extending WavePay further

Obtain redacted real samples of incoming/outgoing transactions, both interface languages, full/masked customer contacts and QR receipts if provided.
Determine what receipt amount includes and whose wallet the sign describes.
Add provider-specific fields and fixtures without enabling KBZPay's unlabeled-ID/name fallbacks for WavePay.
Verify all extracted fields, no balance change before Confirm, duplicate protection, reversals and daily reports before declaring the provider verified.

## Relevant files and tests

- counter/receipts/parser.py handles field recognition and KBZPay-only fallbacks.
- counter/receipts/reader.py coordinates native OCR and the Myanmar fallback.
- counter/receipts/posting.py validates receipt review, provider adjustments and masked contact validation.
- counter/ledger.py orchestrates validation, calculation and atomic posting with receipt linkage.
- public/js/features/transactions.js coordinates form opening/submission.
- public/js/features/transaction-form/ contains template markup, receipt field population and display-only fee/movement previews.
- tests/test_receipts.py covers parsing, masked contacts, provider separation and reviewed posting.
- tests/test_myanmar_ocr.py covers Myanmar-name output and confidence rejection.

Run python3 -B -m unittest discover -s tests -t . -v.
Use a temporary database for testing actual photos. Avoid committing real receipt images or customer details as test fixtures.

## Wave Channel receipts

The supplied Cash In and Receive Money Channel layouts are separate from normal WavePay transfers. They use provider `WavePay` and account kind `Channel`. An operator must choose a Channel wallet; the server also checks the account kind.

Channel rules:

- Read the first currency amount as customer principal, the next currency amount as provider commission, and the last currency amount as the absolute net wallet movement. The lower amount repeats the principal. Cash In repeats commission before its total.
- Cash In: wallet delta = −principal + provider commission − provider fee. Receive Money suggests Cash Out: wallet delta = +principal + provider commission − provider fee.
- Shop cash uses the customer principal and the independently collected shop fee, exactly as manual transactions. Provider commission is wallet income; provider fee is a wallet expense. Neither changes the cash paid/received or gets counted again as collected shop fees.
- Example: principal 30,000, provider commission 9, provider fee 0, shop fee 100. Cash +30,100; wallet −29,991; shop fee income 100 and commission income 9. The receipt's net 29,991 must not replace the principal 30,000.
- The last 10-digit value before the date is the transaction ID in these verified layouts. Cash In has a destination phone before it. Receive Money may have a reference number before it; that reference is not a transaction ID or phone. Masked NRC is not a customer name. Ambiguous identifier counts are left blank.
- Preserve the printed phone digits. Do not invent a leading zero or unmask information.
- Check repeated principal, commission and wallet-net arithmetic. An incomplete/conflicting receipt requires operator direction selection and correction.
- Provider commission and provider fee are editable whole-MMK review fields, validated against the selected Channel account and explicitly confirmed receipt metadata. Missing adjustment fields are rejected. The original image and extraction are temporary and are discarded when the form closes. Corrections affect the posting preview; the original receipt net remains read-only for comparison.
- Entries store provider_commission, provider_fee and receipt_format alongside exact cash/wallet deltas. Additive migrations default old provider adjustments to zero without recomputing old entries. Reversals negate commission, provider fee and the original balance changes exactly.
- Daily Summary, Overview and history expose commission separately. Daily Closing CSV includes provider commission and provider fee per wallet and in its total row. Opening/closing balances sum actual posted wallet deltas.

Both supplied Channel photos were tested through local Apple Vision extraction and the browser form using a temporary database. Tests cover no movement before Confirm, account-kind validation, customer requirement, explicit posting, filtered daily reports, CSV, matching closing and exact reversals. Synthetic fixtures are in tests/test_wave_channel.py; customer images are not copied into the repository.

## Required customer names

Customer Name is required for every manual and imported Cash In / Cash Out. OCR may suggest a name; when the receipt contains no customer name, the operator must supply it. Browser validation and the posting API reject blank, whitespace-only, non-text or overlong names. Names are trimmed and limited to 100 characters. Customer phone and manual provider transaction ID remain optional. Funding and expense records use their required reason/category rather than a customer name. Historical entries are preserved.


## Linux/WSGI OCR backend

`counter/receipts/tesseract_reader.py` validates image dimensions (10,000 max per side, 25 million pixels), format and EXIF rotation before reading. The shared upload limit remains 5 MB. Native Tesseract is invoked with an argument list, a private temporary image, local tessdata, one OpenMP thread and a 40-second per-pass timeout. TSV words are reconstructed as visual fragments, keeping widely separated label/value columns distinct. Missing/invalid TSV and engine errors reject extraction rather than inventing fields. Temporary images/crops are removed after extraction. QR payloads are decoded locally by zxing-cpp and remain unverified input.

The English and Myanmar fast models are bundled with source/license/hash notes. No model download or external OCR API is used at import time. An English Customer Name label anchors the local Myanmar crop; taller glyph marks receive sufficient whitespace. A confident Normal Wave name may be recovered by its position before a unique transaction ID even if the masked phone is unreadable. Reference/NRC values and ambiguous names are not used as customer identities.

Tesseract can render the Wave copy icon as symbols or a separated `8`, join `CashIn`, and read the date bullet as `+`. The Wave parser accepts these tested layout artifacts without substituting digits inside amounts/IDs. A contiguous 11-digit value is not truncated into a 10-digit ID. Split dates/times tolerate limited intervening nonnumeric OCR text.

Actual supplied photos were tested with the portable Tesseract path: Channel Cash In/Receive principal, commission, net, IDs and dates; Normal Wave amounts/IDs/dates/names; KBZ transfer amounts/IDs/customer details and QR; KBZ utility total/date and Myanmar customer name. Some Normal Wave masked contacts remain unreadable with this engine and are left empty. Tests on the local host do not establish accuracy/performance on a live PythonAnywhere system image; run `python tools/manage.py check-ocr` and review actual receipts there before use.

The WSGI import lifecycle is unchanged: authenticate → OCR outside financial locks → temporary fields → review and required name/wallet → explicit Confirm → atomic transaction entry. No balance changes occur during OCR. See `tests/test_portable_ocr.py` and `tests/test_wsgi.py`.
