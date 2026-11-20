# Deploy Counter on PythonAnywhere Free

This deployment runs independently of your Mac. Devices open the same HTTPS URL and use the same server-side SQLite database. Linux uses Tesseract for OCR; it does not call Apple Vision or a Mac over the network.

Code preparation and local tests do not create a PythonAnywhere account or publish a live site. Follow these dashboard steps after the updated source is available on GitHub.

## What the free plan supports

PythonAnywhere currently provides 512 MiB disk space, one web app with one web worker, a one-month web-app expiry and two consoles. Review the Web dashboard's renewal control before expiry. New free accounts do not include MySQL or daily scheduled tasks; SQLite is available to all accounts. Sources: [free features](https://help.pythonanywhere.com/pages/FreeAccountsFeatures/), [databases](https://help.pythonanywhere.com/pages/KindsOfDatabases/).

The published 100 CPU-second allowance applies to consoles/scheduled tasks, not currently to web apps. Console setup and OCR checks may therefore be slowed by the allowance. An OCR request still occupies the single web worker and can delay other requests. [CPU allowance](https://help.pythonanywhere.com/pages/WhatAreCPUSeconds/)

Receipt photos are used temporarily for OCR and are not retained in SQLite or a drafts table. Confirmed transaction fields are stored. The 512 MiB quota still covers source, Git history, dependencies, models, financial records and backups. Monitor disk usage and download backups regularly. Legacy receipt image/draft storage is removed on startup; historical backups made before that change can still contain images.

## 1. Create the account and clone the source

Create a free account at https://www.pythonanywhere.com/ (or the EU service). Open **Consoles → Bash**. Replace `YOUR_USERNAME` in examples with your actual PythonAnywhere username.

```sh
cd ~
git clone https://github.com/ThinzarMayMyat02/Cashier_Agent_Ledger.git
cd ~/Cashier_Agent_Ledger
python3.12 -m venv ~/.virtualenvs/counter
source ~/.virtualenvs/counter/bin/activate
pip install --no-cache-dir -r requirements.txt
mkdir -p ~/counter-data
chmod 700 ~/counter-data
```

Use Python 3.12 for both the virtualenv and the Web application. If the dashboard offers a different supported Python version, select the matching interpreter for both; cloud dependencies require Python 3.11+ and the documented target is 3.12.

There is no npm install or frontend build for this deployment. The cloud backend uses Pillow, native Tesseract and zxing-cpp; the optional Mac Tesseract.js fallback is not used.

## 2. Verify Linux OCR on the host

PythonAnywhere staff have documented `/usr/bin/tesseract`, but system images can differ. Check your actual account rather than assuming the executable/version is available. [Tesseract on PythonAnywhere](https://www.pythonanywhere.com/forums/topic/27147/)

```sh
/usr/bin/tesseract --version
export LEDGER_OCR_BACKEND=tesseract
export LEDGER_TESSERACT_CMD=/usr/bin/tesseract
export OMP_THREAD_LIMIT=1
python tools/manage.py check-ocr
```

Tesseract 4+ is required for the bundled LSTM models. `check-ocr` exercises a synthetic image and the local English model, checks QR/image dependencies and the Myanmar model, and does not post a transaction. No runtime model downloads or external OCR service are used. The repository contains both `eng.traineddata` and `mya.traineddata` with license/source notes.

If the binary is missing/too old or the smoke check fails, do not expose a broken OCR flow. Check your account's system-image availability with PythonAnywhere support. Installing the Python requirements alone does not install the native Tesseract executable; free accounts cannot run `sudo apt install`. [Package installation limits](https://help.pythonanywhere.com/pages/InstallingNewModules/)

## 3. Create the owner before publishing

For a new, empty cloud ledger:

```sh
export LEDGER_DB="$HOME/counter-data/ledger.sqlite3"
python tools/manage.py init-owner --name ShopOwner
```

Enter the owner password twice when prompted. Password input is hidden and is never written into source/configuration files. There are no default credentials. This command refuses an existing configured ledger and creates no browser session.

If migrating your existing ledger, follow the migration section below instead of creating another owner. The CLI and WSGI configuration must use exactly the same database path.

## 4. Add the WSGI web application

In **Web → Add a new web app**:

1. Choose the free `YOUR_USERNAME.pythonanywhere.com` address (use the hostname shown by the EU dashboard when applicable).
2. Choose **Manual configuration**, then **Python 3.12**. Do not choose a generated Flask starter.
3. Set **Source code** and **Working directory** to `/home/YOUR_USERNAME/Cashier_Agent_Ledger`.
4. Set **Virtualenv** to `/home/YOUR_USERNAME/.virtualenvs/counter`.
5. Open the **WSGI configuration file** linked on the Web tab. Replace its generated contents with `deploy/pythonanywhere_wsgi.py` from this repository.
6. Replace every `YOUR_USERNAME` placeholder in that configuration, including the hostname. On EU accounts use the exact EU hostname shown by the dashboard.
7. Save the file and click **Reload** on the Web tab.

The template selects:

```text
LEDGER_DB=/home/YOUR_USERNAME/counter-data/ledger.sqlite3
LEDGER_ALLOWED_HOSTS=YOUR_USERNAME.pythonanywhere.com
LEDGER_OCR_BACKEND=tesseract
LEDGER_TESSERACT_CMD=/usr/bin/tesseract
LEDGER_COOKIE_SECURE=1
OMP_THREAD_LIMIT=1
```

The template imports the root `wsgi.py` application. `server.py` remains the local development entry point; do not run it as a long-lived Bash-console process for hosting. PythonAnywhere manages the WSGI worker.

Open **https://YOUR_USERNAME.pythonanywhere.com** and sign in with the owner credentials created in step 3. Secure cookies are enabled by trusted server configuration, including when the hosting proxy passes an HTTP WSGI scheme. Enable HTTPS-only/force-HTTPS in the dashboard if offered, and distribute the HTTPS link.

Official reference: [manual WSGI setup](https://help.pythonanywhere.com/pages/WebAppBasics/).

## 5. Optional static mappings

To reduce work for the one web worker, add:

| URL | Directory |
|---|---|
| `/css/` | `/home/YOUR_USERNAME/Cashier_Agent_Ledger/public/css/` |
| `/js/` | `/home/YOUR_USERNAME/Cashier_Agent_Ledger/public/js/` |

The top-level HTML/JS/CSS files can remain served through WSGI. Do not map `/` to the source directory and do not map `counter-data`, backups or receipt storage to any public URL. An incorrect root mapping can bypass API routing or expose private files.

## 6. Test from each device

Use fictional data before relying on the cloud ledger:

1. Open the HTTPS URL on the shop computer, phone and tablet. Sign in with appropriate Owner/Staff accounts.
2. Add fictional opening cash and wallet funds. Confirm all devices see the shared balances after navigation/refresh.
3. Test Manual Cash In/Out, required names, editable fees and digit-only monetary inputs.
4. Import a KBZPay, Normal WavePay and Wave Channel receipt. Review amount, ID, time, direction, customer details, commission and provider fee. Select the wallet yourself.
5. Verify balances do not change while importing/editing. Confirm once; check actual cash/wallet movement and duplicate protection.
6. Test owner reversal, selected-date/wallet daily summary, Daily Closing CSV and matching counts.

Tesseract can read differently from Apple Vision. Verified local samples include Channel principal/commission/net, Normal Wave amounts/IDs/dates/names, KBZ transfer fields/QR and a Myanmar utility-customer name. Some Normal Wave masked phone fields were unreadable with Tesseract and remain empty rather than guessing hidden/unclear digits. Review every receipt before Confirm. Hosting-system OCR accuracy and execution time must still be checked on your account.

## Move existing data from your Mac

Git contains no financial database. Cloning the repository creates no copy of your current accounts, users, transactions or receipt evidence.

1. Stop entering transactions temporarily for the final transfer.
2. On the Mac, create a consistent SQLite backup with the actual existing database path:

   ```sh
   LEDGER_DB="/absolute/path/to/current/ledger.sqlite3" python3 tools/manage.py backup --output /private/tmp/counter-transfer.sqlite3
   ```

3. Through PythonAnywhere's private Files interface, upload that backup as `/home/YOUR_USERNAME/counter-data/ledger.sqlite3`. Do not overwrite an already-used cloud ledger; reconcile any cloud activity first.
4. Set the WSGI/CLI database path to that file and Reload. Existing owner/staff logins and stored records remain available.
5. Compare balances, recent history and closing snapshots before reopening entry. Avoid recording new transactions independently in both the Mac and cloud copies after the switch.

## Backups and source updates

From the activated Bash-console virtualenv:

```sh
cd ~/Cashier_Agent_Ledger
export LEDGER_DB="$HOME/counter-data/ledger.sqlite3"
python tools/manage.py backup --output "$HOME/counter-data/backup-YYYY-MM-DD.sqlite3"
```

Choose a new output filename each time. The command uses SQLite's backup API and refuses to overwrite an existing path. Download backups privately, verify them, and remove older copies only according to your retention policy to avoid filling free storage. New free accounts do not have the daily scheduled-task feature, so do not rely on an unavailable scheduler.

For source updates, back up first, run `git pull --ff-only` inside the checkout, activate the virtualenv, run `pip install --no-cache-dir -r requirements.txt` if dependencies changed, then Reload from Web. The database stays outside the checkout, so updating source does not replace it. Schema changes remain additive.

## Troubleshooting

| Symptom | Check |
|---|---|
| ImportError / 502 | Web error log, source path and matching virtualenv/Python version |
| `Invalid request host` | `LEDGER_ALLOWED_HOSTS` must contain the exact dashboard hostname |
| Login immediately disappears | Use HTTPS; verify secure-cookie configuration and the correct database path |
| First-run setup appears unexpectedly | CLI and WSGI are pointing at different SQLite files |
| OCR dependency error | Install requirements in the Web tab's virtualenv and Reload |
| Missing Tesseract/models | Run `/usr/bin/tesseract --version` and `check-ocr`; bundled models must be present |
| Database locked | Check concurrent console writes/long jobs; keep one worker and do not OCR inside a DB write transaction |
| No space left | Source + virtualenv + Git + SQLite receipt blobs + backups share the quota |
| App stops after expiry | Check the Web dashboard's free-app expiry/renewal control |

## Other free-hosting choices

| Service | Fit for this app |
|---|---|
| PythonAnywhere Free | Simplest current target for WSGI + persistent SQLite; storage/worker/expiry limitations above |
| Oracle Cloud Always Free VM | Can host this WSGI app, Tesseract and persistent SQLite. Requires server administration, HTTPS/backups and card verification; free VM capacity may be unavailable and idle resources/accounts may be reclaimed/suspended |
| Render Free | Can run Python, but its local filesystem is ephemeral and free services sleep. Current SQLite/receipt storage must not be used there; external durable database/storage and corresponding code changes are needed. Render's free Postgres expires after 30 days |

Sources checked November 2026: [Oracle FAQ](https://www.oracle.com/cloud/free/faq/), [Render free limits](https://render.com/docs/free). These are platform offers with limits, not guarantees of permanent free financial-system hosting.
