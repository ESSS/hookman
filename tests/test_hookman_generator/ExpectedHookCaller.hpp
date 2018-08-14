#include <functional>

namespace hookman {

template <typename F_TYPE> std::function<F_TYPE> from_c_pointer(uintptr_t p) {
    return std::function<F_TYPE>(reinterpret_cast<F_TYPE *>(p));
}

class HookCaller {
public:
    std::function<int(int, double[2])> friction_factor() {
        return this->_friction_factor;
    }

    void set_friction_factor_function(uintptr_t pointer) {
        this->_friction_factor = from_c_pointer<int(int, double[2])>(pointer);
    }

private:
    std::function<int(int, double[2])> _friction_factor;
};
}
