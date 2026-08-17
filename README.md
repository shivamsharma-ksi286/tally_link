# Tally Link

> **A Frappe/ERPNext application for bidirectional integration with Tally**

Developed by **[Ksolves India Limited](https://www.ksolves.com)**

---

## Overview

Tally Link connects ERPNext with Tally (via Tally's XML API over HTTP), keeping master data and transactions in sync between the two systems. Customers and suppliers sync as Tally ledgers, stock items sync as Tally stock items, and Sales Invoices, Purchase Invoices, and Payment Entries push to Tally as vouchers.

### Key Features

- **Master Data Sync**: Customers and Suppliers sync to Tally Ledgers; Items sync to Tally Stock Items
- **Transaction Push**: Sales Invoices, Purchase Invoices, and Payment Entries push to Tally as vouchers on submit
- **Manual Push Buttons**: "Push to Tally" actions available directly on Customer, Supplier, Sales Invoice, Purchase Invoice, and Payment Entry forms
- **Scheduled Reverse Sync**: Pulls ledgers, stock items, and vouchers from Tally into ERPNext on a schedule
- **Sync Logging**: Every sync operation (success or failure) is recorded in the Tally Sync Log for auditing

---

## Requirements

- **Frappe**: Version 16.x or higher
- **ERPNext**: Version 16.x or higher
- **Python**: 3.10 or higher
- **Tally**: A running Tally instance (Tally Prime or Tally ERP 9) with the XML/HTTP gateway enabled and reachable from the Frappe server (directly or via a tunnel such as ngrok)

---

## Installation

### Using Bench CLI

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/shivamsharma-ksi286/tally_link
bench install-app tally_link
```

### Manual Installation

```bash
cd $PATH_TO_YOUR_BENCH/apps
git clone https://github.com/shivamsharma-ksi286/tally_link.git
cd ../
bench install-app tally_link
```

### Post-Installation

```bash
bench migrate
bench build
```

---

## Configuration

After installation, open **Tally Settings** in the Frappe desk and configure:

- **Host / Port**: The address of the Tally server's XML gateway
- **Enabled**: Master switch for the integration
- **Default Company**: The Tally company these syncs apply to
- **Sync toggles**: Enable/disable ledger, stock item, and voucher sync individually

Use the **Test Connection** button on Tally Settings to confirm connectivity before relying on the sync.

---

## Development

### Setup Development Environment

```bash
cd apps/tally_link
pre-commit install
```

### Code Quality Tools

- **[Ruff](https://github.com/astral-sh/ruff)**: Fast Python linter and code formatter
- **[ESLint](https://eslint.org/)**: JavaScript linting utility
- **[Prettier](https://prettier.io/)**: Code formatter for JavaScript and JSON
- **[Pyupgrade](https://github.com/asottile/pyupgrade)**: Tool to upgrade Python syntax

### Running Pre-commit Checks

```bash
cd apps/tally_link
pre-commit run --all-files
```

### Contributing Guidelines

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Ensure pre-commit checks pass (`pre-commit run --all-files`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

---

## Usage

### Pushing a Customer or Supplier to Tally

Open any Customer or Supplier record and click **Push to Tally** — this creates or updates the corresponding Tally Ledger, including address, GSTIN, PAN, and contact details sourced from the linked Address.

### Pushing Transactions

Submitted Sales Invoices, Purchase Invoices, and Payment Entries automatically push to Tally as vouchers. A manual **Push to Tally** button is also available on each of these forms.

### Reviewing Sync History

Every sync attempt — automatic or manual — is logged in **Tally Sync Log**, including the direction, status, and any error encountered.

---

## Troubleshooting

**Issue**: "Cannot reach Tally server" errors

**Solution**: Confirm Tally is running, its XML gateway is enabled, and the host/port (or tunnel) in Tally Settings is current and reachable. Use the **Test Connection** button to verify.

**Issue**: Address/state/country not appearing on a Tally ledger

**Solution**: Tally requires a pincode to be present for these mailing details to save. Add a pincode to the linked Address and push again.

**Issue**: Push fails with a duplicate/exists-style error

**Solution**: The ledger may already exist in Tally under a different name or group. Check the Tally Sync Log for the exact error returned by Tally.

---

## Support

For issues, questions, or feature requests:

- **Open an Issue**: [GitHub Issues](https://github.com/shivamsharma-ksi286/tally_link/issues)
- **Contact Ksolves**: Visit [ksolves.com](https://www.ksolves.com) or email support@ksolves.com

---

## License

This project is licensed under the **GPL-3.0 License** - see the [license.txt](./license.txt) file for details.

---

## About Ksolves

**Ksolves India Limited** is a leading software development and consulting company specializing in enterprise solutions, open-source technologies, and cloud infrastructure.

- **Website**: [www.ksolves.com](https://www.ksolves.com)
- **GitHub**: [github.com/ksolves](https://github.com/ksolves)
- **Email**: support@ksolves.com

---

## Disclaimer

This application is provided as-is. Ksolves India Limited is not responsible for any data loss or system issues that may arise from improper usage. Please test thoroughly in a development environment before deploying to production.
