#include <pybind11/pybind11.h>
#include <HookCaller.hpp>

namespace py = pybind11;

PYBIND11_MODULE(_test_hook_man_generator, m) {
    py::class_<HookMan::HookCaller>(m, "HookCaller")
        .def(py::init<>())
        .def("set_friction_factor_function", &HookMan::HookCaller::set_friction_factor_function)
        ;
}
