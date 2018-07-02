#include <functional>

namespace HookMan {

template <typename F_TYPE> std::function<F_TYPE> register_c_func(uintptr_t p) {
    return std::function<F_TYPE>(reinterpret_cast<F_TYPE *>(p));
}

class HookCaller {
public:
    inline int friction_factor(int v1, int v2) { return this->_friction_factor(v1, v2); }

    void set_friction_factor_function(uintptr_t pointer) {
        this->_friction_factor = register_c_func<int(int, int)>(pointer);
    }

private:
    std::function<int(int, int)> _friction_factor;
};
}
