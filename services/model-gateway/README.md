# DefuzeX Model Gateway

This is the trusted model credential proxy used by AgentBehaviorBench (ABB) Docker runtimes.
It is intentionally packaged and built independently from the Host Harness.

## Responsibilities

- authenticate the temporary per-run credential sent by an Agent container;
- replace it with the real upstream model credential;
- forward requests to the provider endpoint; and
- keep provider credentials outside untrusted Agent containers.

The Gateway does not generate benchmark Cases, judge submissions, load Agent
frameworks, or depend on the DefuzeX SDK. Those are Host Harness concerns.

## Build

```powershell
docker build -t defuzex-agentbench/model-gateway:local .
```

AgentBehaviorBench (ABB) builds this directory through `LocalGatewayImageProvider`. Released
deployments can inject a prebuilt image through `DEFUZEX_MODEL_GATEWAY_IMAGE`.

## Protocol extensions

Trusted packages may expose a protocol object or factory through the
`defuzex.model_gateway.protocols` entry-point group. Agent manifests cannot
install Gateway extensions.
