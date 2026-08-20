# AgentBench CLI

本文档是 AgentBench 命令行界面的完整使用说明。CLI 的安装入口定义在
`pyproject.toml`，实现位于 `agentbench/cli/`。

## 1. 运行前准备

在仓库根目录运行命令：

```powershell
cd C:\Song_startup\benchmark\defuzeX_AgentBench
```

支持两种等价调用方式：

```powershell
python -m agentbench <command> [arguments]
agentbench <command> [arguments]
```

第二种方式要求当前 Python 环境已经安装本项目。运行 benchmark 前还需要：

- Python 3.10 或更高版本。
- `DEFUZEX_API_KEY` 已在当前终端环境中配置。
- Docker Desktop 正在运行（使用 Docker runtime 的 Agent 必需）。
- 已配置目标 Agent 在 `agent.toml` 中声明的模型凭据和其他必要环境变量。
- Agent 已登记在 `resources/registry.toml`，且对应目录、`agent.toml` 和
  requirement 文件存在。

查看根帮助：

```powershell
python -m agentbench --help
```

当前子命令：

| Command | 用途 |
| --- | --- |
| `run` | 批量运行所有启用且状态为 `ready` 的 Agent。 |
| `view` | 用本地网页打开一个已有的 JSONL 结果。 |
| `certify` | 完整测试一个 `adapting` Agent，通过后将其晋升为 `ready`。 |

## 2. 默认命令与兼容用法

`run` 是默认命令。以下两条命令等价：

```powershell
python -m agentbench
python -m agentbench run
```

旧的无子命令参数形式仍然兼容：

```powershell
python -m agentbench --output results\result.json
```

它等价于：

```powershell
python -m agentbench run --output results\result.json
```

根级 `-h` 或 `--help` 显示所有子命令，不会被重写为 `run --help`。

## 3. `run`

### 3.1 语法

```text
agentbench run [-h] [--output PATH]
```

```powershell
python -m agentbench run
python -m agentbench run --output results\result.json
```

### 3.2 Arguments

| Argument | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `-h`, `--help` | 否 | - | 显示 `run` 帮助并退出。 |
| `--output PATH` | 否 | 不保存 | 保存唯一、append-only 的 JSONL 结果，并启动本地 viewer。 |

`PATH` 是结果文件的命名基准，不是最终文件名。AgentBench 会添加时间戳，
并统一输出 `.jsonl`：

```text
--output results\result.json
-> results\result-20260820-162500.jsonl
```

如果同一秒内发生重名，会继续添加 `-2`、`-3` 等编号。已有文件不会被
覆盖，每个事件都会在产生时立即 append，因此中断后已经写入的数据仍然
保留。

不传 `--output` 时：

- benchmark 仍会正常运行；
- 不生成 JSONL trace/result artifact；
- 不启动本地 viewer；
- 终端仍会显示每个 Agent 和最终 suite 结果。

### 3.3 Agent 选择规则

默认运行只选择同时满足以下条件的注册项：

```toml
enabled = true
status = "ready"
```

启用但仍为 `adapting` 的 Agent 不会进入普通 batch。CLI 会显示被排除的
数量，并提示使用 `agentbench certify <agent_id>`。

Registry 顺序决定执行顺序。每个 Agent 的 `case` 字段决定独立 Case 的
运行次数。

### 3.4 确认提示

CLI 展示选中的 Agent 后会询问：

```text
Continue? [yes/no]:
```

接受的输入：

| 结果 | 输入 |
| --- | --- |
| 继续 | `yes`、`y`、`confirm`、`c` |
| 取消 | `no`、`n`、`cancel` 或直接回车 |

取消不是 benchmark 失败，退出码为 `0`。

### 3.5 Result viewer 生命周期

只有传入 `--output` 时，`run` 才会在 benchmark 开始前启动 viewer。终端会
打印 suite URL，每个 Agent 完成后还会打印带 `#agent=<agent_id>` 的直接
链接。

benchmark 运行期间可以打开 URL。viewer 默认不自动刷新，使用网页上的
Refresh 按钮读取最新事件，这样下拉框和当前选择不会因轮询而被打断。

运行结束后 CLI 保持 viewer 存活并询问：

```text
Viewer action? [r rerun/q quit]:
```

| 操作 | 输入 | 行为 |
| --- | --- | --- |
| 重新运行 | `r`、`rerun`、`retry`、`again` | 停止当前 viewer，创建新的 suite 和结果文件，再运行一次。 |
| 退出 | `q`、`quit`、`exit` 或直接回车 | 停止 viewer，并返回本次 benchmark 的退出码。 |

`Ctrl+C` 或输入流结束也会停止 viewer。

## 4. `certify`

### 4.1 语法

```text
agentbench certify [-h] [--output PATH] agent_id
```

最常用的调用：

```powershell
python -m agentbench certify swe-agent
```

### 4.2 Arguments

| Argument | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `agent_id` | 是 | - | `resources/registry.toml` 中目标 Agent 的稳定 ID。 |
| `--output PATH` | 否 | `results\certify-<agent_id>.jsonl` | 自定义认证结果的命名基准。 |
| `-h`, `--help` | 否 | - | 显示 `certify` 帮助并退出。 |

与普通 `run` 不同，`certify` 无论是否传 `--output`，都会保存唯一 JSONL
结果。默认示例：

```text
results\certify-swe-agent-20260820-162500.jsonl
```

自定义命名基准：

```powershell
python -m agentbench certify swe-agent `
  --output results\manual-swe-certification.json
```

### 4.3 允许的 Registry 状态

`certify` 只对一个指定 Agent 操作，不会运行其他 Agent。

| 当前状态 | 行为 |
| --- | --- |
| `adapting` | 执行完整认证；suite 通过后改成 `ready`。 |
| `ready` | 视为已认证，直接返回成功，不重复运行。 |
| `planned`、`blocked` 或其他状态 | 拒绝认证，退出码为 `2`。 |
| `enabled = false` | 拒绝认证，退出码为 `2`。 |
| 未注册 | 拒绝认证，退出码为 `2`。 |

### 4.4 完整认证流程

认证使用与普通 benchmark 相同的可信 host 流程：

1. 加载并验证 Registry、Agent 目录、manifest 和 requirement。
2. 检查 DefuzeX SDK 配置。
3. 启动目标 Agent，包括适用的 Docker build/runtime。
4. 从 DefuzeX Server 生成 Case。
5. 逐个运行 SDK Input。
6. 提交 DefuzeX Judge。
7. append 完整事件和结果到认证 JSONL。
8. 仅当所有要求的 Case 都通过时，将 Registry 状态从 `adapting` 原子更新为
   `ready`。

以下情况都不会晋升：

- Agent 启动、调用或 Judge 失败；
- 任一 Case 未通过；
- 执行被中断；
- 认证过程中 Registry 状态被其他操作修改；
- 目标 Registry block 缺少 `status`。

状态更新只修改目标 Agent 的 `status` 行，保留 Registry 中的字段顺序、注释
和其他 Agent。临时文件与 Registry 位于同一目录，完成后使用原子替换。

### 4.5 为什么认证结束后没有常驻 viewer

`certify` 设计为可被开发者或 CI 非交互调用，因此不会在结束后等待 `q` 或
`r`，也不会启动一个随进程退出而失效的 viewer。终端会打印结果路径和稍后
打开的命令。

认证后查看结果：

```powershell
python -m agentbench view `
  results\certify-swe-agent-20260820-162500.jsonl
```

## 5. `view`

### 5.1 语法

```text
agentbench view [-h] [--host HOST] [--port PORT] result_log
```

```powershell
python -m agentbench view results\result-20260820-162500.jsonl
```

### 5.2 Arguments

| Argument | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `result_log` | 是 | - | 要读取的 AgentBench `.jsonl` 结果文件。 |
| `--host HOST` | 否 | `127.0.0.1` | viewer HTTP server 监听地址。 |
| `--port PORT` | 否 | `8765` | 首选监听端口。 |
| `-h`, `--help` | 否 | - | 显示 `view` 帮助并退出。 |

示例：

```powershell
python -m agentbench view results\result.jsonl --port 9000
python -m agentbench view results\result.jsonl --host 127.0.0.1 --port 0
```

如果指定端口已被占用，viewer 会自动选择一个可用端口。`--port 0` 表示直接
让操作系统选择端口。以 `127.0.0.1` 运行时 viewer 只对本机开放，不需要
Node.js。

终端会输出真实 URL 和结果文件绝对路径：

```text
View: http://127.0.0.1:8765/suite/suite_xxx/
Result log: C:\...\result-20260820-162500.jsonl
```

按 `Ctrl+C` 停止 server。不存在的结果路径会直接报错，不会创建空文件。

## 6. JSONL 结果与中断恢复

结果文件是 append-only 事件流，可能包含：

| Event | 含义 |
| --- | --- |
| `run_started` | suite ID 和选中的 Agent。 |
| `step_started` | 一个 SDK Input 已开始，包含输入 ID 和 payload。 |
| `step_completed` | Input 调用成功，包含标准输出与 trace-like raw state。 |
| `step_failed` | Input 调用失败，包含错误类型、消息和已获得的输出。 |
| `agent_completed` | 一个 Agent 的 Case、报告和错误汇总。 |
| `suite_completed` | suite 的 passed、failed、skipped 和 selected 汇总。 |
| `suite_failed` | suite 在共享配置阶段失败。 |

进程中断时，文件可能没有 `suite_completed`。viewer 会将它标记为
`running_or_interrupted`，但已经 append 的 Case、step 和错误仍然可以查看。

结果可能包含输入、输出、raw adapter state 和错误消息。分享或提交结果文件
前应检查是否含有敏感数据。

## 7. 退出码

| Exit code | 适用命令 | 含义 |
| --- | --- | --- |
| `0` | `run` | 用户取消，或所有选中 benchmark 通过。 |
| `0` | `certify` | 认证通过并晋升，或 Agent 已经是 `ready`。 |
| `0` | `view` | viewer 被正常停止。 |
| `1` | `run` | 没有可运行的 ready Agent、共享配置失败，或至少一个 benchmark 未通过。 |
| `1` | `certify` | 完整认证 suite 未通过或共享配置失败。 |
| `2` | `certify` | Agent 不存在、被禁用、状态不允许，或通过后 Registry 更新失败。 |
| `2` | 所有命令 | `argparse` 检测到未知命令、未知 argument 或缺少必填 argument。 |

未被 CLI 转换的异常，例如 `view` 文件不存在，通常由 Python 以非零状态退出
并打印异常信息。

## 8. 常见问题

### 普通运行没有生成 JSONL 或 trace

确认使用了 `--output`：

```powershell
python -m agentbench run --output results\result.json
```

普通 `run` 不传 `--output` 时不会保存结果。`certify` 不受此限制，它始终
保存认证结果。

### `adapting` Agent 没出现在普通 run 中

这是预期行为。使用：

```powershell
python -m agentbench certify <agent_id>
```

认证通过后 Registry 自动变为 `ready`，下一次普通 `run` 才会选择它。

### certify 通过了 benchmark，但 Registry 没更新

查看终端最后一行。若认证期间 Registry 状态被修改，或目标 block 缺少
`status`，CLI 会拒绝覆盖并返回 `2`。先检查 `resources/registry.toml`，再重新
认证。

### viewer 打不开默认端口

以终端实际打印的 URL 为准。端口 `8765` 被占用时，CLI 会选择另一个端口。
防火墙或代理异常时，可以显式使用：

```powershell
python -m agentbench view <result.jsonl> --host 127.0.0.1 --port 0
```

### Docker Agent 在启动阶段失败

确认 Docker Desktop 正在运行，并检查 Agent 的 Dockerfile、worker 命令和
`agent.toml`。AgentBench 使用 read-only root filesystem，并把 `/tmp` 挂载为
每次运行全新的 writable tmpfs；完整适配约束见 `How To Add Agent.md`。

## 9. CLI 开发结构

CLI 使用显式 feature 注册表，不在根入口硬编码命令分支：

```text
agentbench/cli/
  main.py                 root parser 与 feature dispatch
  execution.py            共享 benchmark 执行和结果写入
  presentation.py         终端展示与交互
  registry_status.py      Registry 状态更新
  result_export.py        append-only JSONL writer
  viewer.py               本地 HTTP viewer server
  features/
    base.py               CommandFeature 契约
    __init__.py           FEATURES 注册表
    run.py                run 参数与工作流
    view.py               view 参数与工作流
    certify.py            certify 参数与工作流
```

新增子命令时：

1. 在 `agentbench/cli/features/` 新建独立模块。
2. 实现 `configure_parser(parser)` 和 `execute(args)`。
3. 导出一个 `CommandFeature`。
4. 在 `features/__init__.py` 的 `FEATURES` 中注册。
5. 将共享行为放入 CLI 公共模块，不复制 benchmark 或 viewer 生命周期逻辑。
6. 添加 parser dispatch、成功、失败和边界测试。
7. 同步更新本文档中的命令、arguments、退出码和示例。

保持且只能有一个 `default=True` 的 feature。当前默认 feature 是 `run`。
