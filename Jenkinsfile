#!/usr/bin/env groovy

pipeline {

    agent {
        // Use the docker to assign the Python version.
        // Use the label to assign the node to run the test.
        // It is recommended by SQUARE team do not add the label.
        docker {
            image 'lsstts/develop-env:develop'
            args "-u root --entrypoint=''"
        }
    }

    options {
      disableConcurrentBuilds()
    }

    triggers {
        pollSCM('H * * * *')
    }

    environment {
        // SAL user home
        SAL_USERS_HOME = "/home/saluser"
        // SAL setup file
        SAL_SETUP_FILE = "/home/saluser/.setup.sh"
        // PlantUML url
        PLANTUML_URL = "https://managedway.dl.sourceforge.net/project/plantuml/plantuml.jar"
        // XML report path
        XML_REPORT = "jenkinsReport/report.xml"
        // Module name used in the pytest coverage analysis
        MODULE_NAME = "lsst.ts.MTAOS"
        // Stack version
        STACK_VERSION = "current"
        // Target branch - either develop or master, depending on where we are
        // merging or what branch is run
        BRANCH = getBranchName(env.CHANGE_TARGET, env.BRANCH_NAME)
        // Authority to publish the document online
        user_ci = credentials('lsst-io')
        LTD_USERNAME = "${user_ci_USR}"
        LTD_PASSWORD = "${user_ci_PSW}"
        DOCUMENT_NAME = "ts-mtaos"
        WORK_BRANCHES = "${GIT_BRANCH} ${CHANGE_BRANCH} develop"
    }

    stages {

        stage ('Install the Libraries') {
            steps {
                withEnv(["HOME=${env.WORKSPACE}"]) {
                    sh """
                        source ${env.SAL_SETUP_FILE}

                        cd ${env.SAL_USERS_HOME} && { curl -O ${env.PLANTUML_URL} ; cd -; }
                        pip install sphinxcontrib-plantuml
                    """
                }
            }
        }

        stage ('Cloning Repos') {
            steps {
                dir(env.WORKSPACE + '/phosim_utils') {
                    git branch: 'master', url: 'https://github.com/lsst-dm/phosim_utils.git'
                }
                dir(env.WORKSPACE + '/ts_wep') {
                    git branch: "${BRANCH}", url: 'https://github.com/lsst-ts/ts_wep.git'
                }
                dir(env.WORKSPACE + '/ts_ofc') {
                    git branch: "${BRANCH}", url: 'https://github.com/lsst-ts/ts_ofc.git'
                }
            }
        }

        stage ('Building the Dependencies') {
            steps {
                withEnv(["HOME=${env.WORKSPACE}"]) {
                    sh """
                        source ${env.SAL_SETUP_FILE}

                        cd phosim_utils/
                        setup -k -r . -t ${env.STACK_VERSION}
                        scons

                        cd ../ts_wep/
                        setup -k -r .
                        scons python
                    """
                }
            }
        }
        stage("Checkout xml") {
            steps {
                withEnv(["HOME=${env.WORKSPACE}"]) {
                    sh """
                        source ${env.SAL_SETUP_FILE}
                        cd ${env.SAL_USERS_HOME}/repos/ts_xml
                        ${env.SAL_USERS_HOME}/.checkout_repo.sh \${WORK_BRANCHES}
                        git pull
                    """
                }
            }
        }
        stage("Checkout IDL") {
            steps {
                withEnv(["HOME=${env.WORKSPACE}"]) {
                    sh """
                        source ${env.SAL_SETUP_FILE}
                        cd ${env.SAL_USERS_HOME}/repos/ts_idl
                        ${env.SAL_USERS_HOME}/.checkout_repo.sh \${WORK_BRANCHES}
                        git pull
                    """
                }
            }
        }
        stage("Build IDL files") {
            steps {
                withEnv(["HOME=${env.WORKSPACE}"]) {
                    sh """
                        source ${env.SAL_SETUP_FILE}
                        source ${env.SAL_USERS_HOME}/.bashrc
                        make_idl_files.py MTAOS
                    """
                }
            }
        }
        stage ('Unit Tests and Coverage Analysis') {
            steps {
                // Pytest needs to export the junit report.
                withEnv(["HOME=${env.WORKSPACE}"]) {
                    sh """
                        source ${env.SAL_SETUP_FILE}

                        cd phosim_utils/
                        setup -k -r . -t ${env.STACK_VERSION}

                        cd ../ts_wep/
                        setup -k -r .

                        cd ../ts_ofc/
                        setup -k -r .

                        cd ../
                        setup -k -r .
                        pytest --cov-report html --cov=${env.MODULE_NAME} --junitxml=${env.XML_REPORT} tests/
                    """
                }
            }
        }

        stage ('Build and Upload Documentation') {
            steps {
                withEnv(["HOME=${env.WORKSPACE}"]) {
                    sh """
                        source ${env.SAL_SETUP_FILE}

                        cd phosim_utils/
                        setup -k -r . -t ${env.STACK_VERSION}

                        cd ../ts_wep/
                        setup -k -r .

                        cd ../ts_ofc/
                        setup -k -r .

                        cd ../
                        setup -k -r .

                        package-docs build
                        ltd upload --product ${env.DOCUMENT_NAME} --git-ref ${GIT_BRANCH} --dir doc/_build/html
                    """
                }
            }
        }

    }

    post {
        always {
            // Change the ownership of workspace to Jenkins for the clean up
            // This is to work around the condition that the user ID of jenkins
            // is 1003 on TSSW Jenkins instance. In this post stage, it is the
            // jenkins to do the following clean up instead of the root in the
            // docker container.
            withEnv(["HOME=${env.WORKSPACE}"]) {
                sh 'chown -R 1003:1003 ${HOME}/'
            }

            // The path of xml needed by JUnit is relative to
            // the workspace.
            junit "${env.XML_REPORT}"

            // Publish the HTML report
            publishHTML (target: [
                allowMissing: false,
                alwaysLinkToLastBuild: false,
                keepAll: true,
                reportDir: 'htmlcov',
                reportFiles: 'index.html',
                reportName: "Coverage Report"
            ])
        }

        cleanup {
            // clean up the workspace
            deleteDir()
        }
    }
}

// Return branch name. If changeTarget isn't defined, use branchName. Returns
// either develop or master
def getBranchName(changeTarget, branchName) {
    def branch = (changeTarget != null) ? changeTarget : branchName
    // If not master or develop, it's ticket branch and so the main branch is
    // develop. Can be adjusted with hotfix branches merging into master
    // if (branch.startsWith("hotfix")) { return "master" }
    // The reason to use the 'switch' instead of 'if' loop is to prepare for
    // future with more branches
    switch (branch) {
        case "master":
        case "develop":
            return branch
    }
    print("!!! Returning default for branch " + branch + " !!!\n")
    return "develop"
}
