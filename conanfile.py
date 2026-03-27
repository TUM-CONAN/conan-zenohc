import os
from textwrap import dedent

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import copy, rm, save, update_conandata
from conan.tools.layout import basic_layout
from conan.tools.scm import Git


class ZenohCConan(ConanFile):

    name = "zenoh-c"
    version = "1.3.4"

    license = "Apache License 2.0"
    author = "Ulrich Eck"
    url = "https://github.com/TUM-CONAN/conan-zenohc.git"
    description = "Recipe to build zenoh-c using conan"

    settings = "os", "compiler", "build_type", "arch"

    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    exports_sources = "CMakeLists.txt"

    def export(self):
        update_conandata(
            self,
            {
                "sources": {
                    "commit": "{}".format(self.version),
                    "url": "https://github.com/eclipse-zenoh/zenoh-c.git",
                }
            },
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
    def is_linux(self):
        return self.settings.os == "Linux"

    @property
    def is_macos(self):
        return self.settings.os == "Macos"

    @property
    def is_unix_like(self):
        return self.is_linux or self.is_macos

    @property
    def is_uwp_armv8(self):
        return self.settings.os == "WindowsStore" and self.settings.arch == "armv8"

    @property
    def is_win_x64(self):
        return self.settings.os == "Windows" and self.settings.arch == "x86_64"

    @property
    def is_android_armv8(self):
        return self.settings.os == "Android" and self.settings.arch == "armv8"

    def generate(self):
        tc = CMakeToolchain(self)

        def add_cmake_option(option, value):
            var_name = "{}".format(option).upper()
            value_str = "{}".format(value)
            var_value = "ON" if value_str == "True" else "OFF" if value_str == "False" else value_str
            tc.variables[var_name] = var_value

        for option, value in self.options.items():
            add_cmake_option(option, value)

        if self.is_uwp_armv8:
            tc.cache_variables["ZENOHC_CARGO_CHANNEL"] = "nightly"
            tc.cache_variables["ZENOHC_CUSTOM_TARGET"] = "aarch64-uwp-windows-msvc"
            tc.cache_variables["ZENOHC_CARGO_FLAGS"] = "-Zbuild-std=panic_abort,std"
            return

        if self.is_android_armv8:
            tc.cache_variables["ZENOHC_CUSTOM_TARGET"] = "aarch64-linux-android"

        tc.cache_variables["ZENOHC_BUILD_WITH_SHARED_MEMORY"] = not self.is_android_armv8
        tc.cache_variables["ZENOHC_BUILD_WITH_UNSTABLE_API"] = True

        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def layout(self):
        if self.is_uwp_armv8:
            basic_layout(self)
        else:
            cmake_layout(self)

    def patch_sources(self):
        if self.is_uwp_armv8:
            self.output.info("Patching sources for UWP.")
            save(
                self,
                os.path.join(self.source_folder, "rust-toolchain.toml"),
                dedent(
                    """
                    [toolchain]
                    # +nightly is required to enable the build-std feature. The following specifies that the
                    # latest version be used. It can be pinned here to a specific version, e.g.
                    # "nightly-2021-08-12".
                    channel = "nightly"
                    components = ["rust-src"]
                    """
                ),
            )
            save(
                self,
                os.path.join(self.source_folder, "Cargo.toml"),
                dedent(
                    """

                    [patch.crates-io]
                    ring = { git = "https://github.com/awakecoding/ring", branch = "0.16.20_alpha" }
                    """
                ),
                append=True,
            )

    def build(self):
        self.patch_sources()
        if self.is_uwp_armv8:
            build_env = VirtualRunEnv(self)
            with build_env.vars(scope="run").apply():
                rel_flag = ""
                if self.settings.build_type == "Release":
                    rel_flag = " --release"
                self.run(
                    "cargo +nightly build -Zbuild-std=panic_abort,std{0} --features=logger-autoinit --target=aarch64-uwp-windows-msvc".format(
                        rel_flag
                    )
                )
        else:
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def _zenoh_lib_name(self):
        name = "zenohc"
        if self.settings.build_type == "Debug":
            name += "d"
        return name

    def _fix_macos_shared_library_install_name(self):
        if not self.is_macos or not self.options.shared:
            return

        library_name = "lib{}.dylib".format(self._zenoh_lib_name())
        library_path = os.path.join(self.package_folder, "lib", library_name)
        if not os.path.exists(library_path):
            self.output.warning("Expected shared library not found at {}".format(library_path))
            return

        self.output.info("Rewriting install name for {}".format(library_name))
        self.run('install_name_tool -id @rpath/{0} "{1}"'.format(library_name, library_path))

    def _prune_unix_library_artifacts(self):
        if not self.is_unix_like:
            return

        library_folder = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            rm(self, "*.a", library_folder, recursive=False)
        else:
            rm(self, "*.so", library_folder, recursive=False)
            rm(self, "*.dylib", library_folder, recursive=False)

    def package(self):
        if self.is_win:
            bin_path = None
            folder = "release" if self.settings.build_type == "Release" else "debug"
            if self.is_uwp_armv8:
                bin_path = os.path.join(self.source_folder, "target", "aarch64-uwp-windows-msvc", folder)
            if self.is_win_x64:
                bin_path = os.path.join(self.build_folder, folder, "target", folder)

            if bin_path is not None:
                rm(self, "*.dll", os.path.join(bin_path, "deps"))
                rm(self, "*.lib", os.path.join(bin_path, "deps"))
                copy(self, "*.dll", bin_path, os.path.join(self.package_folder, "bin"), keep_path=False)
                copy(self, "*.lib", bin_path, os.path.join(self.package_folder, "lib"), keep_path=False)
                copy(self, "*.h", os.path.join(self.build_folder, folder, "include"), os.path.join(self.package_folder, "include"))
                copy(self, "*.h", os.path.join(self.source_folder, "include"), os.path.join(self.package_folder, "include"))
            else:
                self.output.error("Unknown Windows platform - install incomplete !!!")
            return

        cmake = CMake(self)
        cmake.install()
        self._prune_unix_library_artifacts()
        self._fix_macos_shared_library_install_name()

    def package_info(self):
        self.cpp_info.libs = [self._zenoh_lib_name()]
