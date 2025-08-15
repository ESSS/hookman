#include "hook_specs.h"

HOOK_FRICTION_FACTOR(value1, value2) {
    return value1 - value2;
}

HOOK_ENV_TEMPERATURE(value1, value2){
    return value1 - value2;
}
