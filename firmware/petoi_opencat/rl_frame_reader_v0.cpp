#include "rl_frame_reader_v0.h"

#include <string.h>

namespace rl_frame_reader_v0 {

FrameReader::FrameReader() : buffer_{}, buffered_(0), expected_(0) {}

void FrameReader::Reset() {
  buffered_ = 0;
  expected_ = 0;
}

FeedStatus FrameReader::Feed(const uint8_t* data,
                             size_t len,
                             rl_serial_v0::FrameView* out_frame) {
  if (data == nullptr || len == 0) {
    return FeedStatus::kNeedMore;
  }
  if (buffered_ + len > sizeof(buffer_)) {
    Reset();
    return FeedStatus::kBufferOverflow;
  }

  memcpy(buffer_ + buffered_, data, len);
  buffered_ += len;

  if (expected_ == 0 && buffered_ >= rl_serial_v0::kHeaderSize) {
    size_t expected_size = 0;
    if (rl_serial_v0::ExpectedFrameLengthFromHeader(
            buffer_, rl_serial_v0::kHeaderSize, &expected_size) != rl_serial_v0::ParseError::kOk) {
      Reset();
      return FeedStatus::kHeaderInvalid;
    }
    expected_ = expected_size;
  }

  if (expected_ == 0 || buffered_ < expected_) {
    return FeedStatus::kNeedMore;
  }
  if (buffered_ != expected_) {
    Reset();
    return FeedStatus::kFrameInvalid;
  }
  if (rl_serial_v0::DecodeFrame(buffer_, buffered_, out_frame) != rl_serial_v0::ParseError::kOk) {
    Reset();
    return FeedStatus::kFrameInvalid;
  }
  return FeedStatus::kFrameReady;
}

const uint8_t* FrameReader::frame_data() const {
  return buffer_;
}

size_t FrameReader::frame_size() const {
  return buffered_;
}

size_t FrameReader::expected_frame_size() const {
  return expected_;
}

}  // namespace rl_frame_reader_v0
