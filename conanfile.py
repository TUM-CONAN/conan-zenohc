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

    def build(self):
        replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
            """COMMAND cargo +${ZENOHC_CARGO_CHANNEL} build ${cargo_flags}""",
            """COMMAND cargo build ${cargo_flags}""")
        replace_in_file(self, os.path.join(self.source_folder, "Cargo.toml.in"),
            """branch = "master" """,
            """tag = "0.7.2-rc" """)
        replace_in_file(self, os.path.join(self.source_folder, "Cargo.toml.in"),
            """branch = "master", """,
            """tag = "0.7.2-rc", """)



        super().build()
