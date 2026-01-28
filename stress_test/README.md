# Suna 压力测试指南

本文档指导如何在生产环境中对 Suna 超级智能体应用进行压力测试，监控核心指标并生成分析报告。

## 目录结构

*   `locustfile.py`: Locust 压测脚本，模拟用户并发请求。
*   `monitor.py`: 资源监控脚本，采集 Docker 容器的 CPU、内存、IO 指标。
*   `analyze.py`: 数据分析脚本，生成可视化图表。
*   `requirements.txt`: Python 依赖列表。

## 1. 环境准备

将 `stress_test` 目录上传到所有相关机器（Node A, Node B, 压测机）。

在所有机器上安装依赖：

```bash
cd stress_test
pip install -r requirements.txt
```

## 2. 启动资源监控

请在压测开始前，分别在应用节点和沙箱节点启动监控脚本。建议 `--duration` 稍微长于压测时间。

### Node A (Suna App + Supabase)

监控 Supabase 和 Suna 应用容器（假设应用容器名包含 `suna`，请根据实际情况调整 `--patterns`）：

```bash
# 监控时长设为 600秒 (10分钟)，每5秒采样一次
python monitor.py --node-name node_a --interval 5 --duration 600 --patterns "supabase" "suna" --output-dir ./monitor_data
```

### Node B (Daytona Sandbox)

监控 Daytona 沙箱容器：

```bash
python monitor.py --node-name node_b --interval 5 --duration 600 --patterns "daytona" --output-dir ./monitor_data
```

## 3. 执行压测 (Locust)

**重要说明：**
目前的 Locust 脚本已更新为以 **"Agent 任务完整生命周期"** 为统计维度。
- **响应时间 (Response Time)**: 统计的是从发起 `/api/agent/start` 到 `/api/agent-run/{id}` 状态变为 `completed`/`failed` 的完整耗时。这包含了 LLM 推理、工具调用、沙箱执行等所有后台处理时间。
- **RPS (Requests Per Second)**: 代表**每秒完成的任务数** (Tasks Per Second)，而非单纯的 HTTP 请求数。
- **Failure**: 任何触发失败、轮询超时或任务状态为 `failed`/`error` 的情况都会被计为错误。

### 如何获取真实的复杂 Prompt？


为了真实模拟用户行为，建议通过浏览器抓取实际的请求 Payload。

1. **打开浏览器开发者工具**：按 `F12` 打开控制台，切换到 **Network (网络)** 标签页。
2. **设置过滤器**：
   - 在 Network 标签页左上角的搜索框中输入 `start`。
   - 确保勾选 **Preserve log (保留日志)**，防止页面跳转导致记录丢失。
   - 选中 **Fetch/XHR** 过滤器。
3. **触发请求**：在 Suna 前端界面配置好你想要测试的复杂场景，点击发送。
4. **定位请求**：
   - 在列表中找到名称为 `start` (或 `/agent/start`) 的请求。
   - 点击该请求，在右侧面板选择 **Payload** (或 **Request**) 标签。
   - 在 **Form Data** 部分，你可以找到 `prompt` 字段的完整内容。
5. **(推荐) 直接复制 cURL**：
   - 右键点击该请求行 -> **Copy** -> **Copy as cURL (bash)**。
   - 将其粘贴到文本编辑器中，提取 `--form 'prompt="..."'` 中的内容保存到文件。

在压测机上执行。

**前置条件**：你需要获取一个有效的 Suna 用户 API Key（推荐在设置页面创建一个不过期的 API Key 用于压测）。

**配置 Prompt (可选)**:
你可以通过以下环境变量自定义压测发送的 Prompt 内容：
*   `SUNA_TEST_PROMPT`: 直接设置字符串 Prompt。
*   `SUNA_TEST_PROMPT_FILE`: 指定包含 Prompt 内容的文件路径（优先级更高）。

```bash
# 设置环境变量 (必须) - 注意：使用 pk_xxx:sk_xxx 的完整格式
export SUNA_API_KEY="pk_xxxxxxxx:sk_xxxxxxxx"

# (可选) 设置自定义 Prompt 文件
# export SUNA_TEST_PROMPT_FILE="my_complex_task.txt"

# (可选) 设置简单 Prompt 字符串
# export SUNA_TEST_PROMPT="Please write a python script to calculate fibonacci numbers."

# 启动压测
# -u 50: 50个并发用户
# -r 5: 每秒启动5个用户
# --run-time 10m: 运行10分钟
# --host: 目标服务地址 (Node A 的 IP)
locust -f locustfile.py \
    --host http://<NODE_A_IP>:8000 \
    -u 50 -r 5 \
    --run-time 10m \
    --csv=test_results
```

## 4. 数据分析与可视化

压测结束后，请收集所有生成的 CSV 文件。脚本现在支持灵活指定文件路径，不再要求必须放在同一目录。

**使用示例：**

1.  **自动扫描目录（原有用法）**：
    将所有文件放在同一目录下，脚本会自动识别。

    ```bash
    python analyze.py /path/to/results_dir
    ```

2.  **单独分析 Locust 数据**：
    适用于只关心压测性能指标（TPS, 响应时间）的场景。

    ```bash
    python analyze.py --locust-file test_results_stats_history.csv
    ```

3.  **单独分析资源监控数据**：
    适用于只关心服务器资源负载的场景。支持指定多个资源文件。

    ```bash
    python analyze.py --resource-files resource_stats_node_a.csv resource_stats_node_b.csv
    ```

4.  **混合模式（指定所有文件）**：
    明确指定各类文件路径，并将结果输出到自定义目录。

    ```bash
    python analyze.py \
      --locust-file ./data/test_results_stats_history.csv \
      --resource-files ./data/resource_stats_node_a.csv ./data/resource_stats_node_b.csv \
      --output-dir ./my_analysis_report
    ```

脚本将在输出目录（默认为 `plots/`）下生成以下图表：
*   `latency_p50_p95.png`: P50/P95 时延趋势
*   `throughput_rps.png`: 吞吐量 (RPS)
*   `cpu_usage.png`: 容器 CPU 利用率
*   `memory_usage.png`: 容器内存使用量

## 5. 环境清理

在多次压测之间，可能需要清理 Suna 的执行环境（主要是删除所有的 Thread），以防止旧数据干扰或占用过多资源。

可以使用 `clean_suna_env.sh` 脚本来快速删除所有会话。

**用法：**

```bash
# 需要提供 API Key
./clean_suna_env.sh -k "pk_xxxx:sk_xxxx" -u "http://localhost:8000/api"
```

**参数说明：**

*   `-k, --key`: Suna 的 API Key (格式: `pk_xxx:sk_xxx`)。
*   `-u, --url`: Suna API 地址 (默认: `http://localhost:8000/api`)。

该脚本会自动获取所有 Thread 并逐个删除，删除操作会级联清理关联的 Agent 任务和沙箱环境。
