#include <functional>

namespace HookMan {

template <typename F_TYPE> std::function<F_TYPE> register_c_func(uintptr_t p) {
    return std::function<F_TYPE>(reinterpret_cast<F_TYPE *>(p));
}

class HookCaller {
public:
    std::function<int(int, int)> friction_factor() {
        return this->_friction_factor;
    }

    void set_friction_factor_function(uintptr_t pointer) {
        this->_friction_factor = register_c_func<int(int, int)>(pointer);
    }

private:
    std::function<int(int, int)> _friction_factor;
};
}
