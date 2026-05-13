#ifndef RL_FRAME_READER_V0_H
#define RL_FRAME_READER_V0_H

#include <stddef.h>
#include <stdint.h>

#include "rl_serial_protocol_v0.h"

namespace rl_frame_reader_v0 {

enum class FeedStatus : uint8_t {
  kNeedMore = 0,
  kFrameReady,
  kBufferOverflow,
  kHeaderInvalid,
  kFrameInvalid,
};

class FrameReader {
 public:
  FrameReader();

  void Reset();

  FeedStatus Feed(const uint8_t* data,
                  size_t len,
                  rl_serial_v0::FrameView* out_frame);

  const uint8_t* frame_data() const;
  size_t frame_size() const;
  size_t expected_frame_size() const;

 private:
  uint8_t buffer_[rl_serial_v0::kMaxFrameSize];
  size_t buffered_;
  size_t expected_;
};

}  // namespace rl_frame_reader_v0

#endif  // RL_FRAME_READER_V0_H
