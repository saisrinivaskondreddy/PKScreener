# PKScreener Documentation

Welcome to the PKScreener developer documentation. This documentation is designed to help contributors understand the codebase and make meaningful contributions.

## Quick Links

| Document | Description |
|----------|-------------|
| [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) | Getting started, project structure, development workflow |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture, component details, data flow |
| [SCAN_WORKFLOWS.md](SCAN_WORKFLOWS.md) | Detailed scan category workflows, option formats |
| [API_REFERENCE.md](API_REFERENCE.md) | Key classes, methods, and function signatures |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | Contribution guidelines, code of conduct |

## Overview

PKScreener is a stock screening and analysis tool that provides:

- **47+ Technical Scanners**: From breakouts to chart patterns
- **Multi-Index Support**: NSE, NASDAQ, sectoral indices
- **Backtesting**: Historical performance analysis
- **Piped Scanners**: Chain multiple filters together
- **Telegram Bot**: Automated alerts and commands
- **CLI Interface**: Powerful command-line access

## Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interfaces                          │
│     CLI (pkscreenercli.py) │ Bot (pkscreenerbot.py)        │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                  Core Orchestration                          │
│                     globals.py                               │
│   main() → getScannerMenuChoices() → runScanners()          │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   Screening Engine                           │
│   StockScreener → ScreeningStatistics → Pktalib            │
│              (47+ validation methods)                        │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                     Data Layer                               │
│      Fetcher → DataLoader → AssetsManager                   │
│   (Yahoo Finance, NSE, GitHub cached data)                  │
└─────────────────────────────────────────────────────────────┘
```

## Key Concepts

### Option String Format
```
MenuOption:IndexOption:ExecuteOption:SubOptions

X:12:7:4 = Scanner → All Nifty → Chart Patterns → VCP
```

### Piped Scanners
```
X:12:9:2.5:>|X:0:31:>|X:0:27:
Volume>2.5x → High Momentum → ATR Cross
```

## Getting Started

1. **Read the [Developer Guide](DEVELOPER_GUIDE.md)** for project setup
2. **Understand the [Architecture](ARCHITECTURE.md)** for system design
3. **Explore [Scan Workflows](SCAN_WORKFLOWS.md)** for scanner details
4. **Reference the [API](API_REFERENCE.md)** for implementation details

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for:
- Code style guidelines
- Pull request process
- Testing requirements
- Issue reporting

## Support

- **Issues**: [GitHub Issues](https://github.com/pkjmesra/PKScreener/issues)
- **Discussions**: [GitHub Discussions](https://github.com/pkjmesra/PKScreener/discussions)
