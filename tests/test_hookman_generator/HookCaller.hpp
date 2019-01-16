#ifndef _H_HOOKMAN_HOOK_CALLER
#define _H_HOOKMAN_HOOK_CALLER

#include <functional>
#include <vector>

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

private:
    std::vector<std::function<int(int, double[2])>> _friction_factor_impls;
    std::vector<std::function<int(int, double[2])>> _friction_factor_2_impls;
};

}  // namespace hookman
#endif // _H_HOOKMAN_HOOK_CALLER
