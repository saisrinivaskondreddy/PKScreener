"""
ResultsProcessor - Handles processing and presentation of scan results

This module encapsulates the results processing logic from globals.py
into a clean, testable class structure.
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from PKDevTools.classes.ColorText import colorText
from PKDevTools.classes.OutputControls import OutputControls
from PKDevTools.classes.PKDateUtilities import PKDateUtilities
from PKDevTools.classes import Archiver
from PKDevTools.classes.log import default_logger

from pkscreener.classes import Utility, PortfolioXRay
from pkscreener.classes.Utility import STD_ENCODING


class ResultsProcessor:
    """
    Processes and presents scan results.
    
    Handles:
    - Labeling results for display
    - Removing unknown/invalid entries
    - Applying strategy filters
    - Saving results to files
    - Sending notifications
    """
    
    def __init__(self, config_manager, user_args=None):
        self.config_manager = config_manager
        self.user_args = user_args
        self.strategy_filter: List = []
    
    def label_results(
        self,
        screen_results: pd.DataFrame,
        save_results: pd.DataFrame,
        volume_ratio: float,
        execute_option: int,
        reversal_option: Optional[int],
        menu_option: str
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Label data for printing with appropriate colors and formatting.
        
        Args:
            screen_results: DataFrame with screen results
            save_results: DataFrame with save results
            volume_ratio: Volume ratio threshold
            execute_option: Selected execute option
            reversal_option: Reversal option if applicable
            menu_option: Selected menu option
            
        Returns:
            Tuple of (labeled_screen_results, labeled_save_results)
        """
        from pkscreener.classes.ScreeningStatistics import ScreeningStatistics
        
        if screen_results is None or len(screen_results) == 0:
            return screen_results, save_results
        
        screener = ScreeningStatistics(self.config_manager, default_logger())
        
        try:
            screen_results, save_results = screener.labelDataForPrinting(
                screen_results,
                save_results,
                self.config_manager,
                volume_ratio,
                execute_option,
                reversal_option,
                menu_option
            )
        except Exception as e:
            default_logger().debug(e, exc_info=True)
            # Fallback: try the simpler labeling approach
            pass
        
        return screen_results, save_results
    
    def remove_unknowns(
        self,
        screen_results: pd.DataFrame,
        save_results: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Remove entries with unknown trend values if configured.
        
        Args:
            screen_results: DataFrame with screen results
            save_results: DataFrame with save results
            
        Returns:
            Tuple of (filtered_screen_results, filtered_save_results)
        """
        if screen_results is None or len(screen_results) == 0:
            return screen_results, save_results
        
        if self.config_manager and not self.config_manager.showunknowntrends:
            # Remove rows with "Unknown" in Trend column
            if 'Trend' in save_results.columns:
                mask = save_results['Trend'].astype(str).str.contains('Unknown', case=False) == False
                save_results = save_results[mask]
                
                # Filter screen_results to match
                if len(save_results) > 0:
                    screen_results = screen_results[
                        screen_results.index.isin(
                            [f"NSE%3A{idx}" for idx in save_results.index]
                        ) | screen_results.index.isin(save_results.index)
                    ]
                else:
                    screen_results = pd.DataFrame()
        
        return screen_results, save_results
    
    def apply_strategy_filter(
        self,
        screen_results: pd.DataFrame,
        save_results: pd.DataFrame,
        strategy_filter: List[str]
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Apply strategy filters to results.
        
        Args:
            screen_results: DataFrame with screen results
            save_results: DataFrame with save results
            strategy_filter: List of strategy filter keys
            
        Returns:
            Tuple of (filtered_screen_results, filtered_save_results)
        """
        if not strategy_filter or save_results is None or len(save_results) == 0:
            return screen_results, save_results
        
        try:
            cleaned_results = PortfolioXRay.PortfolioXRay.cleanupData(save_results)
            
            for str_filter in strategy_filter:
                strategy_func = PortfolioXRay.PortfolioXRay.strategyForKey(str_filter)
                if strategy_func:
                    cleaned_results = strategy_func(cleaned_results)
                    save_results = save_results[
                        save_results.index.isin(cleaned_results.index.values)
                    ]
            
            # Filter screen_results to match
            filtered_screen = None
            for stk in save_results.index.values:
                mask = screen_results.index.astype(str).str.contains(f"NSE%3A{stk}")
                df_filter = screen_results[mask == True]
                filtered_screen = pd.concat([filtered_screen, df_filter], axis=0)
            
            if filtered_screen is None or len(filtered_screen) == 0:
                OutputControls().printOutput(
                    f"{colorText.FAIL}  [+] No results matching selected strategies!{colorText.END}"
                )
                return pd.DataFrame(), save_results
            
            screen_results = filtered_screen
            
        except Exception as e:
            default_logger().debug(e, exc_info=True)
        
        return screen_results, save_results
    
    def remove_unused_columns(
        self,
        screen_results: pd.DataFrame,
        save_results: pd.DataFrame,
        columns_to_remove: List[str]
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Remove specified columns from results"""
        for col in columns_to_remove:
            if screen_results is not None and col in screen_results.columns:
                screen_results.drop(columns=[col], inplace=True, errors='ignore')
            if save_results is not None and col in save_results.columns:
                save_results.drop(columns=[col], inplace=True, errors='ignore')
        
        return screen_results, save_results
    
    def format_for_display(
        self,
        screen_results: pd.DataFrame,
        save_results: pd.DataFrame
    ) -> str:
        """Format results for console display"""
        if screen_results is None or len(screen_results) == 0:
            return "No stocks found matching the criteria."
        
        try:
            tabulated = colorText.miniTabulator().tabulate(
                screen_results,
                headers="keys",
                tablefmt=colorText.No_Pad_GridFormat,
                maxcolwidths=Utility.tools.getMaxColumnWidths(screen_results)
            ).encode("utf-8").decode(STD_ENCODING)
            return tabulated
        except Exception as e:
            default_logger().debug(e, exc_info=True)
            return str(screen_results)
    
    def save_results_to_file(
        self,
        save_results: pd.DataFrame,
        menu_choice_hierarchy: str,
        file_format: str = "xlsx"
    ) -> Optional[str]:
        """
        Save results to a file.
        
        Args:
            save_results: DataFrame with save results
            menu_choice_hierarchy: Menu path for filename
            file_format: Output file format (xlsx or csv)
            
        Returns:
            Path to saved file or None on error
        """
        if save_results is None or len(save_results) == 0:
            return None
        
        try:
            # Clean up hierarchy for filename
            clean_hierarchy = menu_choice_hierarchy.replace(">", "_").replace(" ", "")
            clean_hierarchy = clean_hierarchy[:50]  # Limit length
            
            timestamp = PKDateUtilities.currentDateTime().strftime("%Y%m%d_%H%M%S")
            filename = f"PKScreener_{clean_hierarchy}_{timestamp}.{file_format}"
            filepath = os.path.join(Archiver.get_user_reports_dir(), filename)
            
            if file_format == "xlsx":
                save_results.to_excel(filepath)
            else:
                save_results.to_csv(filepath)
            
            OutputControls().printOutput(
                f"{colorText.GREEN}  [+] Results saved to: {filepath}{colorText.END}"
            )
            return filepath
            
        except Exception as e:
            default_logger().debug(e, exc_info=True)
            OutputControls().printOutput(
                f"{colorText.FAIL}  [+] Failed to save results: {e}{colorText.END}"
            )
            return None
    
    def get_summary_stats(
        self,
        save_results: pd.DataFrame
    ) -> Dict[str, Any]:
        """Get summary statistics from results"""
        stats = {
            "total_stocks": 0,
            "bullish_count": 0,
            "bearish_count": 0,
            "neutral_count": 0,
            "avg_volume_ratio": 0,
            "avg_change_percent": 0
        }
        
        if save_results is None or len(save_results) == 0:
            return stats
        
        stats["total_stocks"] = len(save_results)
        
        if "Trend" in save_results.columns:
            trend_col = save_results["Trend"].astype(str)
            stats["bullish_count"] = len(trend_col[trend_col.str.contains("Bull|Up|Strong", case=False)])
            stats["bearish_count"] = len(trend_col[trend_col.str.contains("Bear|Down|Weak", case=False)])
            stats["neutral_count"] = stats["total_stocks"] - stats["bullish_count"] - stats["bearish_count"]
        
        if "Volume" in save_results.columns:
            try:
                stats["avg_volume_ratio"] = save_results["Volume"].astype(float).mean()
            except:
                pass
        
        if "%Chng" in save_results.columns:
            try:
                stats["avg_change_percent"] = save_results["%Chng"].astype(float).mean()
            except:
                pass
        
        return stats


class BacktestResultsProcessor:
    """Processes and formats backtest results"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
    
    def cleanup_backtest_data(
        self,
        backtest_df: pd.DataFrame,
        xray_df: Optional[pd.DataFrame] = None
    ) -> Tuple[pd.DataFrame, Optional[pd.DataFrame]]:
        """Clean up backtest data for presentation"""
        if backtest_df is None:
            return backtest_df, xray_df
        
        # Remove duplicate rows
        backtest_df = backtest_df.drop_duplicates()
        
        # Sort by date if available
        if "Date" in backtest_df.columns:
            backtest_df = backtest_df.sort_values("Date", ascending=False)
        
        return backtest_df, xray_df
    
    def prepare_grouped_xray(
        self,
        backtest_period: int,
        backtest_df: pd.DataFrame
    ) -> Optional[pd.DataFrame]:
        """Prepare grouped X-Ray analysis of backtest results"""
        if backtest_df is None or len(backtest_df) == 0:
            return None
        
        try:
            xray = PortfolioXRay.PortfolioXRay()
            return xray.prepareGroupedXRay(backtest_period, backtest_df)
        except Exception as e:
            default_logger().debug(e, exc_info=True)
            return None
    
    def get_sorted_backtest_data(
        self,
        backtest_df: pd.DataFrame,
        summary_df: pd.DataFrame,
        sort_keys: List[str]
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Sort backtest data by specified keys"""
        if backtest_df is not None and len(sort_keys) > 0:
            valid_keys = [k for k in sort_keys if k in backtest_df.columns]
            if valid_keys:
                backtest_df = backtest_df.sort_values(valid_keys, ascending=False)
        
        return backtest_df, summary_df
