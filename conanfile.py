import os
from conan import ConanFile
from conan.tools.files import update_conandata, copy, rm, chdir, mkdir, collect_libs, replace_in_file
from conan.tools.env import VirtualRunEnv, VirtualBuildEnv
from conan.tools.scm import Git
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout, CMakeDeps
from conan.tools.microsoft import VCVars
from conan.tools.layout import basic_layout

class ZenohCConan(ConanFile):

    name = "zenoh-c"
    version = "0.7.2-rc"
    
    license = "Apache License 2.0"
    author = "Ulrich Eck"
    url = "https://github.com/TUM-CONAN/conan-zenohc.git"
    description = "Recipe to build zenoh-c using conan"    

    settings = "os", "compiler", "build_type", "arch"


    exports_sources = "CMakeLists.txt"

    def export(self):
        update_conandata(self, {"sources": {
            "commit": "master",  # "{}".format(self.version),
            "url": "https://github.com/TUM-CAMP-NARVIS/zenoh-c.git"
            }}
            )

    def source(self):
        git = Git(self)
        sources = self.conan_data["sources"]
        git.clone(url=sources["url"], target=self.source_folder)
        git.checkout(commit=sources["commit"])


    @property
    def is_win(self):
        return self.settings.os == "Windows" or self.settings.os == "WindowsStore"

    @property
    def is_uwp_armv8(self):
        return self.settings.os == "WindowsStore" and self.settings.arch == "armv8"
    
    @property
    def is_win_x64(self):
        return self.settings.os == "Windows" and self.settings.arch == "x86_64"

    def generate(self):

        tc = CMakeToolchain(self)
        def add_cmake_option(option, value):
            var_name = "{}".format(option).upper()
            value_str = "{}".format(value)
            var_value = "ON" if value_str == 'True' else "OFF" if value_str == 'False' else value_str
            tc.variables[var_name] = var_value

        for option, value in self.options.items():
            add_cmake_option(option, value)

        # not used as workaround below, but in theory that would be the right settings
        if self.is_uwp_armv8:
            tc.cache_variables["ZENOHC_CARGO_CHANNEL"] = "nightly"
            tc.cache_variables["ZENOHC_CUSTOM_TARGET"] = "aarch64-uwp-windows-msvc"
            tc.cache_variables["ZENOHC_CARGO_FLAGS"] = "-Zbuild-std=panic_abort,std"
            tc.cache_variables["ZENOHC_BUILD_WITH_SHARED_MEMORY"] = False
            return

        tc.generate()

        deps = CMakeDeps(self)

        deps.generate()

    def layout(self):
        if self.is_uwp_armv8:
            basic_layout(self)
        else:
            cmake_layout(self)

    def build(self):
        if self.is_uwp_armv8:
            be = VirtualRunEnv(self)
            with be.vars(scope="run").apply():
                # try hardcoded for now ..
                # conan-cmake seems to mess with some environment/settings
                rel_flag = ""
                if self.settings.build_type == "Release":
                    rel_flag = " --release"
                self.run("cargo +nightly build -Zbuild-std=panic_abort,std{0} --features=logger-autoinit --target=aarch64-uwp-windows-msvc".format(rel_flag))
        else:
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def _zenoh_lib_name(self):
        name = "zenohc"
        if not self.is_win and self.settings.build_type == "Debug":
            name += "d"
        return name

    def package(self):
        if self.is_win:
            bin_path = None
            folder = "release" if self.settings.build_type == "Release" else "debug"
            if self.is_uwp_armv8:
                bin_path = os.path.join(self.source_folder, "target", 'aarch64-uwp-windows-msvc', folder)
            if self.is_win_x64:
                bin_path = os.path.join(self.source_folder, "target", folder)

            if bin_path is not None:
                # clean up before recursive copy
                rm(self, "*.dll", os.path.join(bin_path, "deps"))
                rm(self, "*.lib", os.path.join(bin_path, "deps"))
                # Manually copy the files in the target (needs to be adapted if debug build is enabled ..)

                copy(self, "*.dll", bin_path, os.path.join(self.package_folder, "bin"), keep_path=False)
                copy(self, "*.lib", bin_path, os.path.join(self.package_folder, "lib"), keep_path=False)
                copy(self, "*.h", os.path.join(self.source_folder, "include"), os.path.join(self.package_folder, "include"))
            else:
                self.output.error("Unknown Windows platform - install incomplete !!!")
        else:
            cmake = CMake(self)
            cmake.install()

    def package_info(self):
        self.cpp_info.libs = [self._zenoh_lib_name()]
