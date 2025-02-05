#!/usr/bin/env python
"""
    The MIT License (MIT)

    Copyright (c) 2023 pkjmesra

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.

"""
import os
import sys
import pandas as pd

from PKDevTools.classes.log import default_logger
from PKDevTools.classes import Archiver
from PKDevTools.classes.PKDateUtilities import PKDateUtilities
from PKDevTools.classes.OutputControls import OutputControls
from PKDevTools.classes.ColorText import colorText

from pkscreener.classes import Utility
from pkscreener.classes.Messenger import PKMessenger, DEV_CHANNEL_ID
from pkscreener.classes.PKScanRunner import PKScanRunner
import pkscreener.classes.ConfigManager as ConfigManager

class PKAssetsManager:

    configManager = ConfigManager.tools()
    configManager.getConfig(ConfigManager.parser)
    
    @classmethod
    def generateKiteBasketOrderReviewDetails(self,saveResultsTrimmed,runOptionName,caption,user):
        kite_file_path = os.path.join(Archiver.get_user_data_dir(), f"{runOptionName}_Kite_Basket.html")
        kite_caption=f"Review Kite(Zerodha) Basket order for {runOptionName}  - {caption}"
        global userPassedArgs
        if PKDateUtilities.isTradingTime() or userPassedArgs.log: # Only during market hours
            # Also share the kite_basket html/json file.
            try:
                with pd.option_context('mode.chained_assignment', None):
                    kite_basket_df = pd.DataFrame(columns=["product","exchange","tradingsymbol","quantity","transaction_type","order_type","price"], index=saveResultsTrimmed.index)
                    price = (saveResultsTrimmed["LTP"].astype(float)*0.995).round(1) if "LTP" in saveResultsTrimmed.columns else 0
                    kite_basket_df.loc[:,"price"] = price
                    kite_basket_df["quantity"] = 1
                    kite_basket_df["product"] = "MIS"
                    kite_basket_df["exchange"] = "NSE"
                    kite_basket_df["transaction_type"] = "SELL" if "sell" in caption.lower() or "bear" in caption.lower() else "BUY"
                    kite_basket_df["order_type"] = "LIMIT"
                    kite_basket_df.reset_index(inplace=True)
                    kite_basket_df.reset_index(inplace=True, drop=True)
                    kite_basket_df["tradingsymbol"] = kite_basket_df["Stock"]
                    kite_basket_df.drop("Stock", axis=1, inplace=True, errors="ignore")
                    kite_basket_df.to_json(kite_file_path,orient='records',lines=False)
                    lines = ""
                    with open(kite_file_path, "r") as f:
                        lines = f.read()
                    lines = lines.replace("\"","&quot;").replace("\n","\n,")
                    style = ".center { margin: 0;position: absolute;top: 50%;left: 50%;-ms-transform: translate(-50%, -50%);transform: translate(-50%, -50%);}"
                    htmlContent = f'<html><style>{style}</style><span><form method="post" action="https://kite.zerodha.com/connect/basket" target="_blank"><input type="hidden" name="api_key" value="gcac8p9oowmserd0"><input type="hidden" name="data" value="{lines}"><div class="center"><input type="submit" value="Review Basket Order on Kite" style="width:250px;height:200px;padding: 0.5rem 1rem; font-weight: 700;"></div></form></span></html>'
                    with open(kite_file_path, "w") as f:
                        f.write(htmlContent)
                    # PKMessenger.sendMessageToTelegramChannel(
                    #     message=None,
                    #     document_filePath=kite_file_path,
                    #     caption=kite_caption,
                    #     user=user,
                    # )
                    # os.remove(kite_file_path)
            except Exception as e:  # pragma: no cover
                default_logger().debug(e, exc_info=True)
                pass
        return kite_file_path, kite_caption
    
    @classmethod
    def saveDownloadedData(self,downloadOnly, testing, stockDictPrimary, configManager, loadCount):
        global userPassedArgs, keyboardInterruptEventFired, download_trials
        argsIntraday = userPassedArgs is not None and userPassedArgs.intraday is not None
        intradayConfig = configManager.isIntradayConfig()
        intraday = intradayConfig or argsIntraday
        if not keyboardInterruptEventFired and (downloadOnly or (
            configManager.cacheEnabled and not PKDateUtilities.isTradingTime() and not testing
        )):
            OutputControls().printOutput(
                colorText.GREEN
                + "  [+] Caching Stock Data for future use, Please Wait... "
                + colorText.END,
                end="",
            )
            Utility.tools.saveStockData(stockDictPrimary, configManager, loadCount, intraday)
            if downloadOnly:
                cache_file = Utility.tools.saveStockData(stockDictPrimary, configManager, loadCount, intraday, downloadOnly=downloadOnly)
                cacheFileSize = os.stat(cache_file).st_size if os.path.exists(cache_file) else 0
                if cacheFileSize < 1024*1024*40:
                    try:
                        from PKDevTools.classes import Archiver
                        log_file_path = os.path.join(Archiver.get_user_data_dir(), "pkscreener-logs.txt")
                        message=f"{cache_file} has size: {cacheFileSize}! Something is wrong!"
                        if os.path.exists(log_file_path):
                            PKMessenger.sendMessageToTelegramChannel(caption=message,document_filePath=log_file_path, user=DEV_CHANNEL_ID)
                        else:
                            PKMessenger.sendMessageToTelegramChannel(message=message,user=DEV_CHANNEL_ID)
                    except: # pragma: no cover
                        pass
                    # Let's try again with logging
                    if "PKDevTools_Default_Log_Level" not in os.environ.keys():
                        launcher = f'"{sys.argv[0]}"' if " " in sys.argv[0] else sys.argv[0]
                        launcher = f"python3.12 {launcher}" if (launcher.endswith(".py\"") or launcher.endswith(".py")) else launcher
                        os.system(f"{launcher} -a Y -e -l -d {'-i 1m' if configManager.isIntradayConfig() else ''}")
                    else:
                        del os.environ['PKDevTools_Default_Log_Level']
                        sys.exit(0)
        else:
            OutputControls().printOutput(colorText.GREEN + "  [+] Skipped Saving!" + colorText.END)


    @classmethod
    def saveNotifyResultsFile(
        self,screenResults, saveResults, defaultAnswer, menuChoiceHierarchy, user=None
    ):
        global userPassedArgs, elapsed_time, selectedChoice, media_group_dict,criteria_dateTime
        if user is None and userPassedArgs.user is not None:
            user = userPassedArgs.user
        if ">|" in userPassedArgs.options and not PKAssetsManager.configManager.alwaysExportToExcel:
            # Let the final results be there. We're mid-way through the screening of some
            # piped scan. Do not save the intermediate results.
            return
        caption = f'<b>{menuChoiceHierarchy.split(">")[-1]}</b>'
        if screenResults is not None and len(screenResults) >= 1:
            choices = PKScanRunner.getFormattedChoices(userPassedArgs,selectedChoice)
            if userPassedArgs.progressstatus is not None:
                choices = userPassedArgs.progressstatus.split("=>")[0].split("  [+] ")[1]
            choices = f'{choices.strip()}{"_IA" if userPassedArgs is not None and userPassedArgs.runintradayanalysis else ""}'
            needsCalc = userPassedArgs is not None and userPassedArgs.backtestdaysago is not None
            pastDate = PKDateUtilities.nthPastTradingDateStringFromFutureDate(int(userPassedArgs.backtestdaysago) if needsCalc else 0) if needsCalc else None
            filename = Utility.tools.promptSaveResults(choices,
                saveResults, defaultAnswer=defaultAnswer,pastDate=pastDate,screenResults=screenResults)
            # User triggered telegram bot request
            # Group user Ids are < 0, individual ones are > 0
            # if filename is not None and user is not None and int(str(user)) > 0:
            #     PKMessenger.sendMessageToTelegramChannel(
            #         document_filePath=filename, caption=menuChoiceHierarchy, user=user
            #     )
            if filename is not None:
                if "ATTACHMENTS" not in media_group_dict.keys():
                    media_group_dict["ATTACHMENTS"] = []
                caption = media_group_dict["CAPTION"] if "CAPTION" in media_group_dict.keys() else menuChoiceHierarchy
                media_group_dict["ATTACHMENTS"].append({"FILEPATH":filename,"CAPTION":caption.replace('&','n')})

            OutputControls().printOutput(
                colorText.WARN
                + f"  [+] Notes:\n  [+] 1.Trend calculation is based on 'daysToLookBack'. See configuration.\n  [+] 2.Reduce the console font size to fit all columns on screen.\n  [+] Standard data columns were hidden: {PKAssetsManager.configManager.alwaysHiddenDisplayColumns}. If you want, you can change this in pkscreener.ini"
                + colorText.END
            )
        if userPassedArgs.monitor is None:
            needsCalc = userPassedArgs is not None and userPassedArgs.backtestdaysago is not None
            pastDate = PKDateUtilities.nthPastTradingDateStringFromFutureDate(int(userPassedArgs.backtestdaysago) if needsCalc else 0) if criteria_dateTime is None else criteria_dateTime
            if userPassedArgs.triggertimestamp is None:
                userPassedArgs.triggertimestamp = int(PKDateUtilities.currentDateTimestamp())
            OutputControls().printOutput(
                colorText.GREEN
                + f"  [+] Screening Completed. Found {len(screenResults) if screenResults is not None else 0} results in {round(elapsed_time,2)} sec. for {colorText.END}{colorText.FAIL}{pastDate}{colorText.END}{colorText.GREEN}. Queue Wait Time:{int(PKDateUtilities.currentDateTimestamp()-userPassedArgs.triggertimestamp-round(elapsed_time,2))}s! Press Enter to Continue.."
                + colorText.END
                , enableMultipleLineOutput=True
            )
            if defaultAnswer is None:
                OutputControls().takeUserInput("Press <Enter> to continue...")