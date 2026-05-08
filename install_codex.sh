#!/bin/bash
clear
echo "==============================================="
echo "        Codex CLI 一键安装脚本 (Ubuntu)"
echo "          自动配置 + 远程连接开启"
echo "==============================================="
sleep 2

# 1. 更新系统
echo -e "\n[1/5] 更新系统软件源..."
sudo apt update && sudo apt upgrade -y > /dev/null 2>&1

# 2. 安装Node.js 20 LTS
echo -e "\n[2/5] 安装 Node.js 20 LTS..."
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - > /dev/null 2>&1
sudo apt install -y nodejs > /dev/null 2>&1

# 3. 安装Codex CLI
echo -e "\n[3/5] 安装 Codex CLI..."
sudo npm install -g @openai/codex --unsafe-perm=true > /dev/null 2>&1

# 4. 配置环境变量
echo -e "\n[4/5] 配置环境变量..."
echo 'export PATH="$PATH:/usr/local/bin"' >> ~/.bashrc
source ~/.bashrc

# 5. 开启远程连接功能
echo -e "\n[5/5] 开启远程连接..."
mkdir -p ~/.codex
cat > ~/.codex/config.toml << EOF
[features]
remote_connections = true
EOF

# 验证结果
echo -e "\n==============================================="
echo -e "✅ 安装完成！验证结果："
node -v
npm -v
codex --version
echo -e "\n🎉 Codex 远程连接已自动开启！"
echo "==============================================="