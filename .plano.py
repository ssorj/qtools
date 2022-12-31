#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

from plano import *

@command
def build():
    # check_module("build")
    # check_module("wheel")

    remove("src/qtools/plano")
    copy("subrepos/plano/src/plano", "src/qtools/plano")

    run("python -m build")

@command
def test():
    # check_module("venv")

    build()

    wheel = find_wheel()

    with temp_dir() as dir:
        if WINDOWS:
            dir = dir.replace("\\", "/")
            activate_script = f"{dir}/Scripts/Activate.ps1"
        else:
            activate_script = f". {dir}/bin/activate"

        run(f"python -m venv {dir}")
        run(f"{activate_script} && pip install --force-reinstall {wheel}", shell=True)
        run(f"{activate_script} && qtools-self-test --exclude tls", shell=True)

@command
def install():
    build()

    wheel = find_wheel()

    run(f"pip install --user --force-reinstall {wheel}")

@command
def clean():
    remove("dist")
    remove(find(".", "__pycache__"))

@command
def upload():
    """
    Upload the package to PyPI
    """

    check_program("twine", "pip install twine")

    build()

    run("twine upload --repository testpypi dist/*", shell=True)

def find_wheel():
    for file in list_dir("dist", "ssorj_qtools-*.whl"):
        return join("dist", file)
    else:
        fail("Wheel file not found")
