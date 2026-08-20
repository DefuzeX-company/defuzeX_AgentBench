# Agent Documentation Guide

在修改 AgentBench 前，先根据任务范围阅读对应文档。

## CLI

如果需要了解、使用或修改 AgentBench CLI，必须先阅读
[`CLI.md`](./CLI.md)。该文档是 CLI 的规范来源，包含：

- `run`、`view`、`certify` 的完整使用方式；
- 所有 positional arguments、options、默认值和兼容形式；
- 交互提示、退出码、JSONL 结果和 viewer 生命周期；
- `adapting` 到 `ready` 的认证与 Registry 更新规则；
- CLI feature 注册结构和新增命令的实现要求。

修改 CLI 行为、参数、默认值、输出文件或退出码时，必须在同一次改动中更新
`CLI.md` 和相关测试。

## Adding Agents

如果需要新增、移植或验证 Agent，必须阅读
[`How To Add Agent.md`](./How%20To%20Add%20Agent.md)。该文档是短入口，只放
happy path 和阅读路线。

按任务范围继续阅读：

- 下载来的 Agent 还没有完成改造：读 [`Agents/Factory.md`](./Agents/Factory.md)。
- 需要处理 Docker、package-data、JSONL worker 或模型网关：
  读 [`Agents/Runtime.md`](./Agents/Runtime.md)。
- 需要理解 `certify`、`ready`、Judge FAIL 或结果文件：
  读 [`Agents/Certify.md`](./Agents/Certify.md)。
- 已经有具体报错：先查 [`Agents/Troubleshooting.md`](./Agents/Troubleshooting.md)。
- 需要完整背景时，再读 [`Agents/Reference.md`](./Agents/Reference.md)。

当 Agent onboarding 涉及 `agentbench certify` 或普通 batch 选择规则时，同时
阅读 `CLI.md`。
