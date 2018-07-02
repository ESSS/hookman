#ifndef HEADER_FILE
#define HEADER_FILE
#ifdef WIN32
    #define API_EXP __declspec(dllexport)
    #define FUNC_EXP __cdecl
#else
    #define API_EXP
    #define FUNC_EXP
#endif

#define INIT_HOOKS() API_EXP char* FUNC_EXP acme_version_api() {return "v1";}
#define HOOK_FRICTION_FACTOR(v1, v2) API_EXP int FUNC_EXP acme_v1_friction_factor(int v1, int v2)

#endif
