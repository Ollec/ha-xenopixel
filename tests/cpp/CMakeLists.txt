cmake_minimum_required(VERSION 3.14)
project(xenopixel_tests CXX)
set(CMAKE_CXX_STANDARD 17)

# Coverage flags
add_compile_options(--coverage -O0 -g)
add_compile_definitions(UNIT_TEST)
add_link_options(--coverage)

# GoogleTest via FetchContent
include(FetchContent)
FetchContent_Declare(googletest
  GIT_REPOSITORY https://github.com/google/googletest.git
  GIT_TAG v1.17.0)
FetchContent_MakeAvailable(googletest)

# Test executable — mock include path comes FIRST so the stub headers
# shadow the real ESPHome includes that xenopixel_light.h tries to pull in.
add_executable(test_xenopixel_light test_xenopixel_light.cpp)
target_include_directories(test_xenopixel_light PRIVATE
  mocks                                              # esphome_mock.h + stub headers
  ${CMAKE_SOURCE_DIR}/../../esphome/components       # real xenopixel_light/xenopixel_light.h
)
target_link_libraries(test_xenopixel_light GTest::gtest_main)

enable_testing()
include(GoogleTest)
gtest_discover_tests(test_xenopixel_light)
