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
    check_module("build")
    check_module("wheel")

    remove("src/qtools/plano")
    copy("subrepos/plano/src/plano", "src/qtools/plano")

    run("python -m build")

@command
def test():
    check_module("venv")

    build()

    wheel = find_wheel()

    with temp_dir() as dir:
        run(f"python -m venv {dir}")
        run(f". {dir}/bin/activate && pip install --force-reinstall {wheel}", shell=True)
        run(f". {dir}/bin/activate && qtools-self-test", shell=True)

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

@command
def image_build():
    check_program("docker")

    run("docker build -t ssorj/qtools .")

@command
def image_test():
    check_program("docker")

    build()

    run("docker run -it ssorj/qtools")

@command
def image_push():
    check_program("docker")

    build()

    run("docker login quay.io")
    run("docker push ssorj/qtools docker://quay.io/ssorj/qtools")

def find_wheel():
    for name in list_dir("dist", "ssorj_qtools-*.whl"):
        return join("dist", name)
    else:
        fail("Wheel file not found")
