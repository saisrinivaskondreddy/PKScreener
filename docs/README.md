# PKScreener Documentation

Welcome to the PKScreener developer documentation. This documentation is designed to help contributors understand the codebase and make meaningful contributions.

## Quick Links

| Document | Description |
|----------|-------------|
| [Developer Guide](DEVELOPER_GUIDE.md) | Getting started, project structure, development workflow |
| [Architecture](ARCHITECTURE.md) | System architecture, component details, data flow |
| [High-Performance Data](HIGH_PERFORMANCE_DATA.md) | Real-time data system, in-memory candle store |
| [Scan Workflows](SCAN_WORKFLOWS.md) | Detailed scan category workflows, option formats |
| [API Reference](API_REFERENCE.md) | Key classes, methods, and function signatures |
| [Testing Guide](TESTING.md) | Writing and running tests, mocking guidelines |
| [Contributing](https://github.com/pkjmesra/PKScreener/blob/main/CONTRIBUTING.md) | Contribution guidelines, code of conduct |

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
│                High-Performance Data Layer                   │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ PKBrokers: InMemoryCandleStore (Real-time)            │ │
│  │    ↓ fallback                                          │ │
│  │ PKDevTools: PKDataProvider (Unified Access)           │ │
│  │    ↓ fallback                                          │ │
│  │ Local/Remote Pickle Files (Cached)                    │ │
│  └───────────────────────────────────────────────────────┘ │
│  Intervals: 1m, 2m, 3m, 4m, 5m, 10m, 15m, 30m, 60m, daily  │
└─────────────────────────────────────────────────────────────┘
```

**Data Flow**: See [High-Performance Data](HIGH_PERFORMANCE_DATA.md) for details.

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

See [Contributing Guidelines](https://github.com/pkjmesra/PKScreener/blob/main/CONTRIBUTING.md) for:
- Code style guidelines
- Pull request process
- Testing requirements
- Issue reporting

## Support

- **Issues**: [GitHub Issues](https://github.com/pkjmesra/PKScreener/issues)
- **Discussions**: [GitHub Discussions](https://github.com/pkjmesra/PKScreener/discussions)
