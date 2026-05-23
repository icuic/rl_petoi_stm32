# Reverse SSH Recovery For Local Ubuntu

This project uses the cloud server as a temporary relay so Codex can reach the
local Ubuntu host connected to the Bittle hardware.

The local Ubuntu host is stable, but the cloud server is disposable. When a new
cloud server is created, rebuild only the reverse tunnel. Do not move the Bittle
or change the local project path.

## Current Local Host

```text
local Ubuntu SSH target from LAN: ubuntu@192.168.0.154 -p 58985
local project path: /mnt/sda5/rl_petoi_stm32
Bittle serial device: /dev/ttyACM0
cloud-side reverse SSH port: 127.0.0.1:60022
```

The cloud server should not expose port `60022` publicly. Keep it bound to
`127.0.0.1` on the cloud server. Only the FRP control port needs to be reachable
from the local Ubuntu network.

## Before The Old Cloud Server Expires

```text
[ ] Commit and push project changes.
[ ] Make an artifact archive if training/checkpoint outputs changed.
[ ] Keep the local Ubuntu project synced with the pushed branch.
[ ] Record the local SSH port, project path, and Bittle serial path.
[ ] When the new cloud server exists, add its SSH public key to local Ubuntu.
```

If the old tunnel is still alive, the new cloud public key can be appended from
the old cloud server:

```bash
ssh -p 60022 ubuntu@127.0.0.1 'mkdir -p ~/.ssh && chmod 700 ~/.ssh'
ssh -p 60022 ubuntu@127.0.0.1 'printf "%s\n" "NEW_CLOUD_PUBLIC_KEY" >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'
```

Do not commit private keys or FRP tokens.

## New Cloud Server Setup

On the new cloud server:

```bash
git clone <repo-url> ~/rl_petoi_stm32
cd ~/rl_petoi_stm32
mkdir -p .tools/frp
```

Recommended one-command setup:

```bash
FRP_TOKEN="TOKEN_FROM_LOCAL_UBUNTU_FRPC_TOML" \
bash scripts/setup_reverse_ssh_frp.sh server --print-client --start
```

The command downloads FRP into ignored `.tools/frp/`, writes
`.tools/frp/frps.toml`, prints the matching local `frpc.toml`, and starts
`frps`. Use the token already stored in the local Ubuntu
`/usr/local/frp/frpc.toml` if you want to keep the local `frpc` service config
stable across cloud server replacements.

If `.tools/frp/frps.toml` already exists on a server, the setup script can reuse
its existing `auth.token`:

```bash
bash scripts/setup_reverse_ssh_frp.sh server --print-client --start
```

For a replacement cloud server, reuse the same token as the local Ubuntu
`frpc.toml`. Keep that token outside Git, for example in a password manager or a
private setup note.

Download the FRP release that matches the cloud CPU architecture. For x86_64
Linux:

```bash
curl -L -o /tmp/frp.tar.gz https://github.com/fatedier/frp/releases/download/v0.64.0/frp_0.64.0_linux_amd64.tar.gz
tar -xzf /tmp/frp.tar.gz -C /tmp
cp /tmp/frp_0.64.0_linux_amd64/frps .tools/frp/frps
chmod +x .tools/frp/frps
```

Create `.tools/frp/frps.toml`:

```toml
bindAddr = "0.0.0.0"
bindPort = 7000
proxyBindAddr = "127.0.0.1"

auth.method = "token"
auth.token = "REPLACE_WITH_A_RANDOM_TOKEN"
```

Start `frps`:

```bash
.tools/frp/frps -c .tools/frp/frps.toml
```

Keep this process running during hardware debugging. If using a firewall or
cloud security group, allow inbound TCP `7000` from the local network that runs
`frpc`.

## Local Ubuntu frpc Setup

On the local Ubuntu host, point `frpc` at the new cloud public IP:

```toml
serverAddr = "NEW_CLOUD_PUBLIC_IP"
serverPort = 7000

auth.method = "token"
auth.token = "SAME_RANDOM_TOKEN_AS_FRPS"

[[proxies]]
name = "local-ubuntu-ssh"
type = "tcp"
localIP = "127.0.0.1"
localPort = 58985
remotePort = 60022
```

For the current local Ubuntu system, edit:

```bash
sudo nano /usr/local/frp/frpc.toml
```

Change only:

```toml
serverAddr = "NEW_CLOUD_PUBLIC_IP"
```

The existing `auth.token` can remain unchanged. Then restart `frpc`:

```bash
sudo systemctl restart frpc
sudo systemctl status frpc
```

If this repository is also checked out on local Ubuntu, the client config can be
written with:

```bash
FRP_TOKEN="SAME_RANDOM_TOKEN_AS_FRPS" \
FRP_SERVER_ADDR="NEW_CLOUD_PUBLIC_IP" \
bash scripts/setup_reverse_ssh_frp.sh client
```

## Verify From The New Cloud Server

From the new cloud server:

```bash
ssh -p 60022 ubuntu@127.0.0.1 'hostname && whoami && pwd'
ssh -p 60022 ubuntu@127.0.0.1 'cd /mnt/sda5/rl_petoi_stm32 && git status --short'
ssh -p 60022 ubuntu@127.0.0.1 'ls -l /dev/ttyACM0'
```

After this passes, hardware commands should be run through the existing project
scripts, for example:

```bash
ssh -p 60022 ubuntu@127.0.0.1 'cd /mnt/sda5/rl_petoi_stm32 && bash scripts/bittle_bringup_probe.sh --port /dev/ttyACM0 --get-state'
```

## Expected Recovery Time

If FRP binaries are available and the local `frpc` config is edited correctly,
the new cloud server should regain SSH access to local Ubuntu in about 5 to 10
minutes.
