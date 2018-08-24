#ifndef ACME_HOOK_SPECS_HEADER_FILE
#define ACME_HOOK_SPECS_HEADER_FILE
#ifdef WIN32
    #define HOOKMAN_API_EXP __declspec(dllexport)
    #define HOOKMAN_FUNC_EXP __cdecl
#else
    #define HOOKMAN_API_EXP
    #define HOOKMAN_FUNC_EXP
#endif

#define INIT_HOOKS() HOOKMAN_API_EXP char* HOOKMAN_FUNC_EXP acme_version_api() {return "v1";}

/*!
Docs for Friction Factor
    Input:
        Testing indentation
    Return:
            Integer
*/
#define HOOK_FRICTION_FACTOR(v1, v2) HOOKMAN_API_EXP int HOOKMAN_FUNC_EXP acme_v1_friction_factor(int v1, double v2[2])

#endif
