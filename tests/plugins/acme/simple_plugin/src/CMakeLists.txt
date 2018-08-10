add_library(simple_plugin SHARED simple_plugin.c hook_specs.h)
install(TARGETS simple_plugin EXPORT simple_plugin_export DESTINATION ${ARTIFACTS_DIR})
