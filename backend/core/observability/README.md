# Viewer.py 使用指南

`viewer.py` 是一个用于分析本地可观测性日志（Metrics Logs）的命令行工具。它可以解析 `metrics_logs.jsonl` 文件，并提供关于 Agent 执行、LLM 调用、工具使用、沙箱操作等的详细统计和性能分析。

## 功能特性

*   **自动日志发现**：自动查找 `logs/` 目录下最新的日志文件（支持 `metrics_logs_YYYYMMDD_HHMMSS.jsonl` 格式）。
*   **多维度分析**：
    *   **Agent 执行**：总运行次数、持续时间统计。
    *   **LLM 统计**：模型调用次数、Token 消耗、响应时间、Token 细分（Prompt/Completion）。
    *   **工具使用**：各工具的调用频率、耗时、错误率。
    *   **沙箱操作**：沙箱环境中的操作统计。
    *   **上下文管理**：任务创建、更新等上下文操作的统计。
    *   **记忆管理**：核心记忆（Core Memory）操作的统计。
*   **性能分析**：端到端会话时长、各组件（LLM、Tool、Sandbox）耗时、并行/重叠执行时间分析。
*   **Trace 过滤**：支持查看所有 Trace 的摘要，或指定 Trace ID 查看详细详情。

## 使用方法

### 基本用法

在项目根目录下运行以下命令：

```bash
python3 backend/core/observability/viewer.py
```

如果不指定参数，工具将自动加载 `logs/` 目录下最新的日志文件，并输出所有 Trace 的摘要信息以及详细分析。

### 常用参数

| 参数 | 说明 | 示例 |
| :--- | :--- | :--- |
| `--file` | 指定要分析的日志文件路径。如果不指定，默认使用最新的日志文件。 | `python3 viewer.py --file logs/metrics_logs_20231027_103000.jsonl` |
| `--trace-id` | 仅分析指定的 Trace ID。 | `python3 viewer.py --trace-id <UUID>` |
| `-h`, `--help` | 显示帮助信息。 | `python3 viewer.py -h` |

### 输出示例

运行工具后，你将看到类似以下的统计信息：

```text
Found 1 traces:
Trace ID                                 Events     Start Time                     Duration (s)   
----------------------------------------------------------------------------------------------------
a1b2c3d4-e5f6-...                        50         2023-10-27T10:30:00+00:00      12.50          

####################################################################################################
TRACE: a1b2c3d4-e5f6-...
####################################################################################################

--- End-to-End Performance Statistics ---
Total Session Duration: 12.50 s
...

--- Agent Execution Summary ---
Total Agent Runs: 1
Total Run Duration: 12500.00 ms
...

--- LLM Statistics ---
Model Name                               Count      Total Dur (ms)  Avg Dur (ms)    Avg Tokens      Errors    
-------------------------------------------------------------------------------------------------------------------
gpt-4                                    5          5000.00         1000.00         150             0         
...
```

## 注意事项

*   日志文件默认存储在项目根目录下的 `logs/` 文件夹中。
*   工具依赖 `metrics_logs.jsonl` 文件的格式，该文件由 `LocalMetricsCollector` 生成。
*   时间戳基于 UTC 时间。
