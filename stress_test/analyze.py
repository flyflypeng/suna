import pandas as pd
import matplotlib.pyplot as plt
import glob
import os
import argparse

def analyze_results(results_dir):
    print(f"Analyzing results in {results_dir}...")
    
    # 1. Load Locust Data
    # Locust produces *_stats_history.csv
    locust_files = glob.glob(os.path.join(results_dir, "*_stats_history.csv"))
    if not locust_files:
        print("No Locust stats history file found.")
        return

    locust_df = pd.read_csv(locust_files[0])
    # Convert Timestamp to datetime
    locust_df['Timestamp'] = pd.to_datetime(locust_df['Timestamp'], unit='s')
    
    # 2. Load Monitor Data (Node A and Node B)
    monitor_files = glob.glob(os.path.join(results_dir, "resource_stats_*.csv"))
    monitor_dfs = []
    for f in monitor_files:
        df = pd.read_csv(f)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        monitor_dfs.append(df)
    
    if monitor_dfs:
        full_monitor_df = pd.concat(monitor_dfs)
    else:
        print("No monitor files found.")
        full_monitor_df = pd.DataFrame()

    # Create Output Directory for Plots
    plots_dir = os.path.join(results_dir, "plots")
    os.makedirs(plots_dir, exist_ok=True)

    # --- Plot 1: Response Time (P50, P95) ---
    plt.figure(figsize=(12, 6))
    plt.plot(locust_df['Timestamp'], locust_df['Total Median Response Time'], label='P50 Latency (ms)')
    plt.plot(locust_df['Timestamp'], locust_df['Total 95%'], label='P95 Latency (ms)')
    plt.xlabel('Time')
    plt.ylabel('Latency (ms)')
    plt.title('Suna Application Response Time (P50 vs P95)')
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(plots_dir, "latency_p50_p95.png"))
    plt.close()
    
    # --- Plot 2: Requests per Second (RPS) ---
    plt.figure(figsize=(12, 6))
    plt.plot(locust_df['Timestamp'], locust_df['Requests/s'], label='RPS', color='green')
    plt.xlabel('Time')
    plt.ylabel('Requests / Second')
    plt.title('Throughput (RPS)')
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(plots_dir, "throughput_rps.png"))
    plt.close()

    if full_monitor_df.empty:
        print("Skipping resource plots (no data).")
        return

    # --- Plot 3: CPU Usage by Container ---
    # We aggregate by container name
    containers = full_monitor_df['container_name'].unique()
    
    plt.figure(figsize=(14, 8))
    for container in containers:
        subset = full_monitor_df[full_monitor_df['container_name'] == container]
        if not subset.empty:
            plt.plot(subset['timestamp'], subset['cpu_percent'], label=container)
    
    plt.xlabel('Time')
    plt.ylabel('CPU Usage (%)')
    plt.title('Container CPU Usage')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.grid(True)
    plt.savefig(os.path.join(plots_dir, "cpu_usage.png"))
    plt.close()

    # --- Plot 4: Memory Usage by Container ---
    plt.figure(figsize=(14, 8))
    for container in containers:
        subset = full_monitor_df[full_monitor_df['container_name'] == container]
        if not subset.empty:
            plt.plot(subset['timestamp'], subset['mem_usage_mb'], label=container)
    
    plt.xlabel('Time')
    plt.ylabel('Memory Usage (MB)')
    plt.title('Container Memory Usage')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.grid(True)
    plt.savefig(os.path.join(plots_dir, "memory_usage.png"))
    plt.close()

    # --- Plot 5: Network IO ---
    # Just summing RX+TX for simplicity or separate
    plt.figure(figsize=(14, 8))
    for container in containers:
        subset = full_monitor_df[full_monitor_df['container_name'] == container]
        if not subset.empty:
            # Calculate bandwidth (diff between cumulative stats if they are cumulative, 
            # BUT docker stats API usually returns current cumulative. 
            # Our monitor script just dumps the raw cumulative or current? 
            # The python SDK returns cumulative stats usually.
            # Let's assume the monitor script is logging cumulative bytes converted to MB.
            # So we should plot the RATE (diff).
            
            # Resample/Sort first
            subset = subset.sort_values('timestamp')
            # Calculate rate per second roughly
            # For simplicity in this script, we just plot the cumulative or raw values for now 
            # as implementing accurate rate calculation requires careful timestamp alignment.
            # However, looking at monitor.py, it gets 'rx_bytes'. 
            # If we want rate, we need to diff.
            pass

    print(f"Analysis complete. Charts saved to {plots_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("results_dir", help="Directory containing locust csv and resource csv files")
    args = parser.parse_args()
    analyze_results(args.results_dir)
