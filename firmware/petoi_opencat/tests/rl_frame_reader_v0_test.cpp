#include "../rl_frame_reader_v0.h"

#include <stdint.h>
#include <stdio.h>
#include <string.h>

namespace {

using namespace rl_frame_reader_v0;
using namespace rl_serial_v0;

bool HexToBytes(const char* hex, uint8_t* out, size_t out_capacity, size_t* out_len) {
  const size_t hex_len = strlen(hex);
  if (hex_len % 2 != 0 || out == nullptr || out_len == nullptr || out_capacity < hex_len / 2) {
    return false;
  }
  for (size_t i = 0; i < hex_len / 2; ++i) {
    unsigned int value = 0;
    if (sscanf(hex + i * 2, "%2x", &value) != 1) {
      return false;
    }
    out[i] = static_cast<uint8_t>(value);
  }
  *out_len = hex_len / 2;
  return true;
}

int Fail(const char* message) {
  fprintf(stderr, "FAIL: %s\n", message);
  return 1;
}

}  // namespace

int main() {
  static const char kStepRequestHex[] =
      "524c000309002000ae47613ed7a3b03f8fc2753e7b14ae3fec51383e8fc2b53f0ad7233eec51b83ffb09";

  uint8_t frame[kMaxFrameSize] = {};
  size_t frame_len = 0;
  if (!HexToBytes(kStepRequestHex, frame, sizeof(frame), &frame_len)) {
    return Fail("failed to parse step request vector");
  }

  FrameReader reader;
  FrameView decoded;
  if (reader.Feed(frame, 3, &decoded) != FeedStatus::kNeedMore) {
    return Fail("reader should wait for more header bytes");
  }
  if (reader.Feed(frame + 3, 5, &decoded) != FeedStatus::kNeedMore) {
    return Fail("reader should infer length and keep waiting");
  }
  if (reader.expected_frame_size() != frame_len) {
    return Fail("reader inferred wrong expected frame length");
  }
  if (reader.Feed(frame + 8, frame_len - 8, &decoded) != FeedStatus::kFrameReady) {
    return Fail("reader failed to emit complete frame");
  }
  if (decoded.message_type != kMsgStepReq || decoded.sequence_id != 9) {
    return Fail("decoded frame metadata mismatch");
  }
  if (reader.frame_size() != frame_len || memcmp(reader.frame_data(), frame, frame_len) != 0) {
    return Fail("reader internal frame buffer mismatch");
  }

  reader.Reset();
  uint8_t bad_header[kHeaderSize] = {'X', 'L', 0x00, kMsgGetStateReq, 0x00, 0x00, 0x00, 0x00};
  if (reader.Feed(bad_header, sizeof(bad_header), &decoded) != FeedStatus::kHeaderInvalid) {
    return Fail("reader failed to reject invalid header");
  }

  puts("rl_frame_reader_v0_test: PASS");
  return 0;
}
