# Counter — Agent Shop Ledger

Run with Python 3.12+: `python server.py`, then open http://127.0.0.1:8000.
Create the owner login on first visit. There are no default credentials or example financial records. Add opening cash using Overview → Add funds → Shop cash; add wallet funds in the same way or set opening balances when creating new accounts. Existing accounts start at zero.

The application uses a shared SQLite database on the server, not browser storage. `LEDGER_DB` selects another database path. Back up the database regularly with SQLite's backup API. For multi-device access run with `HOST=0.0.0.0` on a trusted network. Internet deployment requires an HTTPS reverse proxy; do not expose Python's development HTTP server directly. `PORT` defaults to 8000. No external Python packages are required. Google Fonts is optional; system fonts work offline.

Features: owner/staff logins, editable provider/account types and account archival, cash-in/out, automatic fees, actual cash movement, customer suggestions, shared balances, cash/wallet expenses, owner fund movements, reasoned reversals, searchable history, CSV export, and saved daily reconciliation counts. Fee income reflects collected fees and confirmed cash movements. All amounts are whole MMK.

Fees: cash-in is 100 MMK per started 100,000 MMK. Cash-out is 100 through 10,000, 300 through 50,000, and 500 through 99,999. From 100,000 to 1,999,999 it is 500 per completed 100,000. At 2,000,000 and above it is 0.4% rounded to the nearest kyat, ties up. The threshold gives 9,500 at 1,999,999 and 8,000 at 2,000,000. Fees are editable. An override reason is optional. Cash-out supports deducting the fee or confirming a separately collected cash fee.

New reversals create a dated compensating entry and preserve the original movements. Old reversed entries retain their prior behavior because their reversal date was never stored. Historical collected fees are inferred from recorded cash plus wallet movement; the original recorded fee remains available in the API audit fields. Historical records with a negative implied fee are flagged for review. Old closing snapshots remain observations. New closings require all counts to match and lock financial writes for the current Myanmar business day. New account opening funds are posted as a ledger entry.

Staff can create transactions, expenses and closings and view the shop ledger. Only the owner manages wallets, funds, staff creation and reversals. Every financial write runs in a serialized database transaction with balance validation. Repeated transaction IDs are rejected. Sessions expire after 12 hours; password hashes use salted PBKDF2. First-run setup must be completed before exposing the server. Staff password reset and account removal are not included in this first version.

Run tests: `python3 -B -m unittest discover -s tests -t . -v`.

Sites publishing was unavailable in this execution environment: the Sites plugin's setup, source workflow and packaging helper files were not installed. This is a runnable local application, not a published Sites deployment.


Receipt import supports PNG/JPEG up to 5 MB, selected as KBZPay or WavePay. The server reads images locally: macOS defaults to Apple Vision; Linux uses native Tesseract with the cloud requirements and bundled models. English/Myanmar name handling and QR decoding run locally; see the OCR notes for engine-specific limits. QR transaction IDs are decoded as unverified data. No external OCR service receives the image. WavePay Send/Receive Money extraction reads transaction ID, total amount, customer contact and receipt time from the verified supplied layouts.

Import creates a private draft with its source image and extracted data. It has no balance effect. The user must choose a matching wallet, check Cash In/Cash Out, complete the required customer name, review the fields and press Confirm. The review checkbox starts selected. Unused drafts expire after 24 hours and are removed on later imports. Confirmed receipt images remain in the SQLite backup with their transaction linkage. Manual provider transaction IDs are optional. Nonblank IDs are unique per wallet, including reversed originals. The posted entry retains the provider transaction ID, receipt time and import ID. Receipt time is informational. Posting uses the current open Myanmar business date.


## Developer navigation

Read [Developer.md](Developer.md) for the project tree, every feature and method entry point, REST routes, database compatibility and financial rules. Backend features live in `counter/`, browser features in `public/js/features/`, translations and icons in `public/js/i18n/`, and regression tests in `tests/`. The startup command remains `python3 -B server.py`.

Normal receipt import uses the printed Total Amount when present. Wave Channel uses customer principal and records commission/provider fee separately to derive the net wallet movement. For a shop-owned wallet receipt, minus suggests agent Cash In and plus suggests agent Cash Out. The owner selects the wallet and checks the editable direction and other fields before pressing Confirm. Unsigned receipts require manual direction selection. Both manual and imported Cash In increase shop cash by principal plus collected fee and decrease the selected wallet by principal. Cash Out increases the wallet by principal and decreases net shop cash by principal minus collected fee. Separate cash-out collection records the full payout and receipt of the fee. Cash In checks outgoing wallet funds. Cash Out checks outgoing cash. New postings have accounting_rule AGENT_CASH_V1. Historical recorded movements are retained and reversals negate the exact original movements. Masked phones remain separate from full phone numbers.


Myanmar customer names use local Tesseract.js when Apple Vision misses the Customer Name field. Install Node.js, then run npm ci --prefix tools/ocr once on a new computer. The included Myanmar model runs locally. The OCR image stays on the server. Low-confidence results remain empty for manual review.

Daily Summary provides date and wallet filters, net Cash In/Cash Out, fees, and per-wallet opening/movement/closing balances. Export CSV is available on Daily Closing only, with its own date/wallet selection and saved closing counts when available.

OCR implementation notes and verified KBZPay layouts are recorded in [docs/OCR.md](docs/OCR.md). The supplied WavePay Send/Receive Money and Wave Channel Cash In/Receive Money layouts are verified; other layouts need samples and validation. Masked customer contacts are stored separately from complete phone numbers.

Wave Channel OCR: import using WavePay and choose a wallet whose account type is Channel. The review form separates customer principal, provider commission, provider fee and original receipt wallet movement. Confirm is required before balances change. Provider commission/fees are included separately in daily reports and CSV exports; reversals restore exact posted movements. See docs/OCR.md for rules and extension notes.

Customer Name is required for manual and imported Cash In / Cash Out. If OCR cannot read a name or the receipt has no name, fill it before confirming. Customer phone and provider transaction ID remain optional. This rule applies to new postings; historical records are unchanged.

Money inputs accept English/Myanmar digits and comma grouping. Letters, decimal points, signs and text pasted with currency labels are rejected without changing the existing amount. Whole-MMK/range validation also runs on the server.


## Cloud hosting without a Mac

Follow [the PythonAnywhere deployment guide](docs/DEPLOY_PYTHONANYWHERE.md). It includes the WSGI template, Python 3.12 environment, Linux Tesseract setup, private owner creation, existing-ledger migration, backups and free-hosting alternatives. The hosted entry point is `wsgi.py`; `server.py` stays available for local development. Cloud OCR dependencies are installed with `pip install -r requirements.txt` and additionally require native Tesseract 4+. No React/Spring Boot migration is required.
