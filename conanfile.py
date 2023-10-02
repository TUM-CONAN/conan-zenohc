import os
from conan import ConanFile
from conan.tools.files import update_conandata, copy, chdir, mkdir, collect_libs, replace_in_file
from conan.tools.env import VirtualRunEnv
from conan.tools.scm import Git
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout, CMakeDeps

class ZenohCConan(ConanFile):
    python_requires = "camp_common/0.5@camposs/stable"
    python_requires_extend = "camp_common.CampCMakeBase"

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
            "commit": "{}".format(self.version),
            "url": "https://github.com/eclipse-zenoh/zenoh-c.git"
            }}
            )

    def source(self):
        git = Git(self)
        sources = self.conan_data["sources"]
        git.clone(url=sources["url"], target=self.source_folder)
        git.checkout(commit=sources["commit"])

    def _configure_toolchain(self, tc):
        if self.settings.os == "WindowsStore" and self.settings.arch == "armv8":
            tc.cache_variables["ZENOHC_CARGO_CHANNEL"] = "nightly"
            tc.cache_variables["ZENOHC_CUSTOM_TARGET"] = "aarch64-uwp-windows-msvc"
            tc.cache_variables["ZENOHC_CARGO_FLAGS"] = "-Z build-std=panic_abort,std"
            tc.cache_variables["ZENOHC_BUILD_WITH_SHARED_MEMORY"] = False


