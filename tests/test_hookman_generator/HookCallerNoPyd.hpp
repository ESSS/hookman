// File automatically generated by hookman, **DO NOT MODIFY MANUALLY**
#ifndef _H_HOOKMAN_HOOK_CALLER
#define _H_HOOKMAN_HOOK_CALLER

#include <functional>
#include <stdexcept>
#include <string>
#include <vector>

#ifdef _WIN32
    #include <windows.h>
#else
    #include <dlfcn.h>
#endif


namespace hookman {

template <typename F_TYPE> std::function<F_TYPE> from_c_pointer(uintptr_t p) {
    return std::function<F_TYPE>(reinterpret_cast<F_TYPE *>(p));
}

class HookCaller {
public:


#if defined(_WIN32)

public:
    ~HookCaller() {
        for (auto handle : this->handles) {
            FreeLibrary(handle);
        }
    }
    void load_impls_from_library(const std::string& utf8_filename) {
        std::wstring w_filename = utf8_to_wstring(utf8_filename);
        auto handle = LoadLibraryW(w_filename.c_str());
        if (handle == NULL) {
            throw std::runtime_error("Error loading library " + utf8_filename + ": " + std::to_string(GetLastError()));
        }
        this->handles.push_back(handle);

    }


private:
    std::wstring utf8_to_wstring(const std::string& s) {
        int flags = 0;
        int required_size = MultiByteToWideChar(CP_UTF8, flags, s.c_str(), -1, nullptr, 0);
        std::wstring result;
        if (required_size == 0) {
            return result;
        }
        result.resize(required_size);
        int err = MultiByteToWideChar(CP_UTF8, flags, s.c_str(), -1, &result[0], required_size);
        if (err == 0) {
            // error handling: https://docs.microsoft.com/en-us/windows/desktop/api/stringapiset/nf-stringapiset-multibytetowidechar#return-value
            switch (GetLastError()) {
                case ERROR_INSUFFICIENT_BUFFER: throw std::runtime_error("utf8_to_wstring: ERROR_INSUFFICIENT_BUFFER");
                case ERROR_INVALID_FLAGS: throw std::runtime_error("utf8_to_wstring: ERROR_INVALID_FLAGS");
                case ERROR_INVALID_PARAMETER: throw std::runtime_error("utf8_to_wstring: ERROR_INVALID_PARAMETER");
                case ERROR_NO_UNICODE_TRANSLATION: throw std::runtime_error("utf8_to_wstring: ERROR_NO_UNICODE_TRANSLATION");
                default: throw std::runtime_error("Undefined error: " + std::to_string(GetLastError()));
            }
        }
        return result;
    }


private:
    std::vector<HMODULE> handles;

#elif defined(__linux__)

private:
    std::vector<void*> handles;

public:
    ~HookCaller() {
        for (auto handle : this->handles) {
            dlclose(handle);
        }
    }
    void load_impls_from_library(const std::string& utf8_filename) {
        auto handle = dlopen(utf8_filename.c_str(), RTLD_LAZY);
        if (handle == nullptr) {
            throw std::runtime_error("Error loading library " + utf8_filename + ": dlopen failed");
        }
        this->handles.push_back(handle);

    }

#else
    #error "unknown platform"
#endif

private:
};

}  // namespace hookman
#endif // _H_HOOKMAN_HOOK_CALLER