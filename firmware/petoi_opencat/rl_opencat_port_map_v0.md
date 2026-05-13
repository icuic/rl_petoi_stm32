# OpenCatEsp32 RL Port Map v0

This note narrows the repo-local RL prototype into concrete upstream patch
locations for `OpenCatEsp32`.

## 1. `src/OpenCat.h`

Add one dedicated RL transport token:

```cpp
#define T_RL_FRAME 'Y'
```

`'Y'` is only a placeholder candidate. The final token should be selected after
checking that Petoi does not already reserve it elsewhere in the active command
surface.

Also add fixed-size state for the RL transport:

```cpp
uint8_t rlResponse[rl_serial_v0::kMaxFrameSize];
size_t rlResponseLen = 0;
```

If the upstream build style prefers zero global C++ objects, the
`DispatchBridge` instance can remain file-static in a dedicated RL helper
translation unit instead of `OpenCat.h`.

## 2. `src/moduleManager.h::read_serial()`

Add a dedicated branch immediately after:

```cpp
token = serialPort->read();
lowerToken = tolower(token);
newCmdIdx = 2;
```

Recommended shape:

```cpp
if (token == T_RL_FRAME) {
  rlFrameReader.Reset();

  uint8_t header[rl_serial_v0::kHeaderSize] = {};
  if (!readExact(serialPort, header, sizeof(header), SERIAL_TIMEOUT)) {
    rlFrameReader.Reset();
    newCmdIdx = 0;
    return;
  }

  rl_serial_v0::FrameView ignored;
  if (rlFrameReader.Feed(header, sizeof(header), &ignored) ==
      rl_frame_reader_v0::FeedStatus::kHeaderInvalid) {
    newCmdIdx = 0;
    return;
  }

  const size_t expected = rlFrameReader.expected_frame_size();
  const size_t remainder = expected - rl_serial_v0::kHeaderSize;
  uint8_t tail[rl_serial_v0::kMaxFrameSize] = {};
  if (!readExact(serialPort, tail, remainder, SERIAL_TIMEOUT)) {
    rlFrameReader.Reset();
    newCmdIdx = 0;
    return;
  }

  rlFrameReader.Feed(tail, remainder, &ignored);
  cmdLen = expected;
  newCmdIdx = 2;
  return;
}
```

Implementation notes:

- do not use the existing `~` terminator path for RL frames
- do not copy arbitrary RL bytes into the legacy `newCmd` string buffer unless
  the upstream patch explicitly chooses that representation
- prefer a small `readExact(...)` helper so timeout and partial-read behavior is
  explicit and testable

## 3. `src/reaction.h`

Add one token case near the other top-level command handlers:

```cpp
case T_RL_FRAME: {
  size_t responseLen = 0;
  const auto status =
      rlDispatchBridge.HandleBufferedFrame(rlResponse,
                                           sizeof(rlResponse),
                                           &responseLen);
  if (status == rl_dispatch_bridge_v0::DispatchStatus::kResponseReady) {
    activeSerialPort->write(rlResponse, responseLen);
  }
  token = '\0';
  break;
}
```

The repo-local `DispatchBridge::Feed(...)` is byte-stream oriented. The upstream
port can either:

1. keep that API and let `read_serial()` feed the frame into it directly, or
2. store the completed frame and add a small `HandleBufferedFrame(...)` wrapper
   for `reaction()`.

The first option is more direct. The second option fits OpenCat's existing
split between input collection and command execution.

## 4. Telemetry Callback Hook

Map the repo-local callback:

```cpp
bool ReadTelemetry(TelemetryState* out, void* userData);
```

to upstream state:

- `roll`, `pitch` from the current IMU orientation storage
- angular velocity xyz from the active IMU source
- eight physical feedback-servo readings through a non-printing helper factored
  out of the existing feedback path

Do not source feedback from text printing or from the public `j` response.

## 5. Target Callback Hook

Map:

```cpp
bool ApplyTargets(const float targets[8], void* userData);
```

to the existing simultaneous multi-joint execution path:

1. convert protocol radians to OpenCat's internal angle representation
2. map policy joint order to OpenCat joint indices
3. write into a local `targetFrame`
4. reuse `transform(...)`
5. reuse `skill->convertTargetToPosture(...)`

## 6. Bring-up Acceptance Criteria

The first real upstream patch is considered useful when:

1. `RL_GET_STATE` returns a valid binary response with matching sequence id
2. `RL_SET_TARGETS` reaches the target callback and returns command-accepted
3. arbitrary payload bytes containing `0x7E` do not break frame acquisition
4. the host Python codec can decode the returned response without special cases

