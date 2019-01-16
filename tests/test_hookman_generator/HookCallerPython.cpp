#include <pybind11/functional.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl_bind.h>
#include <HookCaller.hpp>

namespace py = pybind11;

PYBIND11_MAKE_OPAQUE(std::vector<std::function<int(int, double[2])>>);

PYBIND11_MODULE(_test_hook_man_generator, m) {
    py::bind_vector<std::vector<std::function<int(int, double[2])>>>(m, "vector_friction_factor");

    py::class_<hookman::HookCaller>(m, "HookCaller")
        .def(py::init<>())
        .def("friction_factor_impls", &hookman::HookCaller::friction_factor_impls)
        .def("append_friction_factor_impl", &hookman::HookCaller::append_friction_factor_impl)
    ;
}