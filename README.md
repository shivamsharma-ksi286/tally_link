# KS Item Price History

> **A Frappe/ERPNext application for tracking and displaying last selling prices of items**

Developed by **[Ksolves India Limited](https://www.ksolves.com)**

---

## Overview

KS Item Price History is a powerful Frappe/ERPNext application that maintains a comprehensive history of item prices and displays the last selling prices of items in your system. This helps businesses track pricing trends, understand historical pricing patterns, and make informed pricing decisions.

### Key Features

- **Price History Tracking**: Automatically maintains a complete history of item prices
- **Last Selling Price Display**: Quickly view the most recent selling price for any item
- **Historical Data**: Access complete pricing records for analysis and reporting
- **Integration**: Seamlessly integrates with your existing ERPNext implementation

---

## Requirements

- **Frappe**: Version 16.x or higher
- **ERPNext**: Version 16.x or higher
- **Python**: 3.10 or higher
- **Node.js**: 16.x or higher (for frontend development)

---

## Installation

### Using Bench CLI

This is the recommended way to install the app in a Frappe bench environment:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/ksolves/ks_item_price_history --branch version-16
bench install-app ks_item_price_history
```

### Manual Installation

If you prefer manual installation, clone the repository into your `apps` directory:

```bash
cd $PATH_TO_YOUR_BENCH/apps
git clone https://github.com/ksolves/ks_item_price_history.git --branch version-16
cd ../
bench install-app ks_item_price_history
```

### Post-Installation

After installation, migrate the database to create necessary tables and DocTypes:

```bash
bench migrate
bench build
```

---

## Configuration

Once installed, the app is ready to use without additional configuration. Price history will be automatically tracked as items are created and updated in your system.

---

## Development

### Setup Development Environment

Install pre-commit to ensure code quality and consistency:

```bash
cd apps/ks_item_price_history
pre-commit install
```

### Code Quality Tools

This project uses the following tools for maintaining code quality:

- **[Ruff](https://github.com/astral-sh/ruff)**: Fast Python linter and code formatter
- **[ESLint](https://eslint.org/)**: JavaScript linting utility
- **[Prettier](https://prettier.io/)**: Code formatter for JavaScript and JSON
- **[Pyupgrade](https://github.com/asottile/pyupgrade)**: Tool to upgrade Python syntax

### Running Pre-commit Checks

To manually run pre-commit checks on all files:

```bash
cd apps/ks_item_price_history
pre-commit run --all-files
```

### Contributing Guidelines

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Ensure pre-commit checks pass (`pre-commit run --all-files`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

Before submitting a PR, please ensure:
- All code follows the project's style guidelines (enforced by pre-commit)
- Your changes are tested
- Documentation is updated if needed

---

## Usage

### Accessing Item Price History

1. Navigate to any Item in your ERPNext system
2. View the price history section to see all historical prices
3. The last selling price is prominently displayed for quick reference

### Generating Reports

Use the built-in report features to analyze pricing trends and patterns across your inventory.

---

## API Documentation

The app provides REST APIs for programmatic access to price history data. See the [API Documentation](./docs/api.md) for detailed information.

---

## Troubleshooting

### Common Issues

**Issue**: Prices not showing in history

**Solution**: Ensure that the app has been properly installed and migrated. Run:
```bash
bench migrate
bench build
bench clear-cache
```

**Issue**: Performance degradation with large price history

**Solution**: The app includes database indexing for optimal performance. If you experience slowdowns, consider archiving old price records or implementing custom data retention policies.

---

## Support

For issues, questions, or feature requests, please:

- **Open an Issue**: [GitHub Issues](https://github.com/ksolves/ks_item_price_history/issues)
- **Contact Ksolves**: Visit [ksolves.com](https://www.ksolves.com) or email support@ksolves.com

---

## License

This project is licensed under the **MIT License** - see the [LICENSE](./LICENSE) file for details.

---

## Changelog

### Version 1.0.0 (Initial Release)
- Initial release with core price history tracking functionality
- Last selling price display feature
- Pre-commit configuration for code quality

For detailed changelog, see [CHANGELOG.md](./CHANGELOG.md)

---

## About Ksolves

**Ksolves India Limited** is a leading software development and consulting company specializing in enterprise solutions, open-source technologies, and cloud infrastructure.

- **Website**: [www.ksolves.com](https://www.ksolves.com)
- **GitHub**: [github.com/ksolves](https://github.com/ksolves)
- **Email**: support@ksolves.com

---

## Contributors

This project is maintained by the Ksolves team. Special thanks to all contributors who have helped improve this application.

---

## Disclaimer

This application is provided as-is. Ksolves India Limited is not responsible for any data loss or system issues that may arise from improper usage. Please test thoroughly in a development environment before deploying to production.

---

**Last Updated**: May 2026
