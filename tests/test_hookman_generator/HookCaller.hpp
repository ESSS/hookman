#ifndef _H_HOOKMAN_HOOK_CALLER
#define _H_HOOKMAN_HOOK_CALLER

#include <functional>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>
#include <iostream>

#ifdef _WIN32
    #include <windows.h>
#else
    #include <dlfcn.h>
#endif

#include <custom_include1>
#include <custom_include2>

namespace hookman {

template <typename F_TYPE> std::function<F_TYPE> from_c_pointer(uintptr_t p) {
    return std::function<F_TYPE>(reinterpret_cast<F_TYPE *>(p));
}

class HookCaller {
public:
    std::vector<std::function<int(int, double[2])>> friction_factor_impls() {
        return this->_friction_factor_impls;
    }
    std::vector<std::function<int(int, double[2])>> friction_factor_2_impls() {
        return this->_friction_factor_2_impls;
    }

    void append_friction_factor_impl(uintptr_t pointer) {
        this->_friction_factor_impls.push_back(from_c_pointer<int(int, double[2])>(pointer));
    }

    void append_friction_factor_2_impl(uintptr_t pointer) {
        this->_friction_factor_2_impls.push_back(from_c_pointer<int(int, double[2])>(pointer));
    }


#if defined(_WIN32)

public:
    ~HookCaller() {
        for (auto handle : this->handles) {
            FreeLibrary(handle);
        }
    }
    void load_impls_from_library(const std::string utf8_filename) {
        std::wstring w_filename = utf8_to_wstring(utf8_filename);
        auto handle = LoadLibraryW(w_filename.c_str());
        if (handle == NULL) {
            throw std::runtime_error("Error loading library " + utf8_filename + ": " + std::to_string(GetLastError()));
        }
        this->handles.push_back(handle);

        auto p0 = GetProcAddress(handle, "acme_v1_friction_factor");
        if (p0 != nullptr) {
            this->append_friction_factor_impl((uintptr_t)(p0));
        }

        auto p1 = GetProcAddress(handle, "acme_v1_friction_factor_2");
        if (p1 != nullptr) {
            this->append_friction_factor_2_impl((uintptr_t)(p1));
        }

    }


private:
    std::wstring utf8_to_wstring(const std::string &s) {
        int required_size = MultiByteToWideChar(CP_UTF8, MB_PRECOMPOSED | MB_ERR_INVALID_CHARS, s.c_str(), -1, nullptr, 0);
        auto buffer = std::make_unique<WCHAR[]>(required_size);
        int err = MultiByteToWideChar(CP_UTF8, MB_PRECOMPOSED | MB_ERR_INVALID_CHARS, s.c_str(), -1, buffer.get(), required_size);
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
        return std::wstring(buffer.get(), required_size);
    }


private:
    std::vector<HMODULE> handles;

#elif defined(__linux__)

public:
    void load_impls_from_library(const std::string utf8_filename) {
    }

#else
    #error "unknown platform"
#endif

private:
    std::vector<std::function<int(int, double[2])>> _friction_factor_impls;
    std::vector<std::function<int(int, double[2])>> _friction_factor_2_impls;
};

}  // namespace hookman
#endif // _H_HOOKMAN_HOOK_CALLER
