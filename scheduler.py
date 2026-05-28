# scheduler.py
import schedule
import time
from agent_stock_analyzer import StockAnalysisAgent

def run_analysis():
    """Run stock analysis job"""
    print(f"\n{'='*60}")
    print(f"Starting analysis at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    agent = StockAnalysisAgent()
    try:
        results = agent.run_analysis_all_stocks()
        print(f"\nAnalysis complete. {len(results)} stocks analyzed.\n")
    except Exception as e:
        print(f"Error during analysis: {str(e)}\n")

def schedule_job():
    """Schedule the job to run every hour"""
    schedule.every().hour.do(run_analysis)
    
    print("Stock Analysis Agent scheduler started")
    print(f"Agent configured:")
    agent = StockAnalysisAgent()
    print(f"  - Ollama Host: {agent.ollama_host}")
    print(f"  - Ollama Model: {agent.ollama_model}")
    print(f"  - Stocks to analyze: {len(agent.stocks)}")
    print(f"  - WhatsApp Enabled: {agent.enable_whatsapp_send}")
    print(f"\nSchedule: Every hour at the top of the hour")
    print(f"Next run: {schedule.next_run()}\n")
    
    # Run immediately on start
    run_analysis()
    
    # Keep running
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        print("\nScheduler stopped by user")

if __name__ == "__main__":
    schedule_job()

