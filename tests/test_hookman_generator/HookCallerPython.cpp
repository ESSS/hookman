#include <pybind11/pybind11.h>
#include <pybind11/functional.h>
#include <HookCaller.hpp>

namespace py = pybind11;

PYBIND11_MODULE(_test_hook_man_generator, m) {
    py::class_<hookman::HookCaller>(m, "HookCaller")
        .def(py::init<>())
        .def("friction_factor", &hookman::HookCaller::friction_factor)
        .def("set_friction_factor_function", &hookman::HookCaller::set_friction_factor_function)
        ;
}
