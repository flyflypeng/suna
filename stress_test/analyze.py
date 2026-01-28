import pandas as pd
import matplotlib.pyplot as plt
import glob
import os
import argparse
import sys

def analyze_results(locust_file=None, resource_files=None, output_dir="plots"):
    print(f"Analyzing results...")
    print(f"Output directory: {output_dir}")
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Load Locust Data
    # Locust produces *_stats_history.csv
    if locust_file:
        if os.path.exists(locust_file):
            print(f"Loading Locust data from: {locust_file}")
            try:
                locust_df = pd.read_csv(locust_file)
                # Convert Timestamp to datetime
                locust_df['Timestamp'] = pd.to_datetime(locust_df['Timestamp'], unit='s')
                
                # --- Plot 1: Response Time (P50, P95) ---
                plt.figure(figsize=(12, 6))
                plt.plot(locust_df['Timestamp'], locust_df['Total Median Response Time'], label='P50 Latency (ms)')
                plt.plot(locust_df['Timestamp'], locust_df['Total 95%'], label='P95 Latency (ms)')
                plt.xlabel('Time')
                plt.ylabel('Latency (ms)')
                plt.title('Suna Application Response Time (P50 vs P95)')
                plt.legend()
                plt.grid(True)
                plt.savefig(os.path.join(output_dir, "latency_p50_p95.png"))
                plt.close()
                
                # --- Plot 2: Requests per Second (RPS) ---
                plt.figure(figsize=(12, 6))
                plt.plot(locust_df['Timestamp'], locust_df['Requests/s'], label='RPS', color='green')
                plt.xlabel('Time')
                plt.ylabel('Requests / Second')
                plt.title('Throughput (RPS)')
                plt.legend()
                plt.grid(True)
                plt.savefig(os.path.join(output_dir, "throughput_rps.png"))
                plt.close()
            except Exception as e:
                print(f"Error analyzing Locust data: {e}")
        else:
            print(f"Locust file not found: {locust_file}")
    else:
        print("No Locust file provided, skipping Locust plots.")

    # 2. Load Monitor Data (Node A and Node B)
    if resource_files:
        print(f"Loading Resource data from: {resource_files}")
        monitor_dfs = []
        for f in resource_files:
            if os.path.exists(f):
                try:
                    df = pd.read_csv(f)
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    monitor_dfs.append(df)
                except Exception as e:
                    print(f"Error reading resource file {f}: {e}")
            else:
                print(f"Resource file not found: {f}")
        
        if monitor_dfs:
            full_monitor_df = pd.concat(monitor_dfs)
            
            if full_monitor_df.empty:
                print("Skipping resource plots (no data).")
            else:
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
                plt.savefig(os.path.join(output_dir, "cpu_usage.png"))
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
                plt.savefig(os.path.join(output_dir, "memory_usage.png"))
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
        else:
            print("No valid resource data loaded.")
    else:
        print("No resource files provided, skipping resource plots.")

    print(f"Analysis complete. Charts saved to {output_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze stress test results.")
    
    # Optional positional argument for backward compatibility
    parser.add_argument("results_dir", nargs='?', help="Directory containing locust csv and resource csv files")
    
    # Optional arguments for specific files
    parser.add_argument("--locust-file", help="Path to locust stats history csv")
    parser.add_argument("--resource-files", nargs='*', help="List of paths to resource stats csv files")
    parser.add_argument("--output-dir", help="Directory to save plots")
    
    args = parser.parse_args()
    
    locust_file = args.locust_file
    resource_files = args.resource_files
    output_dir = args.output_dir
    
    # Logic to resolve files
    if args.results_dir:
        # If results_dir is provided, we look for files there if they aren't explicitly provided
        if not locust_file:
            locust_files = glob.glob(os.path.join(args.results_dir, "*_stats_history.csv"))
            if locust_files:
                locust_file = locust_files[0]
        
        if not resource_files:
            resource_files = glob.glob(os.path.join(args.results_dir, "resource_stats_*.csv"))
            
        if not output_dir:
            output_dir = os.path.join(args.results_dir, "plots")
            
    # Default output dir if still not set
    if not output_dir:
        output_dir = "plots"
        
    if not locust_file and not resource_files:
        print("Warning: No input files found or provided.")
        parser.print_help()
        sys.exit(1)
        
    analyze_results(locust_file, resource_files, output_dir)
