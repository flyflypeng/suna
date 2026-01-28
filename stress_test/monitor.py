import os
import time
import csv
import argparse
import docker
import re
from datetime import datetime

def parse_io(io_str):
    """
    Parses IO string like '1.2MB / 3.4MB' into tuple of bytes (in, out).
    This is a fallback if we use CLI, but with Docker SDK we get raw bytes.
    """
    pass

def get_container_stats(container):
    try:
        stats = container.stats(stream=False)
        
        # CPU
        # Docker stats calculation is complex.
        # CPU % = (cpu_delta / system_cpu_delta) * number_of_cpus * 100.0
        cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
        system_cpu_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
        number_cpus = stats['cpu_stats']['online_cpus']
        
        if system_cpu_delta > 0.0:
            cpu_percent = (cpu_delta / system_cpu_delta) * number_cpus * 100.0
        else:
            cpu_percent = 0.0

        # Memory
        mem_usage = stats['memory_stats']['usage']
        mem_limit = stats['memory_stats']['limit']
        mem_percent = (mem_usage / mem_limit) * 100.0 if mem_limit > 0 else 0.0

        # Network IO (sum of all networks)
        rx_bytes = 0
        tx_bytes = 0
        if 'networks' in stats:
            for net in stats['networks'].values():
                rx_bytes += net['rx_bytes']
                tx_bytes += net['tx_bytes']

        # Block IO
        read_bytes = 0
        write_bytes = 0
        if 'blkio_stats' in stats and 'io_service_bytes_recursive' in stats['blkio_stats']:
            for entry in stats['blkio_stats']['io_service_bytes_recursive']:
                if entry['op'] == 'Read':
                    read_bytes += entry['value']
                elif entry['op'] == 'Write':
                    write_bytes += entry['value']

        return {
            'cpu_percent': cpu_percent,
            'mem_usage_mb': mem_usage / (1024 * 1024),
            'mem_percent': mem_percent,
            'net_rx_mb': rx_bytes / (1024 * 1024),
            'net_tx_mb': tx_bytes / (1024 * 1024),
            'disk_read_mb': read_bytes / (1024 * 1024),
            'disk_write_mb': write_bytes / (1024 * 1024)
        }
    except Exception as e:
        print(f"Error getting stats for {container.name}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Monitor Docker container resources.')
    parser.add_argument('--node-name', required=True, help='Name of the node (e.g., node_a, node_b)')
    parser.add_argument('--interval', type=int, default=5, help='Sampling interval in seconds')
    parser.add_argument('--duration', type=int, default=300, help='Duration to run in seconds')
    parser.add_argument('--patterns', nargs='+', required=True, help='Regex patterns for container names to monitor')
    parser.add_argument('--output-dir', help='Directory to save output CSV file')
    
    args = parser.parse_args()
    
    client = docker.from_env()
    filename = f'resource_stats_{args.node_name}.csv'
    
    if args.output_dir:
        if not os.path.exists(args.output_dir):
            os.makedirs(args.output_dir)
        output_file = os.path.join(args.output_dir, filename)
    else:
        output_file = filename
    
    print(f"Starting monitor on {args.node_name}. Output: {output_file}")
    print(f"Monitoring patterns: {args.patterns}")

    # Compile regex patterns
    regex_list = [re.compile(p) for p in args.patterns]

    with open(output_file, 'w', newline='') as csvfile:
        fieldnames = ['timestamp', 'container_name', 'cpu_percent', 'mem_percent', 'mem_usage_mb', 'net_rx_mb', 'net_tx_mb', 'disk_read_mb', 'disk_write_mb']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        start_time = time.time()
        
        try:
            while time.time() - start_time < args.duration:
                iteration_start = time.time()
                timestamp = datetime.now().isoformat()
                
                try:
                    all_containers = client.containers.list()
                    target_containers = []
                    
                    for c in all_containers:
                        for regex in regex_list:
                            if regex.search(c.name):
                                target_containers.append(c)
                                break
                    
                    if not target_containers:
                        print("No matching containers found.")
                    
                    for container in target_containers:
                        stats = get_container_stats(container)
                        if stats:
                            row = {'timestamp': timestamp, 'container_name': container.name}
                            row.update(stats)
                            writer.writerow(row)
                            print(f"[{timestamp}] Recorded stats for {container.name}")
                    
                    # Flush data to disk immediately to prevent data loss on interruption
                    csvfile.flush()
                            
                except Exception as e:
                    print(f"Error during monitoring loop: {e}")

                # Sleep for the remainder of the interval
                elapsed = time.time() - iteration_start
                sleep_time = max(0, args.interval - elapsed)
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            print("\nMonitoring stopped by user. Saving data and exiting...")


if __name__ == "__main__":
    main()
