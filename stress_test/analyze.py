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
                # --- Pre-calculate Rates for all data ---
                # We need to calculate rates because stats are cumulative
                # Sort first to ensure diff works correctly
                full_monitor_df = full_monitor_df.sort_values(['container_name', 'timestamp'])
                
                # Calculate diffs grouped by container
                for col in ['net_rx_mb', 'net_tx_mb', 'disk_read_mb', 'disk_write_mb']:
                    full_monitor_df[f'{col}_diff'] = full_monitor_df.groupby('container_name')[col].diff()
                
                # Calculate time diff in seconds
                full_monitor_df['time_diff'] = full_monitor_df.groupby('container_name')['timestamp'].diff().dt.total_seconds()
                
                # Calculate rates (MB/s)
                for col in ['net_rx_mb', 'net_tx_mb', 'disk_read_mb', 'disk_write_mb']:
                    rate_col = f'{col}_rate'
                    full_monitor_df[rate_col] = full_monitor_df[f'{col}_diff'] / full_monitor_df['time_diff']
                    # Clean up invalid rates (inf, negative, nan)
                    full_monitor_df.loc[full_monitor_df[rate_col] < 0, rate_col] = 0
                    full_monitor_df[rate_col] = full_monitor_df[rate_col].fillna(0)

                # --- Group Containers by Prefix ---
                containers = full_monitor_df['container_name'].unique()
                grouped_containers = {}
                for container in containers:
                    # Get prefix (part before first dash)
                    if '-' in container:
                        prefix = container.split('-')[0]
                    else:
                        prefix = "other" # Default group for names without dash
                    
                    if prefix not in grouped_containers:
                        grouped_containers[prefix] = []
                    grouped_containers[prefix].append(container)
                
                print(f"Detected container groups: {list(grouped_containers.keys())}")

                # --- Generate Plots for Each Group ---
                for prefix, group_containers in grouped_containers.items():
                    print(f"Plotting charts for group: {prefix} ({len(group_containers)} containers)")
                    
                    # Generate a color map for this group
                    num_group_containers = len(group_containers)
                    colors = cm.get_cmap('tab20', num_group_containers) if num_group_containers <= 20 else cm.get_cmap('nipy_spectral', num_group_containers)
                    container_colors = {c: colors(i) for i, c in enumerate(group_containers)}
                    
                    # Helper function to add line labels
                    def add_line_label(subset, col_name, label_text, color):
                         if not subset.empty:
                            plt.annotate(label_text, 
                                         xy=(subset['timestamp'].iloc[-1], subset[col_name].iloc[-1]),
                                         xytext=(5, 0), textcoords='offset points',
                                         color=color, fontsize=8, fontweight='bold')

                    # --- Plot 3: CPU Usage by Container ---
                    plt.figure(figsize=(14, 8))
                    for container in group_containers:
                        subset = full_monitor_df[full_monitor_df['container_name'] == container]
                        if not subset.empty:
                            plt.plot(subset['timestamp'], subset['cpu_percent'], label=container, color=container_colors[container])
                            add_line_label(subset, 'cpu_percent', container, container_colors[container])
                    
                    plt.xlabel('Time')
                    plt.ylabel('CPU Usage (%)')
                    plt.title(f'Container CPU Usage ({prefix})')
                    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', ncol=1 if num_group_containers < 15 else 2)
                    plt.tight_layout()
                    plt.grid(True)
                    plt.savefig(os.path.join(output_dir, f"cpu_usage_{prefix}.png"))
                    plt.close()

                    # --- Plot 4: Memory Usage by Container ---
                    plt.figure(figsize=(14, 8))
                    for container in group_containers:
                        subset = full_monitor_df[full_monitor_df['container_name'] == container]
                        if not subset.empty:
                            plt.plot(subset['timestamp'], subset['mem_usage_mb'], label=container, color=container_colors[container])
                            add_line_label(subset, 'mem_usage_mb', container, container_colors[container])
                    
                    plt.xlabel('Time')
                    plt.ylabel('Memory Usage (MB)')
                    plt.title(f'Container Memory Usage ({prefix})')
                    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', ncol=1 if num_group_containers < 15 else 2)
                    plt.tight_layout()
                    plt.grid(True)
                    plt.savefig(os.path.join(output_dir, f"memory_usage_{prefix}.png"))
                    plt.close()

                    # --- Plot 5: Network IO ---
                    plt.figure(figsize=(14, 8))
                    for container in group_containers:
                        subset = full_monitor_df[full_monitor_df['container_name'] == container]
                        if not subset.empty:
                            # RX is solid
                            plt.plot(subset['timestamp'], subset['net_rx_mb_rate'], label=f"{container} (RX)", linestyle='-', color=container_colors[container])
                            add_line_label(subset, 'net_rx_mb_rate', f"{container} (RX)", container_colors[container])
                            
                            # TX is dashed
                            plt.plot(subset['timestamp'], subset['net_tx_mb_rate'], label=f"{container} (TX)", linestyle='--', color=container_colors[container], alpha=0.7)
                            add_line_label(subset, 'net_tx_mb_rate', f"{container} (TX)", container_colors[container])
                    
                    plt.xlabel('Time')
                    plt.ylabel('Network Rate (MB/s)')
                    plt.title(f'Container Network I/O Rate ({prefix})')
                    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', ncol=1 if num_group_containers < 15 else 2)
                    plt.grid(True)
                    plt.tight_layout()
                    plt.savefig(os.path.join(output_dir, f"network_io_{prefix}.png"))
                    plt.close()

                    # --- Plot 6: Disk IO ---
                    plt.figure(figsize=(14, 8))
                    for container in group_containers:
                        subset = full_monitor_df[full_monitor_df['container_name'] == container]
                        if not subset.empty:
                            # Read is solid
                            plt.plot(subset['timestamp'], subset['disk_read_mb_rate'], label=f"{container} (Read)", linestyle='-', color=container_colors[container])
                            add_line_label(subset, 'disk_read_mb_rate', f"{container} (Read)", container_colors[container])

                            # Write is dashed
                            plt.plot(subset['timestamp'], subset['disk_write_mb_rate'], label=f"{container} (Write)", linestyle='--', color=container_colors[container], alpha=0.7)
                            add_line_label(subset, 'disk_write_mb_rate', f"{container} (Write)", container_colors[container])
                    
                    plt.ylabel('Disk Rate (MB/s)')
                    plt.xlabel('Time')
                    plt.title(f'Container Disk I/O Rate ({prefix})')
                    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', ncol=1 if num_group_containers < 15 else 2)
                    plt.grid(True)
                    plt.tight_layout()
                    plt.savefig(os.path.join(output_dir, f"disk_io_{prefix}.png"))
                    plt.close()
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
