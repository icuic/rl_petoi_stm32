cmake_minimum_required(VERSION 3.16)

project(stm32h747_m7_inference_smoke C ASM)

set(FIRMWARE_ROOT "${CMAKE_CURRENT_LIST_DIR}/..")
set(STEDGEAI_STAGING_DIR "${FIRMWARE_ROOT}/App/inference/stedgeai" CACHE PATH "Prepared ST Edge AI runtime staging directory")
set(STM32_CMSIS_DIR "${FIRMWARE_ROOT}/App/cmsis/stm32h7" CACHE PATH "Prepared STM32H747 CMSIS staging directory")
set(STEDGEAI_GENERATED_DIR "${STEDGEAI_STAGING_DIR}/generated")
set(STEDGEAI_INCLUDE_DIR "${STEDGEAI_STAGING_DIR}/include")
file(GLOB STEDGEAI_RUNTIME_LIB_CANDIDATES
  "${STEDGEAI_STAGING_DIR}/lib/gcc/stm32h7/NetworkRuntime*_CM7_GCC.a"
)
list(SORT STEDGEAI_RUNTIME_LIB_CANDIDATES)
if(STEDGEAI_RUNTIME_LIB_CANDIDATES)
  list(GET STEDGEAI_RUNTIME_LIB_CANDIDATES -1 STEDGEAI_RUNTIME_LIB)
else()
  set(STEDGEAI_RUNTIME_LIB "${STEDGEAI_STAGING_DIR}/lib/gcc/stm32h7/NetworkRuntime_CM7_GCC_NOT_FOUND.a")
endif()
set(LINKER_SCRIPT "${CMAKE_CURRENT_LIST_DIR}/stm32h747xih_m7_smoke.ld")

foreach(required_file
    "${STM32_CMSIS_DIR}/startup/startup_stm32h747xihx.s"
    "${STM32_CMSIS_DIR}/src/system_stm32h7xx.c"
    "${STM32_CMSIS_DIR}/device/stm32h747xx.h"
    "${STM32_CMSIS_DIR}/core/core_cm7.h"
    "${STEDGEAI_GENERATED_DIR}/network.c"
    "${STEDGEAI_GENERATED_DIR}/network_data.c"
    "${STEDGEAI_INCLUDE_DIR}/stai.h"
    "${STEDGEAI_RUNTIME_LIB}")
  if(NOT EXISTS "${required_file}")
    message(FATAL_ERROR "Missing ${required_file}. Run scripts/prepare_stm32_ai_runtime.sh first.")
  endif()
endforeach()

add_executable(m7_inference_smoke.elf
  "${STM32_CMSIS_DIR}/startup/startup_stm32h747xihx.s"
  "${STM32_CMSIS_DIR}/src/system_stm32h7xx.c"
  main.c
  "${FIRMWARE_ROOT}/rl_uart8_transport_v0.c"
  "${FIRMWARE_ROOT}/rl_stedgeai_policy_v0.c"
  "${STEDGEAI_GENERATED_DIR}/network.c"
  "${STEDGEAI_GENERATED_DIR}/network_data.c"
)

target_compile_definitions(m7_inference_smoke.elf PRIVATE
  CORE_CM7
  STM32H747xx
  RL_POLICY_INFERENCE_V0_ENABLE_STEDGEAI
)

target_include_directories(m7_inference_smoke.elf PRIVATE
  "${FIRMWARE_ROOT}"
  "${STM32_CMSIS_DIR}/device"
  "${STM32_CMSIS_DIR}/core"
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
  -specs=nosys.specs
  "LINKER:-T,${LINKER_SCRIPT}"
  "LINKER:-Map,${CMAKE_CURRENT_BINARY_DIR}/m7_inference_smoke.map"
  "LINKER:--gc-sections"
)

target_link_libraries(m7_inference_smoke.elf PRIVATE
  "${STEDGEAI_RUNTIME_LIB}"
  m
)

add_custom_command(TARGET m7_inference_smoke.elf POST_BUILD
  COMMAND ${CMAKE_SIZE} $<TARGET_FILE:m7_inference_smoke.elf>
)
