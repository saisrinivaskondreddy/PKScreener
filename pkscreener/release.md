[![MADE-IN-INDIA](https://img.shields.io/badge/MADE%20WITH%20%E2%9D%A4%20IN-INDIA-orange?style=for-the-badge)](https://en.wikipedia.org/wiki/India) [![GitHub release (latest by date)](https://img.shields.io/github/v/release/pkjmesra/PKScreener?style=for-the-badge)](#) [![GitHub all releases](https://img.shields.io/github/downloads/pkjmesra/PKScreener/total?color=Green&label=Downloads&style=for-the-badge)](#) [![MADE_WITH](https://img.shields.io/badge/BUILT%20USING-PYTHON-yellow?style=for-the-badge&logo=python&logoColor=yellow)](https://www.python.org/)

## What's New?
1. [v0.45.20240813.495] release
* Bullish anchored VWAP implemented under X > 12 > 34. Added these along with VCP in pre-defined piped scanners as well under option 22/23.
* Potential profitable setups (Try menu option 33. X > 12 > 33) with condtions such that 200 MA is rising for at least 3 months, 50 MA is above 200MA, Current price is above 20Osma and preferably above 50 to 100, Current price is at least above 100 % from 52week low, the stock should have made a 52 week high at least once every 4 to 6 month.
* Super confluence option modified to be configurable. In the pkscreener.ini filoe, you can configure which EMAs you would like to have super-confluence tested with. For example, by default it is 8,21,55 but you can change superconfluenceemaperiods to 10,20,55 as well. Similarly, change superconfluencemaxreviewdays to suitable number of days within which you would like the tool to review for super-confluence. By default it is set to 3 days. (8/10 EMA >= 21/20 EMA >= 55 EMA >= 200 SMA within 0-2%). Try X > 12 > 7 > 3 > Option 4.
* Intraday Breakout setup at Day Open (open==low or high with open/close >< previous day high/low price) : Try the X > 12 > 32 option with Buy, Sell or All options.
* Sectoral Indices integrated. Try X > S. Then go on and select whichever scanner menu you would like to select.

## Older Releases
* [https://github.com/pkjmesra/PKScreener/releases] : Discarded to save on storage costs!

## Downloads
| Operating System                                                                                         | Executable File                                                                                                                                                                                                               |
| -------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ![Windows](https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white) | **[pkscreenercli.exe](https://github.com/pkjmesra/PKScreener/releases/download/0.45.20240813.495/pkscreenercli.exe)**                                                                                                         |
| ![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)       | **[pkscreenercli.bin](https://github.com/pkjmesra/PKScreener/releases/download/0.45.20240813.495/pkscreenercli.bin)**                                                                                                         |
| ![Mac OS](https://img.shields.io/badge/mac%20os-D3D3D3?style=for-the-badge&logo=apple&logoColor=000000)  | **[pkscreenercli.run](https://github.com/pkjmesra/PKScreener/releases/download/0.45.20240813.495/pkscreenercli.run)** ([Read Installation Guide](https://github.com/pkjmesra/PKScreener/blob/main/INSTALLATION.md#for-macos)) |

## How to use?

[**Click Here**](https://github.com/pkjmesra/PKScreener) to read the documentation. You can also read it at https://pkscreener.readthedocs.io/en/latest/?badge=latest

## Join our Community Discussion

[**Click Here**](https://github.com/pkjmesra/PKScreener/discussions) to join the community discussion and see what other users are doing!

## Facing an Issue? Found a Bug?

[**Click Here**](https://github.com/pkjmesra/PKScreener/issues/new/choose) to open an Issue so we can fix it for you!

## Want to Contribute?

[**Click Here**](https://github.com/pkjmesra/PKScreener/blob/main/CONTRIBUTING.md) before you start working with us on new features!

## Disclaimer:
* DO NOT use the result provided by the software solely to make your trading decisions.
* Always backtest and analyze the stocks manually before you trade.
* The Author(s) and the software will not be held liable for any losses.

## License
* MIT: https://github.com/pkjmesra/PKScreener/blob/main/LICENSE
