add_library(simple_plugin_2 SHARED simple_plugin_2.cpp hook_specs.h)
install(TARGETS simple_plugin_2 EXPORT simple_plugin_2_export DESTINATION ${ARTIFACTS_DIR})
