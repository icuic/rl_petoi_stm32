cmake_minimum_required(VERSION 3.16)

project(stm32h747_m7_inference_smoke C ASM)

set(FIRMWARE_ROOT "${CMAKE_CURRENT_LIST_DIR}/..")
set(STEDGEAI_STAGING_DIR "${FIRMWARE_ROOT}/App/inference/stedgeai" CACHE PATH "Prepared ST Edge AI runtime staging directory")
set(STEDGEAI_GENERATED_DIR "${STEDGEAI_STAGING_DIR}/generated")
set(STEDGEAI_INCLUDE_DIR "${STEDGEAI_STAGING_DIR}/include")
set(STEDGEAI_RUNTIME_LIB "${STEDGEAI_STAGING_DIR}/lib/gcc/stm32h7/NetworkRuntime1200_CM7_GCC.a")
set(LINKER_SCRIPT "${CMAKE_CURRENT_LIST_DIR}/stm32h747xih_m7_smoke.ld")

foreach(required_file
    "${STEDGEAI_GENERATED_DIR}/network.c"
    "${STEDGEAI_GENERATED_DIR}/network_data.c"
    "${STEDGEAI_INCLUDE_DIR}/stai.h"
    "${STEDGEAI_RUNTIME_LIB}")
  if(NOT EXISTS "${required_file}")
    message(FATAL_ERROR "Missing ${required_file}. Run scripts/prepare_stm32_ai_runtime.sh first.")
  endif()
endforeach()

add_executable(m7_inference_smoke.elf
  main.c
  "${FIRMWARE_ROOT}/rl_stedgeai_policy_v0.c"
  "${STEDGEAI_GENERATED_DIR}/network.c"
  "${STEDGEAI_GENERATED_DIR}/network_data.c"
)

target_compile_definitions(m7_inference_smoke.elf PRIVATE
  RL_POLICY_INFERENCE_V0_ENABLE_STEDGEAI
)

target_include_directories(m7_inference_smoke.elf PRIVATE
  "${FIRMWARE_ROOT}"
  "${STEDGEAI_GENERATED_DIR}"
  "${STEDGEAI_INCLUDE_DIR}"
)

target_compile_options(m7_inference_smoke.elf PRIVATE
  -mcpu=cortex-m7
  -mthumb
  -mfloat-abi=hard
  -mfpu=fpv5-d16
  -ffunction-sections
  -fdata-sections
  -Wall
  -Wextra
  -Werror
)

target_link_options(m7_inference_smoke.elf PRIVATE
  -mcpu=cortex-m7
  -mthumb
  -mfloat-abi=hard
  -mfpu=fpv5-d16
  -nostartfiles
  -specs=nosys.specs
  "LINKER:-T,${LINKER_SCRIPT}"
  "LINKER:-Map,${CMAKE_CURRENT_BINARY_DIR}/m7_inference_smoke.map"
  "LINKER:--gc-sections"
  "LINKER:-e,main"
)

target_link_libraries(m7_inference_smoke.elf PRIVATE
  "${STEDGEAI_RUNTIME_LIB}"
  m
)

add_custom_command(TARGET m7_inference_smoke.elf POST_BUILD
  COMMAND ${CMAKE_SIZE} $<TARGET_FILE:m7_inference_smoke.elf>
)
