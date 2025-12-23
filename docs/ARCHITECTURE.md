# PKScreener System Architecture

## Overview

PKScreener is built as a modular, multi-process stock screening application with the following architectural principles:
- **Separation of Concerns**: Clear boundaries between UI, business logic, and data layers
- **Parallel Processing**: Multiprocessing for efficient stock screening
- **Extensibility**: Easy addition of new scanners and patterns
- **Multi-Interface Support**: CLI, Telegram Bot, and programmatic access

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PRESENTATION LAYER                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │   CLI Interface │  │  Telegram Bot   │  │  GitHub Actions │             │
│  │ pkscreenercli.py│  │pkscreenerbot.py │  │   Workflows     │             │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘             │
└───────────┼─────────────────────┼─────────────────────┼─────────────────────┘
            │                     │                     │
            ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           APPLICATION LAYER                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        globals.py (Main Orchestrator)                │   │
│  │  • main() - Entry point for all screening operations                │   │
│  │  • runScanners() - Multiprocessing coordinator                      │   │
│  │  • getScannerMenuChoices() - Menu flow management                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌──────────────────┬──────────────┼──────────────┬──────────────────┐     │
│  ▼                  ▼              ▼              ▼                  ▼     │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌───────────┐│
│  │MenuManager │ │MainLogic.py│ │BacktestHdlr│ │ResultsMgr  │ │ConfigMgr  ││
│  │Navigation  │ │ExecuteOpts │ │BacktestUtil│ │ResultsLblr │ │           ││
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘ └───────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
            │                     │                     │
            ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BUSINESS LOGIC LAYER                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     StockScreener.screenStocks()                     │   │
│  │  • Orchestrates the screening process per stock                     │   │
│  │  • Manages parallel execution context                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────┼─────────────────────────────────┐     │
│  ▼                                 ▼                                 ▼     │
│  ┌────────────────────┐ ┌────────────────────┐ ┌────────────────────┐     │
│  │ScreeningStatistics │ │  CandlePatterns    │ │     Pktalib        │     │
│  │• 47+ validators    │ │• Pattern detection │ │• TA-Lib wrapper    │     │
│  │• Technical calcs   │ │• Candlestick types │ │• EMA, SMA, RSI...  │     │
│  └────────────────────┘ └────────────────────┘ └────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
            │                     │                     │
            ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             DATA LAYER                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────┐ ┌────────────────────┐ ┌────────────────────┐      │
│  │     Fetcher.py     │ │   DataLoader.py    │ │  AssetsManager.py  │      │
│  │• Yahoo Finance API │ │• Local caching     │ │• GitHub data sync  │      │
│  │• NSE data sources  │ │• Pickle storage    │ │• Index constituents│      │
│  └────────────────────┘ └────────────────────┘ └────────────────────┘      │
│                                    │                                        │
│  ┌─────────────────────────────────┼─────────────────────────────────┐     │
│  ▼                                 ▼                                 ▼     │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                      External Data Sources                          │    │
│  │  • Yahoo Finance  • NSE India  • Morning Star  • GitHub Actions    │    │
│  └────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Entry Points

#### `pkscreenercli.py`
The CLI entry point that handles:
- Argument parsing (`ArgumentParser`)
- Output control setup (`OutputController`)
- Logging configuration (`LoggerSetup`)
- Dependency checking (`DependencyChecker`)
- Application lifecycle (`ApplicationRunner`)

```python
# Execution flow
def pkscreenercli():
    args = ArgumentParser().parse_args()
    LoggerSetup.setup_logging(args)
    OutputController.setup_output_controller(args)
    runApplicationForScreening()  # Main loop
```

#### `pkscreenerbot.py`
Telegram bot interface using `python-telegram-bot`:
- Command handlers for user interactions
- Inline keyboard menus
- Scan result notifications
- Alert subscriptions

---

### 2. Core Orchestration (globals.py)

The `globals.py` module is the heart of the application, containing:

#### Key Functions

| Function | Purpose |
|----------|---------|
| `main(args)` | Main entry point, orchestrates entire workflow |
| `getScannerMenuChoices()` | Handles menu navigation and option selection |
| `runScanners()` | Multiprocessing coordinator for stock screening |
| `printNotifySaveScreenedResults()` | Result display and notification |
| `finishScreening()` | Cleanup and result persistence |

#### Global State Variables
```python
# Key global variables managed in globals.py
configManager = ConfigManager.tools()    # Configuration
selectedChoice = {}                       # Current menu selections
userPassedArgs = None                    # CLI arguments
keyboardInterruptEvent = None            # Interrupt handling
stockDictPrimary = {}                    # Loaded stock data
```

---

### 3. Menu System

#### MenuOptions.py
Contains all menu definitions as dictionaries:

```python
# Menu hierarchy
level0MenuDict = {           # Main menu (X, P, C, D, etc.)
level1_X_MenuDict = {        # Index selection (0-15, W, S, etc.)
level2_X_MenuDict = {        # Scan options (0-47)
level3_X_Reversal_MenuDict   # Sub-options for reversals
level3_X_ChartPattern_MenuDict  # Sub-options for patterns
# ... etc.
```

#### MenuManager.py
Handles menu rendering and navigation:
- `menus` class - Menu container
- `renderForMenu()` - Display menu options
- `find()` - Locate menu by key

---

### 4. Screening Engine

#### StockScreener.py
Main screening orchestrator:

```python
class StockScreener:
    def screenStocks(self, ...):
        """
        Process a single stock through the screening pipeline.
        
        1. Fetch/validate stock data
        2. Apply pre-filters (volume, price range)
        3. Execute selected screening criteria
        4. Build result dictionaries
        5. Return results tuple
        """
```

#### ScreeningStatistics.py
Contains 47+ validation methods:

| Execute Option | Method | Description |
|----------------|--------|-------------|
| 0 | `validateFullScreen` | Technical overview |
| 1 | `validateBreakout` | Breakout detection |
| 2 | `validateBreakdown` | Breakdown detection |
| 3 | `validateConsolidation` | Range consolidation |
| 4 | `validateLowestVolume` | Volume drying up |
| 5 | `validateRSI` | RSI screening |
| 6 | `validateReversal` | Reversal patterns |
| 7 | `validateChartPattern` | Chart patterns |
| ... | ... | ... |

---

### 5. Multiprocessing Model

```
┌───────────────────────────────────────────────────────────────┐
│                     Main Process                               │
│  globals.py::runScanners()                                    │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Pool = multiprocessing.Pool(processes=cpu_count)       │  │
│  │                                                          │  │
│  │  results = pool.imap_unordered(                         │  │
│  │      StockScreener.screenStocks,                        │  │
│  │      [(stock1, params), (stock2, params), ...]          │  │
│  │  )                                                       │  │
│  └─────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
                              │
           ┌──────────────────┼──────────────────┐
           ▼                  ▼                  ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Worker 1       │ │  Worker 2       │ │  Worker N       │
│  screenStocks() │ │  screenStocks() │ │  screenStocks() │
│  - RELIANCE     │ │  - TCS          │ │  - INFY         │
│  - HDFC         │ │  - WIPRO        │ │  - ...          │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         └───────────────────┴───────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────────┐
│                  Result Aggregation                            │
│  processResults() → lstscreen, lstsave → DataFrame            │
└───────────────────────────────────────────────────────────────┘
```

---

### 6. Data Flow

#### Stock Data Loading
```python
# Data sources priority
1. Local cache (pickle files)
2. GitHub Actions pre-downloaded data
3. Real-time fetch from Yahoo Finance / NSE
```

#### Cache Structure
```
~/.pkscreener/
├── stock_data_DDMMYY.pkl       # Daily OHLCV data
├── stock_data_intraday.pkl     # Intraday data
├── indices/                    # Index constituent lists
└── outputs/                    # Scan results
```

---

### 7. Notification System

```
┌─────────────────────────────────────────────────────────────────┐
│                    TelegramNotifier                              │
├─────────────────────────────────────────────────────────────────┤
│  send_quick_scan_result()                                       │
│    │                                                             │
│    ├── Generate HTML table                                      │
│    ├── Create PNG image (optional)                              │
│    ├── send_message() / send_photo() / send_document()         │
│    └── send_media_group() for multiple attachments              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 PKDevTools.classes.Telegram                      │
│  • is_token_telegram_configured()                               │
│  • send_message()                                               │
│  • send_photo()                                                 │
│  • send_document()                                              │
└─────────────────────────────────────────────────────────────────┘
```

---

### 8. Configuration Management

#### ConfigManager.py
Handles user preferences stored in `pkscreener.ini`:

```ini
[config]
period = 1y
duration = 1d
daysToLookback = 22
minLTP = 20.0
maxLTP = 50000.0
volumeRatio = 2.5
consolidationPercentage = 10
shuffle = True
cacheEnabled = True
stageTwo = True
# ... many more options
```

#### Key Configuration Classes
- `tools()` - Main configuration manager
- `getConfig()` / `setConfig()` - Read/write config
- `toggleConfig()` - Toggle boolean settings

---

## Extension Points

### Adding New Technical Indicators
1. Add to `Pktalib.py` or use `TA-Lib` directly
2. Create validation method in `ScreeningStatistics.py`
3. Register in `StockScreener.py` execute option switch

### Adding New Data Sources
1. Implement fetcher in `Fetcher.py` or new module
2. Integrate with `DataLoader.py` caching
3. Update `AssetsManager.py` if needed

### Adding New Notification Channels
1. Create handler class similar to `TelegramNotifier.py`
2. Integrate with `globals.py::sendMessageToTelegramChannel()`
3. Add configuration options

---

## Performance Considerations

1. **Caching**: Enable `cacheEnabled` in config to avoid re-fetching
2. **Parallel Processing**: Uses all CPU cores by default
3. **Data Filtering**: Apply volume/price filters early to reduce processing
4. **Piped Scanners**: Filter progressively to minimize stock count

---

## See Also
- [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) - Getting started
- [SCAN_WORKFLOWS.md](SCAN_WORKFLOWS.md) - Detailed scan workflows
