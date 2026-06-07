# upstream_patch_preview

这个目录保存针对官方 `OpenCatEsp32` 的预演 patch。

它们的作用不是直接应用，而是把我们已验证过的 repo 内原型映射到上游源码的具体改动位置，方便后续真正同步官方源码时快速落地。

- `0001-opencat-h-rl-token.patch`
- `0002-module-manager-rl-frame-read.patch`
- `0003-reaction-rl-dispatch.patch`
- `0004-opencat-rl-get-state-skeleton.patch`
- `0005-opencat-rl-get-state-real-tree.patch`
- `0006-opencat-add-rl-helper-files.patch`
- `0007-opencat-ble-client-rl-frame.patch`

这些 patch 目前仍是 preview：

- `T_RL_FRAME` 的最终 token 字符还未定案
- `activeSerialPort`
- `rlFrameReader`
- `rlDispatchBridge`
- `FlushBufferedFrame(...)`

这些符号需要在真实上游 patch 中结合最终组织方式统一收口。

其中 `0004-opencat-rl-get-state-skeleton.patch` 更接近第一版真实落地目标：

- 只覆盖 `RL_GET_STATE`
- telemetry 仍使用 stub
- `Serial.write(...)` 先固定走 USB 串口
- 目标是先让上游工程形成第一条可编译、可回包的 bring-up 链路

`0005-opencat-rl-get-state-real-tree.patch` 和 `0006-opencat-add-rl-helper-files.patch` 是基于本地拉取的官方源码树实际落 patch 后回收出的真实 diff，
用于后续继续收敛编译问题和替换 telemetry stub。

`0007-opencat-ble-client-rl-frame.patch` 接入 BLE client notify callback：

- STM32/JDY-23 -> Petoi 的请求仍是 `Y + RL frame`
- Petoi -> STM32/JDY-23 的响应是裸 `RL frame`
- Petoi 响应先在 notify callback 中缓存，再由主循环按 20 字节分片写回 BLE
- 普通 ASCII BLE 命令继续走原 `String` parser fallback
